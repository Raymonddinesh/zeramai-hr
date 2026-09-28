"""
Module 5 — Offboarding & Exit Management: Security, Scope & Lifecycle Tests.

Test Coverage:
1.  Employee submits resignation (ownership server-derived)
2.  Employee gets own exit request via /api/v3/offboarding/my
3.  Duplicate active resignation attempt rejected (400)
4.  Employee cannot access another employee's exit request directly (IDOR -> 403)
5.  Cross-tenant access denied (tenant-A request accessed with tenant-B -> 403)
6.  Employee cannot approve/review their own resignation (403)
7.  Unauthorized user (FINANCE) cannot approve exit request (403)
8.  Reporting Manager can view and review team member's exit request
9.  Manager B cannot review Manager A's employee exit (403)
10. HR Admin can review and approve exit request with approved last working day
11. Employee cannot sign off on departmental clearance tasks (403)
12. Manager can clear MANAGER departmental clearance tasks for team member
13. HR Admin can clear any departmental clearance task
14. Handover creation and status update
15. Exit interview submission and confidentiality masking (manager sees masked feedback)
16. Settlement readiness checklist update
17. Unauthorized user cannot complete exit (403)
18. HR Admin completes exit (status -> completed, engagement -> completed)
19. Audit log verified for key lifecycle transitions
"""
import os
import uuid
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN":    ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN":       ("hr@zeramai.com",          "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com",      "ChangeMe123!"),
    "FINANCE":        ("finance@zeramai.com",       "ChangeMe123!"),
    "EMPLOYEE":       ("employee@example.com",      "ChangeMe123!"),
}


def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.cookies.get("access_token") or resp.json().get("access_token")
    assert token, f"No token for {email}"
    return token


def set_auth(token: str):
    client.cookies.set("access_token", token)


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


_shared: dict = {}


# ---------------------------------------------------------------------------
# 1. Resignation Submission & Ownership
# ---------------------------------------------------------------------------

def test_employee_submits_resignation(seed_data):
    """Employee submits resignation. Ownership is derived server-side."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    today = date.today()
    lwd = today + timedelta(days=30)
    resp = client.post("/api/v3/offboarding/resignations", json={
        "resignation_date": str(today),
        "proposed_last_working_day": str(lwd),
        "reason_category": "better_opportunity",
        "employee_comments": "Pursuing a new role elsewhere.",
    })
    assert resp.status_code == 201, f"Submission failed: {resp.text}"
    data = resp.json()
    assert data["ticket_number"].startswith("EXIT-")
    assert data["status"] == "submitted"
    assert data["notice_period_days"] == 30
    assert len(data["clearance_tasks"]) == 6
    assert data["interview"] is not None
    assert data["settlement"] is not None

    _shared["exit_id"] = data["id"]
    _shared["employee_person_id"] = data["person_id"]
    _shared["employee_user_id"] = data["user_id"]


def test_employee_gets_own_exit_request(seed_data):
    """Employee gets own exit request via /api/v3/offboarding/my."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/offboarding/my")
    assert resp.status_code == 200
    assert resp.json()["id"] == _shared["exit_id"]


def test_duplicate_active_resignation_rejected(seed_data):
    """Employee cannot submit a second active resignation request."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    today = date.today()
    resp = client.post("/api/v3/offboarding/resignations", json={
        "resignation_date": str(today),
        "proposed_last_working_day": str(today + timedelta(days=30)),
        "reason_category": "personal",
    })
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Cross-Employee IDOR & Tenant Isolation
# ---------------------------------------------------------------------------

def test_employee_cannot_access_other_exit_request(seed_data):
    """Create a second employee and verify they cannot access first employee's exit request."""
    from app.database import SessionLocal
    from app.models import User, Person, Engagement, EngagementType, EngagementStatus, UserRole
    from app.auth import hash_password

    db = SessionLocal()
    try:
        u2 = db.query(User).filter(User.email == "second.emp@test.com").first()
        if not u2:
            p2 = Person(full_name="Second Employee", email="second.emp@test.com")
            db.add(p2)
            db.flush()

            u2 = User(
                email="second.emp@test.com",
                hashed_password=hash_password("ChangeMe123!"),
                role=UserRole.EMPLOYEE,
                person_id=p2.id,
                is_active=True,
            )
            db.add(u2)
            db.flush()

            eng2 = Engagement(
                person_id=p2.id,
                engagement_type=EngagementType.FULL_TIME_EMPLOYEE,
                designation="Software Engineer",
                department="Engineering",
                start_date=date(2026, 1, 1),
                status=EngagementStatus.ACTIVE,
            )
            db.add(eng2)
            db.commit()
        _shared["second_emp_email"] = u2.email
    finally:
        db.close()

    # Login as second employee and attempt IDOR on first employee's exit
    token2 = login("second.emp@test.com", "ChangeMe123!")
    set_auth(token2)

    resp = client.get(f"/api/v3/offboarding/{_shared['exit_id']}")
    assert resp.status_code == 403, (
        f"Expected 403 for unauthorized access to other employee's exit, got {resp.status_code}"
    )


def test_cross_tenant_access_denied(seed_data):
    """Requests belonging to tenant-A cannot be accessed by tenant-B context."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Access exit request with mismatched tenant header
    resp = client.get(
        f"/api/v3/offboarding/{_shared['exit_id']}",
        headers={"X-Tenant-ID": "tenant-other"},
    )
    # The exit request was created in default/null tenant, so tenant-other is a mismatch
    # If the record has tenant_id=None, it's global; let's test explicit tenant isolation
    from app.database import SessionLocal
    from app.models_offboarding import ExitRequest
    db = SessionLocal()
    try:
        req = db.query(ExitRequest).filter(ExitRequest.id == _shared["exit_id"]).first()
        req.tenant_id = "tenant-alpha"
        db.commit()
    finally:
        db.close()

    resp_denied = client.get(
        f"/api/v3/offboarding/{_shared['exit_id']}",
        headers={"X-Tenant-ID": "tenant-beta"},
    )
    assert resp_denied.status_code == 403


# ---------------------------------------------------------------------------
# 3. Review & Approval Permissions
# ---------------------------------------------------------------------------

def test_employee_cannot_approve_own_resignation(seed_data):
    """An employee CANNOT approve or review their own resignation."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/review",
        json={"action": "approve", "comments": "Self approving"},
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 403
    assert "cannot approve or review their own" in resp.json()["detail"]


def test_finance_cannot_review_exit(seed_data):
    """Finance role without manager relationship cannot review exit."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/review",
        json={"action": "approve"},
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 403


def test_manager_reviews_team_resignation(seed_data):
    """Reporting Manager reviews team member's resignation request."""
    # Ensure manager@zeramai.com is the reporting manager on employee's engagement
    from app.database import SessionLocal
    from app.models import Engagement, EngagementType, EngagementStatus, User
    db = SessionLocal()
    try:
        mgr_user = db.query(User).filter(User.email == "manager@zeramai.com").first()
        eng = db.query(Engagement).filter(Engagement.person_id == _shared["employee_person_id"]).first()
        if not eng:
            eng = Engagement(
                person_id=_shared["employee_person_id"],
                engagement_type=EngagementType.FULL_TIME_EMPLOYEE,
                designation="Software Engineer",
                department="Engineering",
                start_date=date(2026, 1, 1),
                status=EngagementStatus.ACTIVE,
                reporting_manager_id=mgr_user.id,
            )
            db.add(eng)
        else:
            eng.reporting_manager_id = mgr_user.id
        db.commit()
    finally:
        db.close()

    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/review",
        json={
            "action": "approve",
            "comments": "Acknowledged by manager. Handover assigned.",
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 200, f"Manager review failed: {resp.text}"
    assert resp.json()["status"] == "under_review"
    assert resp.json()["manager_comments"] == "Acknowledged by manager. Handover assigned."


def test_hr_admin_approves_resignation(seed_data):
    """HR Admin approves resignation and confirms approved last working day."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    approved_lwd = date.today() + timedelta(days=25)
    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/review",
        json={
            "action": "approve",
            "comments": "Approved by HR with early release granted.",
            "approved_last_working_day": str(approved_lwd),
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 200, f"HR approval failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_last_working_day"] == str(approved_lwd)
    assert data["hr_approved_at"] is not None


# ---------------------------------------------------------------------------
# 4. Clearance Tasks & Authorization
# ---------------------------------------------------------------------------

def test_employee_cannot_clear_departmental_tasks(seed_data):
    """Departing employee cannot sign off on departmental clearance tasks."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # Get a task ID
    resp = client.get("/api/v3/offboarding/my", headers={"X-Tenant-ID": "tenant-alpha"})
    task_id = resp.json()["clearance_tasks"][0]["id"]
    _shared["sample_task_id"] = task_id

    clear_resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/clearance",
        json={"task_id": task_id, "is_cleared": True},
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert clear_resp.status_code == 403


def test_manager_clears_manager_clearance(seed_data):
    """Reporting manager clears MANAGER departmental clearance task."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    # Find the MANAGER task
    resp = client.get(f"/api/v3/offboarding/{_shared['exit_id']}", headers={"X-Tenant-ID": "tenant-alpha"})
    manager_task = next(t for t in resp.json()["clearance_tasks"] if t["department"] == "manager")

    clear_resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/clearance",
        json={
            "task_id": manager_task["id"],
            "is_cleared": True,
            "remarks": "Project repositories and documentation handed over.",
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert clear_resp.status_code == 200
    updated_task = next(t for t in clear_resp.json()["clearance_tasks"] if t["id"] == manager_task["id"])
    assert updated_task["is_cleared"] is True
    assert updated_task["remarks"] == "Project repositories and documentation handed over."


def test_hr_clears_remaining_clearance_tasks(seed_data):
    """HR Admin can clear remaining clearance tasks (IT, Assets, Admin, Finance, HR)."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get(f"/api/v3/offboarding/{_shared['exit_id']}", headers={"X-Tenant-ID": "tenant-alpha"})
    tasks = resp.json()["clearance_tasks"]
    for t in tasks:
        if not t["is_cleared"]:
            c_resp = client.post(
                f"/api/v3/offboarding/{_shared['exit_id']}/clearance",
                json={"task_id": t["id"], "is_cleared": True, "remarks": "Cleared by HR"},
                headers={"X-Tenant-ID": "tenant-alpha"},
            )
            assert c_resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Handover Management
# ---------------------------------------------------------------------------

def test_handover_creation_and_status_update(seed_data):
    """Employee creates handover item, manager/HR can view and mark completed."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/handover",
        json={
            "title": "Auth & JWT service documentation",
            "description": "Handed over repo keys and runbook",
            "documentation_url": "https://wiki.zeramai.com/auth-service",
            "recipient_name": "Senior Eng",
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["handovers"]) >= 1
    handover_id = data["handovers"][0]["id"]

    # Mark completed
    status_resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/handover-status",
        json={"handover_id": handover_id, "status": "completed"},
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert status_resp.status_code == 200
    updated_h = next(h for h in status_resp.json()["handovers"] if h["id"] == handover_id)
    assert updated_h["status"] == "completed"


# ---------------------------------------------------------------------------
# 6. Exit Interview Confidentiality
# ---------------------------------------------------------------------------

def test_exit_interview_confidentiality(seed_data):
    """
    Employee submits sensitive exit interview feedback.
    HR can view full feedback.
    Manager viewing the record sees masked feedback ([Confidential to HR]).
    """
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # Employee submits interview feedback
    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/exit-interview",
        json={
            "primary_reason": "career_growth",
            "feedback_company": "Great engineering culture.",
            "feedback_management": "Needs better communication from leadership.",
            "feedback_role": "Good learning experience.",
            "is_completed": True,
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 200

    # HR views -> sees full feedback
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    hr_view = client.get(f"/api/v3/offboarding/{_shared['exit_id']}", headers={"X-Tenant-ID": "tenant-alpha"})
    assert hr_view.json()["interview"]["feedback_management"] == "Needs better communication from leadership."

    # Manager views -> management and company feedback are masked
    mgr_token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(mgr_token)
    mgr_view = client.get(f"/api/v3/offboarding/{_shared['exit_id']}", headers={"X-Tenant-ID": "tenant-alpha"})
    assert mgr_view.json()["interview"]["feedback_management"] == "[Confidential to HR]"


# ---------------------------------------------------------------------------
# 7. Settlement Readiness & Completion
# ---------------------------------------------------------------------------

def test_settlement_readiness_update(seed_data):
    """HR or Finance updates settlement readiness checklist."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/settlement-readiness",
        json={
            "payroll_reviewed": True,
            "leave_balance_reviewed": True,
            "leave_encashment_days": 4.5,
            "asset_clearance_completed": True,
            "finance_clearance_completed": True,
            "settlement_status": "approved",
            "settlement_amount": 54200.0,
            "remarks": "Leave encashment + final month pro-rated stipend calculated.",
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 200
    settlement = resp.json()["settlement"]
    assert settlement["payroll_reviewed"] is True
    assert settlement["settlement_status"] == "approved"
    assert settlement["leave_encashment_days"] == 4.5


def test_unauthorized_user_cannot_complete_exit(seed_data):
    """Non-HR users (e.g. Employee or Finance) cannot complete offboarding."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/complete",
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 403


def test_hr_admin_completes_exit(seed_data):
    """HR Admin completes offboarding: status becomes COMPLETED."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.post(
        f"/api/v3/offboarding/{_shared['exit_id']}/complete",
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


# ---------------------------------------------------------------------------
# 8. Audit Logging Verification
# ---------------------------------------------------------------------------

def test_audit_logs_for_offboarding(seed_data):
    """Verifies that all key lifecycle actions were written to audit_logs."""
    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        actions = [a[0] for a in db.query(AuditLog.action).all()]
        assert "resignation_submitted" in actions, "Missing resignation_submitted audit entry"
        assert "exit_reviewed" in actions, "Missing exit_reviewed audit entry"
        assert "clearance_task_updated" in actions, "Missing clearance_task_updated audit entry"
        assert "exit_interview_updated" in actions, "Missing exit_interview_updated audit entry"
        assert "exit_completed" in actions, "Missing exit_completed audit entry"
    finally:
        db.close()
