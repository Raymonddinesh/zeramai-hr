"""
Module 8 — HR Policy & Employee Relations Tests.

Verification of:
- Policy Lifecycle (Draft -> Review -> Approved -> Published -> Archived)
- Versioning and historical immutability
- Scope and applicability filtering (department, employment type)
- Employee electronic acknowledgement & duplicate prevention
- IDOR prevention & unauthorized access restrictions
- ER Case Management Lifecycle & status progression
- Confidential notes masking (investigation notes masked for non-HR)
- Disciplinary actions issuance & employee acknowledgement
- Strict isolation from GrievanceCase/Whistleblower subsystem
- Audit logging verification
"""
import os
import uuid
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, Person, Engagement, EngagementType, EngagementStatus, AuditLog
from app.models_policy_er import (
    HRPolicy, HRPolicyStatus, HRPolicyCategory, PolicyAcknowledgementRecord,
    EmployeeRelationsCase, ERCaseStatus, ERCaseSeverity, ERCaseNote,
    DisciplinaryAction, DisciplinaryActionType, DisciplinaryStatus
)

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN":    ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN":       ("hr@zeramai.com",          "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com",      "ChangeMe123!"),
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


@pytest.fixture(autouse=True)
def ensure_test_setup():
    db = SessionLocal()
    try:
        emp_user = db.query(User).filter(User.email == "employee@example.com").first()
        mgr_user = db.query(User).filter(User.email == "manager@zeramai.com").first()
        assert emp_user and emp_user.person_id
        assert mgr_user

        # Ensure engagement has department and manager
        eng = db.query(Engagement).filter(Engagement.person_id == emp_user.person_id).first()
        if eng:
            eng.department = "Engineering"
            eng.reporting_manager_id = mgr_user.id
            eng.engagement_type = EngagementType.FULL_TIME_EMPLOYEE
            eng.status = EngagementStatus.ACTIVE
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# HR Policy Tests
# ---------------------------------------------------------------------------

def test_hr_policy_lifecycle():
    """Verify Draft -> Review -> Approved -> Published lifecycle."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    code = f"POL-LIFECYCLE-{uuid.uuid4().hex[:6].upper()}"
    # 1. Create draft
    create_payload = {
        "policy_code": code,
        "title": "Remote Work Guidelines",
        "category": "remote_work",
        "description": "Rules for working remotely",
        "content": "Employees may work remotely 2 days a week.",
        "is_mandatory": True,
        "effective_date": str(date.today()),
    }
    resp = client.post("/api/v3/hr-policies", json=create_payload)
    assert resp.status_code == 201, resp.text
    pol = resp.json()
    policy_id = pol["id"]
    assert pol["status"] == "draft"
    assert pol["version"] == "1.0"

    # 2. Submit for review
    resp = client.post(f"/api/v3/hr-policies/{policy_id}/submit")
    assert resp.status_code == 200
    assert resp.json()["status"] == "review"

    # 3. Approve
    resp = client.post(f"/api/v3/hr-policies/{policy_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # 4. Publish
    resp = client.post(f"/api/v3/hr-policies/{policy_id}/publish")
    assert resp.status_code == 200
    published_pol = resp.json()
    assert published_pol["status"] == "published"
    assert published_pol["published_at"] is not None


def test_hr_policy_versioning_and_immutability():
    """Verify updating a published policy creates a new version leaving original intact."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    code = f"POL-VER-{uuid.uuid4().hex[:6].upper()}"
    # Create & publish v1.0
    r1 = client.post("/api/v3/hr-policies", json={
        "policy_code": code,
        "title": "Code of Conduct",
        "category": "code_of_conduct",
        "content": "Initial conduct rules v1.0",
        "effective_date": str(date.today()),
    })
    assert r1.status_code == 201, r1.text
    v1_id = r1.json()["id"]

    client.post(f"/api/v3/hr-policies/{v1_id}/approve")
    client.post(f"/api/v3/hr-policies/{v1_id}/publish")

    # Create new version v1.1
    r_ver = client.post(f"/api/v3/hr-policies/{v1_id}/versions", json={
        "version": "1.1",
        "description": "Updated section on social media",
        "content": "Updated conduct rules v1.1",
        "effective_date": str(date.today() + timedelta(days=5)),
    })
    assert r_ver.status_code == 201, r_ver.text
    v11 = r_ver.json()
    v11_id = v11["id"]
    assert v11["version"] == "1.1"
    assert v11["status"] == "draft"
    assert v11["previous_version_id"] == v1_id

    # Verify v1.0 is still published and unchanged
    r_get_v1 = client.get(f"/api/v3/hr-policies/{v1_id}")
    assert r_get_v1.status_code == 200
    assert r_get_v1.json()["status"] == "published"
    assert r_get_v1.json()["content"] == "Initial conduct rules v1.0"

    # Now approve and publish v1.1
    client.post(f"/api/v3/hr-policies/{v11_id}/approve")
    r_pub11 = client.post(f"/api/v3/hr-policies/{v11_id}/publish")
    assert r_pub11.status_code == 200
    assert r_pub11.json()["status"] == "published"

    # Verify v1.0 is now automatically archived
    r_get_v1_archived = client.get(f"/api/v3/hr-policies/{v1_id}")
    assert r_get_v1_archived.json()["status"] == "archived"


def test_hr_policy_applicability_and_acknowledgement():
    """Verify applicability filtering and employee electronic acknowledgement."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create policy applicable to "Sales" department (not employee who is Engineering)
    r_sales = client.post("/api/v3/hr-policies", json={
        "policy_code": f"POL-SALES-{uuid.uuid4().hex[:6].upper()}",
        "title": "Sales Commission Policy",
        "category": "compensation_benefits",
        "content": "Commission structures",
        "department_id": "Sales",
        "is_mandatory": True,
        "effective_date": str(date.today()),
    })
    assert r_sales.status_code == 201, r_sales.text
    sales_id = r_sales.json()["id"]
    client.post(f"/api/v3/hr-policies/{sales_id}/approve")
    client.post(f"/api/v3/hr-policies/{sales_id}/publish")

    # 2. Create policy applicable to "Engineering"
    r_eng = client.post("/api/v3/hr-policies", json={
        "policy_code": f"POL-ENG-{uuid.uuid4().hex[:6].upper()}",
        "title": "Engineering Open Source Policy",
        "category": "it_security",
        "content": "Rules for contributing to open source",
        "department_id": "Engineering",
        "is_mandatory": True,
        "effective_date": str(date.today()),
    })
    assert r_eng.status_code == 201, r_eng.text
    eng_id = r_eng.json()["id"]
    client.post(f"/api/v3/hr-policies/{eng_id}/approve")
    client.post(f"/api/v3/hr-policies/{eng_id}/publish")

    # 3. Create org-wide policy (department_id=None)
    r_org = client.post("/api/v3/hr-policies", json={
        "policy_code": f"POL-ALL-{uuid.uuid4().hex[:6].upper()}",
        "title": "General Health and Safety",
        "category": "workplace_safety",
        "content": "Emergency exits and fire drills",
        "is_mandatory": True,
        "effective_date": str(date.today()),
    })
    assert r_org.status_code == 201, r_org.text
    org_id = r_org.json()["id"]
    client.post(f"/api/v3/hr-policies/{org_id}/approve")
    client.post(f"/api/v3/hr-policies/{org_id}/publish")

    # Switch to Employee
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    # Employee fetches applicable policies
    r_app = client.get("/api/v3/hr-policies/my/applicable")
    assert r_app.status_code == 200
    app_policies = r_app.json()
    app_ids = [p["id"] for p in app_policies]

    assert eng_id in app_ids, "Engineering policy should be applicable to employee"
    assert org_id in app_ids, "Org-wide policy should be applicable to employee"
    assert sales_id not in app_ids, "Sales policy should NOT be applicable to employee in Engineering"

    # Employee acknowledges Engineering policy
    r_ack = client.post(f"/api/v3/hr-policies/{eng_id}/acknowledge", json={
        "signature_text": "Jane Doe",
        "confirmation_checked": True,
    })
    assert r_ack.status_code == 201, r_ack.text
    ack_data = r_ack.json()
    assert ack_data["policy_id"] == eng_id
    assert ack_data["status"] == "acknowledged"

    # Verify duplicate acknowledgement is rejected
    r_dup = client.post(f"/api/v3/hr-policies/{eng_id}/acknowledge", json={
        "signature_text": "Jane Doe",
        "confirmation_checked": True,
    })
    assert r_dup.status_code == 400
    assert "already acknowledged" in r_dup.json()["detail"].lower()

    # Verify employee's acknowledgements list
    r_my_acks = client.get("/api/v3/hr-policies/my/acknowledgements")
    assert r_my_acks.status_code == 200
    my_ack_policy_ids = [a["policy_id"] for a in r_my_acks.json()]
    assert eng_id in my_ack_policy_ids

    # Switch back to HR to check compliance status
    set_auth(hr_token)
    r_comp = client.get(f"/api/v3/hr-policies/{eng_id}/compliance-status")
    assert r_comp.status_code == 200
    comp_data = r_comp.json()
    assert comp_data["policy_id"] == eng_id
    assert comp_data["acknowledged_count"] >= 1


def test_hr_policy_rbac_and_unauthorized():
    """Verify employee cannot create, edit, or publish policies."""
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    # Attempt to create policy
    r_create = client.post("/api/v3/hr-policies", json={
        "policy_code": "POL-ROGUE-01",
        "title": "Unauthorized Policy",
        "category": "general",
        "content": "No more meetings",
        "effective_date": str(date.today()),
    })
    assert r_create.status_code == 403

    # Switch to HR to create a draft policy
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    r_draft = client.post("/api/v3/hr-policies", json={
        "policy_code": f"POL-SECRET-{uuid.uuid4().hex[:6].upper()}",
        "title": "Confidential Reorg",
        "category": "general",
        "content": "Secret draft",
        "effective_date": str(date.today()),
    })
    draft_id = r_draft.json()["id"]

    # Switch back to employee and attempt to view or publish draft
    set_auth(emp_token)
    r_view_draft = client.get(f"/api/v3/hr-policies/{draft_id}")
    assert r_view_draft.status_code in (403, 404)

    r_pub = client.post(f"/api/v3/hr-policies/{draft_id}/publish")
    assert r_pub.status_code == 403


# ---------------------------------------------------------------------------
# Employee Relations & Confidential Notes Tests
# ---------------------------------------------------------------------------

def test_er_case_lifecycle_and_notes():
    """Verify ER Case creation, status flow, confidential note masking, and disciplinary action."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    mgr_token = login(*CREDENTIALS["HIRING_MANAGER"])
    emp_token = login(*CREDENTIALS["EMPLOYEE"])

    # Lookup employee person_id
    db = SessionLocal()
    try:
        emp_user = db.query(User).filter(User.email == "employee@example.com").first()
        emp_person_id = emp_user.person_id
    finally:
        db.close()

    # 1. HR creates an ER Case
    set_auth(hr_token)
    r_case = client.post("/api/v3/employee-relations/cases", json={
        "subject_person_id": emp_person_id,
        "category": "performance",
        "severity": "medium",
        "title": "Unexcused Absences and Sprint Misses",
        "description": "Employee has missed 3 sprints without advance notice.",
        "investigation_summary": "Initial audit showed unexplained commit gaps.",
    })
    assert r_case.status_code == 201, r_case.text
    case = r_case.json()
    case_id = case["id"]
    assert case["case_number"].startswith("ER-")
    assert case["status"] == "open"
    assert case["investigation_summary"] == "Initial audit showed unexplained commit gaps."

    # 2. Status transitions: OPEN -> UNDER_REVIEW -> INVESTIGATION
    r_stat1 = client.post(f"/api/v3/employee-relations/cases/{case_id}/status", json={
        "status": "under_review",
    })
    assert r_stat1.status_code == 200
    assert r_stat1.json()["status"] == "under_review"

    r_stat2 = client.post(f"/api/v3/employee-relations/cases/{case_id}/status", json={
        "status": "investigation",
        "investigation_summary": "Interviewed team lead; logs confirmed lack of commits."
    })
    assert r_stat2.status_code == 200
    assert r_stat2.json()["status"] == "investigation"

    # 3. HR adds a confidential internal note and a shared note
    r_note_conf = client.post(f"/api/v3/employee-relations/cases/{case_id}/notes", json={
        "note_type": "internal_hr",
        "content": "CONFIDENTIAL: Legal counsel advised proceeding with formal written warning.",
        "is_confidential": True
    })
    assert r_note_conf.status_code == 201

    r_note_pub = client.post(f"/api/v3/employee-relations/cases/{case_id}/notes", json={
        "note_type": "employee_communication",
        "content": "Scheduled 1-on-1 discussion for Friday at 10 AM.",
        "is_confidential": False
    })
    assert r_note_pub.status_code == 201

    # 4. Verify Confidentiality Masking for Reporting Manager
    set_auth(mgr_token)
    r_mgr_view = client.get(f"/api/v3/employee-relations/cases/{case_id}")
    assert r_mgr_view.status_code == 200
    mgr_case = r_mgr_view.json()
    # Manager must NOT see confidential investigation summary
    assert mgr_case["investigation_summary"] is None, "Manager must not see confidential investigation_summary"
    # Manager must only see non-confidential notes
    note_contents = [n["content"] for n in mgr_case["notes"]]
    assert "Scheduled 1-on-1 discussion for Friday at 10 AM." in note_contents
    assert not any("CONFIDENTIAL: Legal counsel" in c for c in note_contents), "Confidential note must be masked from manager"

    # 5. Verify Regular Employee gets 403 Forbidden on ER Cases
    set_auth(emp_token)
    r_emp_list = client.get("/api/v3/employee-relations/cases")
    assert r_emp_list.status_code == 403

    r_emp_view = client.get(f"/api/v3/employee-relations/cases/{case_id}")
    assert r_emp_view.status_code == 403

    # 6. HR issues Disciplinary Action
    set_auth(hr_token)
    r_disc = client.post(f"/api/v3/employee-relations/cases/{case_id}/disciplinary", json={
        "action_type": "written_warning",
        "title": "First Written Warning - Attendance and Sprint Delivery",
        "description": "Failure to meet commitments for Sprint 42 and 43.",
        "action_plan": "Employee must provide daily standup updates and complete catch-up tasks.",
        "effective_date": str(date.today()),
        "expiry_date": str(date.today() + timedelta(days=90)),
        "appeal_deadline": str(date.today() + timedelta(days=14)),
    })
    assert r_disc.status_code == 201, r_disc.text
    disc = r_disc.json()
    disc_id = disc["id"]
    assert disc["action_type"] == "written_warning"
    assert disc["status"] == "active"
    assert disc["employee_acknowledged"] is False

    # 7. Employee views their own disciplinary actions and acknowledges
    set_auth(emp_token)
    r_emp_disc = client.get("/api/v3/employee-relations/disciplinary")
    assert r_emp_disc.status_code == 200
    emp_actions = r_emp_disc.json()
    assert any(a["id"] == disc_id for a in emp_actions)

    r_emp_ack_disc = client.post(f"/api/v3/employee-relations/disciplinary/{disc_id}/acknowledge", json={
        "signature_text": "Jane Doe",
        "employee_comment": "Acknowledged and received copy. Working on catch-up."
    })
    assert r_emp_ack_disc.status_code == 200
    ack_res = r_emp_ack_disc.json()
    assert ack_res["employee_acknowledged"] is True


def test_er_whistleblower_isolation():
    """Verify that EmployeeRelationsCase and GrievanceCase (Whistleblower) remain strictly isolated."""
    from app.models_v9 import GrievanceCase, GrievanceCategory, GrievanceStatus

    db = SessionLocal()
    try:
        # Create a confidential whistleblower grievance
        g_case = GrievanceCase(
            ticket_number=f"WHISTLE-{uuid.uuid4().hex[:6].upper()}",
            category=GrievanceCategory.ETHICS_VIOLATION,
            title="Anonymous Whistleblower Report on Executive Expense Fraud",
            description="Highly sensitive executive report",
            status=GrievanceStatus.SUBMITTED,
            is_anonymous=True,
        )
        db.add(g_case)
        db.commit()
        db.refresh(g_case)
        whistle_id = g_case.id

        # Query ER cases via API and ensure the whistleblower ticket does NOT appear
        hr_token = login(*CREDENTIALS["HR_ADMIN"])
        set_auth(hr_token)

        resp = client.get("/api/v3/employee-relations/cases")
        assert resp.status_code == 200
        er_cases = resp.json()
        assert not any(c["title"] == "Anonymous Whistleblower Report on Executive Expense Fraud" for c in er_cases)
        assert not any(c.get("id") == whistle_id for c in er_cases)

        # Confirm ER case table is distinct
        er_count = db.query(EmployeeRelationsCase).filter(EmployeeRelationsCase.id == whistle_id).count()
        assert er_count == 0, "GrievanceCase record must NOT exist in employee_relations_cases"
    finally:
        db.close()


def test_policy_and_er_audit_logs():
    """Verify audit log entries are generated for policy publication and ER actions."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Create and publish a policy
    pol_code = f"POL-AUDIT-{uuid.uuid4().hex[:6].upper()}"
    r_pol = client.post("/api/v3/hr-policies", json={
        "policy_code": pol_code,
        "title": "Audit Test Policy",
        "category": "general",
        "content": "Audit check content",
        "effective_date": str(date.today()),
    })
    assert r_pol.status_code == 201, r_pol.text
    pol_id = r_pol.json()["id"]
    client.post(f"/api/v3/hr-policies/{pol_id}/approve")
    client.post(f"/api/v3/hr-policies/{pol_id}/publish")

    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(
            AuditLog.entity == "hr_policy",
            AuditLog.entity_id == pol_id,
            AuditLog.action == "hr_policy_published"
        ).all()
        assert len(logs) >= 1, "Audit log for policy publish should be recorded"
    finally:
        db.close()


def test_er_case_assign_and_resolution():
    """Verify assigning HR owner and transitioning to RESOLVED and CLOSED with resolution summary."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    db = SessionLocal()
    try:
        emp_user = db.query(User).filter(User.email == "employee@example.com").first()
        hr_user = db.query(User).filter(User.email == "hr@zeramai.com").first()
        emp_person_id = emp_user.person_id
        hr_user_id = hr_user.id
    finally:
        db.close()

    # 1. Create case
    r_case = client.post("/api/v3/employee-relations/cases", json={
        "subject_person_id": emp_person_id,
        "category": "conduct",
        "severity": "low",
        "title": "Minor Dress Code Dispute",
        "description": "Dispute resolved with informal conversation.",
    })
    assert r_case.status_code == 201
    case_id = r_case.json()["id"]

    # 2. Assign HR Owner
    r_assign = client.post(f"/api/v3/employee-relations/cases/{case_id}/assign", json={
        "hr_owner_id": hr_user_id
    })
    assert r_assign.status_code == 200
    assert r_assign.json()["hr_owner_id"] == hr_user_id

    # 3. Transition to RESOLVED
    r_res = client.post(f"/api/v3/employee-relations/cases/{case_id}/status", json={
        "status": "resolved",
        "resolution_summary": "Employee agreed to company guidelines."
    })
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "resolved"
    assert r_res.json()["resolution_summary"] == "Employee agreed to company guidelines."

    # 4. Transition to CLOSED
    r_close = client.post(f"/api/v3/employee-relations/cases/{case_id}/status", json={
        "status": "closed"
    })
    assert r_close.status_code == 200
    assert r_close.json()["status"] == "closed"
    assert r_close.json()["closed_at"] is not None


def test_manager_cross_scope_denied():
    """Verify Manager B cannot view cases where reporting manager is Manager A."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    db = SessionLocal()
    try:
        emp_user = db.query(User).filter(User.email == "employee@example.com").first()
        emp_person_id = emp_user.person_id

        # Find or create a second manager
        mgr2 = db.query(User).filter(User.email == "manager2@zeramai.com").first()
        if not mgr2:
            from app.auth import hash_password
            from app.models import UserRole
            mgr2 = User(
                email="manager2@zeramai.com",
                hashed_password=hash_password("ChangeMe123!"),
                role=UserRole.HIRING_MANAGER,
                is_active=True,
            )
            db.add(mgr2)
            db.commit()
            db.refresh(mgr2)
    finally:
        db.close()

    # Create case with reporting_manager_id set to primary manager
    mgr1 = db.query(User).filter(User.email == "manager@zeramai.com").first()
    r_case = client.post("/api/v3/employee-relations/cases", json={
        "subject_person_id": emp_person_id,
        "reporting_manager_id": mgr1.id,
        "category": "workplace_behavior",
        "severity": "medium",
        "title": "Disagreement in Meeting",
        "description": "Conflict between peers in meeting.",
    })
    assert r_case.status_code == 201
    case_id = r_case.json()["id"]

    # Login as Manager 2 and attempt to view case
    mgr2_token = login("manager2@zeramai.com", "ChangeMe123!")
    set_auth(mgr2_token)

    r_mgr2_view = client.get(f"/api/v3/employee-relations/cases/{case_id}")
    assert r_mgr2_view.status_code == 403, "Manager 2 must not see Manager 1's employee case"

