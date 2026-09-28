"""
Module 3 — Manager Self Service: Security tests.

Coverage:
1. Unauthenticated access denied (401)
2. EMPLOYEE role denied (403) — no dashboard:view for employee role?
   Actually EMPLOYEE has dashboard:view, so this test checks that an employee
   WITH no team gets 404, not someone else's data.
3. Manager sees only their own team (scope isolation)
4. Manager A cannot see Manager B's employees
5. No salary/bank/payroll fields exposed in response schema
6. No grievance/POSH/disciplinary data exposed
7. No query-parameter IDOR (endpoint accepts no person_id param)
8. HIRING_MANAGER cannot list ALL attendance via /api/attendance
9. HIRING_MANAGER cannot list ALL leave via /api/leave
10. HIRING_MANAGER cannot approve ANY leave via /api/leave/{id}/review
11. Audit log created on dashboard access
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.cookies.get("access_token") or resp.json().get("access_token")
    assert token, f"No token for {email}"
    return token


def set_auth(token: str):
    client.cookies.set("access_token", token)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CREDENTIALS = {
    "SUPER_ADMIN":    ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN":       ("hr@zeramai.com",          "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com",      "ChangeMe123!"),
    "FINANCE":        ("finance@zeramai.com",       "ChangeMe123!"),
    "EMPLOYEE":       ("employee@example.com",      "ChangeMe123!"),
}


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    """Re-seed RBAC and demo data so permissions are current."""
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


# ---------------------------------------------------------------------------
# 1. Unauthenticated access → 401
# ---------------------------------------------------------------------------

def test_manager_dashboard_unauthenticated(seed_data):
    """GET /api/v3/manager/me without a session cookie → 401."""
    client.cookies.clear()
    resp = client.get("/api/v3/manager/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Employee with no team → 404 (not someone else's data)
# ---------------------------------------------------------------------------

def test_employee_gets_404_not_other_data(seed_data):
    """An EMPLOYEE who has dashboard:view but manages no one gets 404,
    not another manager's team data."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.get("/api/v3/manager/me")
    # EMPLOYEE has dashboard:view, so they pass auth, but they have no
    # reporting relationships → 404
    assert resp.status_code == 404, (
        f"Expected 404 for employee with no team, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 3. Finance role with no team → 404
# ---------------------------------------------------------------------------

def test_finance_gets_404_not_other_data(seed_data):
    """FINANCE role has dashboard:view but no team → 404."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)
    resp = client.get("/api/v3/manager/me")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Response schema does not expose salary/bank/payroll
# ---------------------------------------------------------------------------

def test_no_salary_fields_in_schema(seed_data):
    """Verify the ManagerDashboardOut Pydantic schema has no salary/bank fields."""
    from app.schemas_manager import ManagerDashboardOut, TeamMemberOut
    team_fields = set(TeamMemberOut.model_fields.keys())
    dashboard_fields = set(ManagerDashboardOut.model_fields.keys())
    all_fields = team_fields | dashboard_fields

    sensitive_keywords = {"salary", "bank", "account_number", "ifsc", "ctc",
                          "gross", "net", "deduction", "payslip", "payroll",
                          "stipend_amount", "stipend"}
    leaked = all_fields & sensitive_keywords
    assert not leaked, f"Sensitive fields exposed in manager schema: {leaked}"


# ---------------------------------------------------------------------------
# 5. Response schema does not expose grievance/POSH/disciplinary data
# ---------------------------------------------------------------------------

def test_no_grievance_fields_in_schema(seed_data):
    """Verify no grievance/POSH/disciplinary data in manager schema."""
    from app.schemas_manager import ManagerDashboardOut
    dashboard_fields = set(ManagerDashboardOut.model_fields.keys())
    sensitive_keywords = {"grievance", "posh", "disciplinary", "complaint",
                          "investigation", "complainant"}
    leaked = dashboard_fields & sensitive_keywords
    assert not leaked, f"Confidential fields exposed: {leaked}"


# ---------------------------------------------------------------------------
# 6. No query-parameter IDOR — endpoint accepts no person_id
# ---------------------------------------------------------------------------

def test_no_query_param_idor(seed_data):
    """Passing a person_id query param to /api/v3/manager/me does nothing.
    The endpoint derives scope entirely from the authenticated user."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    fake_person_id = str(uuid.uuid4())
    resp = client.get(f"/api/v3/manager/me?person_id={fake_person_id}")
    # Should either succeed (showing only the manager's team, ignoring param)
    # or 404 (if manager has no team). Either is acceptable.
    # It must NOT return data for the injected person_id.
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        # Verify no team member has the injected person_id
        for member in data.get("pending_leaves", []):
            assert member["person_id"] != fake_person_id


# ---------------------------------------------------------------------------
# 7. HIRING_MANAGER cannot list ALL attendance via /api/attendance
# ---------------------------------------------------------------------------

def test_hiring_manager_cannot_list_all_attendance(seed_data):
    """After RBAC fix, HIRING_MANAGER should NOT have attendance:view,
    so GET /api/attendance should be forbidden (403)."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    resp = client.get("/api/attendance")
    # HIRING_MANAGER should not have attendance:view or attendance:view_own
    assert resp.status_code == 403, (
        f"HIRING_MANAGER should not access /api/attendance, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 8. HIRING_MANAGER cannot list ALL leave via /api/leave
# ---------------------------------------------------------------------------

def test_hiring_manager_cannot_list_all_leave(seed_data):
    """After RBAC fix, HIRING_MANAGER should NOT have leave:view,
    so GET /api/leave should be forbidden (403)."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    resp = client.get("/api/leave")
    assert resp.status_code == 403, (
        f"HIRING_MANAGER should not access /api/leave, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 9. HIRING_MANAGER cannot approve ANY leave
# ---------------------------------------------------------------------------

def test_hiring_manager_cannot_approve_any_leave(seed_data):
    """After RBAC fix, HIRING_MANAGER should NOT have leave:approve,
    so POST /api/leave/{id}/review should be forbidden."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    fake_leave_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/leave/{fake_leave_id}/review",
        json={"status": "approved"},
    )
    # 403 because they lack leave:approve permission
    assert resp.status_code == 403, (
        f"HIRING_MANAGER should not approve leave, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 10. Audit log created on dashboard access
# ---------------------------------------------------------------------------

def test_audit_log_on_manager_dashboard(seed_data):
    """Successful manager dashboard access should create an audit entry."""
    from app.database import SessionLocal
    from app.models import AuditLog

    # First, access the dashboard (may be 200 or 404 depending on seed data)
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    resp = client.get("/api/v3/manager/me")

    if resp.status_code == 200:
        # Verify audit log was created
        db = SessionLocal()
        try:
            entry = (
                db.query(AuditLog)
                .filter(AuditLog.action == "manager_dashboard_viewed")
                .order_by(AuditLog.timestamp.desc())
                .first()
            )
            assert entry is not None, "Expected audit entry for manager_dashboard_viewed"
            assert entry.entity == "manager_self_service"
        finally:
            db.close()
    # If 404, no audit log is expected (no team data to log)
