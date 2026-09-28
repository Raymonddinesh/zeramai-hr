"""
Module 4 — HR Service Desk: Security + functional tests.

Coverage:
1.  Employee creates HR request (ownership server-derived)
2.  Employee sees own request
3.  Employee cannot see another employee's request (IDOR)
4.  Employee cannot modify another employee's request
5.  Employee cannot create internal HR notes
6.  Employee can close own resolved request
7.  Unauthorized user cannot manage/assign/resolve requests
8.  HR can view all requests
9.  HR can assign requests
10. HR can change status
11. HR can resolve requests
12. HR can add internal notes (hidden from employee)
13. Internal HR notes hidden from employee view
14. Audit logging on create/assign/status/resolve/comment
15. Existing Module 2 + 3 tests remain passing (run full suite)
"""
import os
import uuid

import pytest
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
# 1. Employee creates HR request
# ---------------------------------------------------------------------------

def test_employee_creates_hr_request(seed_data):
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post("/api/v3/hr-requests", json={
        "category": "payroll",
        "priority": "medium",
        "subject": "Salary slip query",
        "description": "I need my salary slip for September 2026.",
    })
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    data = resp.json()
    assert data["ticket_number"].startswith("HR-")
    assert data["status"] == "open"
    assert data["category"] == "payroll"
    _shared["emp_request_id"] = data["id"]
    _shared["emp_request_requester_id"] = data["requester_user_id"]


# ---------------------------------------------------------------------------
# 2. Employee sees own request
# ---------------------------------------------------------------------------

def test_employee_sees_own_request(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.get(f"/api/v3/hr-requests/{_shared['emp_request_id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == _shared["emp_request_id"]


def test_employee_lists_own_requests(seed_data):
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.get("/api/v3/hr-requests")
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert _shared["emp_request_id"] in ids


# ---------------------------------------------------------------------------
# 3. Employee cannot see another employee's request (IDOR)
# ---------------------------------------------------------------------------

def test_employee_cannot_see_other_request(seed_data):
    """Create request as HR, then try to read it as EMPLOYEE."""
    # HR creates a request (on behalf of self, which means HR's user_id owns it)
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    resp = client.post("/api/v3/hr-requests", json={
        "category": "general_hr",
        "subject": "HR internal test",
        "description": "Testing HR request creation.",
    })
    assert resp.status_code == 201
    hr_request_id = resp.json()["id"]
    _shared["hr_owned_request_id"] = hr_request_id

    # Employee tries to access HR's request
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)
    resp = client.get(f"/api/v3/hr-requests/{hr_request_id}")
    assert resp.status_code == 403, (
        f"Employee should not access HR's request, got {resp.status_code}"
    )


def test_cross_tenant_access_denied(seed_data):
    """Requests belonging to tenant-A cannot be accessed by requests with tenant-B context."""
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    # Create request in tenant-alpha
    resp = client.post(
        "/api/v3/hr-requests",
        json={
            "category": "it_access",
            "subject": "Alpha tenant ticket",
            "description": "Cross tenant test request",
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert resp.status_code == 201
    alpha_ticket_id = resp.json()["id"]

    # Try to access using tenant-beta
    resp = client.get(
        f"/api/v3/hr-requests/{alpha_ticket_id}",
        headers={"X-Tenant-ID": "tenant-beta"},
    )
    assert resp.status_code == 403, (
        f"Expected 403 for cross-tenant request access, got {resp.status_code}"
    )

    # Try to mutate status using tenant-beta
    resp = client.post(
        f"/api/v3/hr-requests/{alpha_ticket_id}/status",
        json={"status": "in_progress"},
        headers={"X-Tenant-ID": "tenant-beta"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. Employee cannot modify another employee's request
# ---------------------------------------------------------------------------

def test_employee_cannot_change_status_of_other_request(seed_data):
    assert "hr_owned_request_id" in _shared
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['hr_owned_request_id']}/status",
        json={"status": "closed"},
    )
    assert resp.status_code == 403


def test_employee_cannot_comment_on_other_request(seed_data):
    assert "hr_owned_request_id" in _shared
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['hr_owned_request_id']}/comments",
        json={"content": "Snooping attempt"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 5. Employee cannot create internal HR notes
# ---------------------------------------------------------------------------

def test_employee_cannot_create_internal_note(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/comments",
        json={"content": "Trying internal", "is_internal": True},
    )
    assert resp.status_code == 403, (
        f"Employee should not create internal notes, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 6. Unauthorized user (FINANCE) cannot manage requests
# ---------------------------------------------------------------------------

def test_finance_cannot_assign_request(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/assign",
        json={"assigned_to_user_id": "fake-id"},
    )
    assert resp.status_code == 403


def test_finance_cannot_resolve_request(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/resolve",
        json={"resolution": "Unauthorized attempt"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7. HR can view all requests
# ---------------------------------------------------------------------------

def test_hr_can_view_all_requests(seed_data):
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.get("/api/v3/hr-requests")
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    # Should see both employee's and HR's own request
    assert _shared["emp_request_id"] in ids
    assert _shared["hr_owned_request_id"] in ids


# ---------------------------------------------------------------------------
# 8. HR can assign requests
# ---------------------------------------------------------------------------

def test_hr_can_assign_request(seed_data):
    assert "emp_request_id" in _shared
    # Get an HR user ID to assign to
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    me = client.get("/api/auth/me")
    hr_user_id = me.json()["id"]

    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/assign",
        json={"assigned_to_user_id": hr_user_id},
    )
    assert resp.status_code == 200, f"Assign failed: {resp.text}"
    data = resp.json()
    assert data["assigned_to_user_id"] == hr_user_id
    assert data["status"] == "assigned"
    assert data["first_response_at"] is not None


# ---------------------------------------------------------------------------
# 9. HR can change status
# ---------------------------------------------------------------------------

def test_hr_can_change_status(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/status",
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


# ---------------------------------------------------------------------------
# 10. HR can resolve requests
# ---------------------------------------------------------------------------

def test_hr_can_resolve_request(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/resolve",
        json={"resolution": "Salary slip has been emailed to the employee."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolution"] == "Salary slip has been emailed to the employee."
    assert data["resolved_at"] is not None


# ---------------------------------------------------------------------------
# 11. HR can add internal notes (hidden from employee)
# ---------------------------------------------------------------------------

def test_hr_can_add_internal_note(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/comments",
        json={"content": "Internal: checked payroll system", "is_internal": True},
    )
    assert resp.status_code == 201
    assert resp.json()["is_internal"] is True
    _shared["internal_comment_id"] = resp.json()["id"]


# ---------------------------------------------------------------------------
# 12. Internal HR notes hidden from employee view
# ---------------------------------------------------------------------------

def test_internal_notes_hidden_from_employee(seed_data):
    assert "emp_request_id" in _shared
    assert "internal_comment_id" in _shared
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.get(f"/api/v3/hr-requests/{_shared['emp_request_id']}")
    assert resp.status_code == 200
    comment_ids = [c["id"] for c in resp.json()["comments"]]
    assert _shared["internal_comment_id"] not in comment_ids, (
        "Internal HR note should be hidden from employee"
    )


def test_hr_sees_internal_notes(seed_data):
    assert "emp_request_id" in _shared
    assert "internal_comment_id" in _shared
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.get(f"/api/v3/hr-requests/{_shared['emp_request_id']}")
    assert resp.status_code == 200
    comment_ids = [c["id"] for c in resp.json()["comments"]]
    assert _shared["internal_comment_id"] in comment_ids, (
        "HR should see internal notes"
    )


# ---------------------------------------------------------------------------
# 13. Employee can close own resolved request
# ---------------------------------------------------------------------------

def test_employee_can_close_resolved_request(seed_data):
    assert "emp_request_id" in _shared
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post(
        f"/api/v3/hr-requests/{_shared['emp_request_id']}/status",
        json={"status": "closed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
    assert resp.json()["closed_at"] is not None


# ---------------------------------------------------------------------------
# 14. Employee cannot close a non-resolved request
# ---------------------------------------------------------------------------

def test_employee_cannot_close_non_resolved_request(seed_data):
    """Create a new request and try to close it directly (status=open)."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post("/api/v3/hr-requests", json={
        "category": "leave",
        "subject": "Leave balance query",
        "description": "How many leaves do I have?",
    })
    assert resp.status_code == 201
    new_id = resp.json()["id"]

    resp = client.post(
        f"/api/v3/hr-requests/{new_id}/status",
        json={"status": "closed"},
    )
    assert resp.status_code == 403, (
        f"Employee should not close non-resolved request, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 15. Unauthenticated access denied
# ---------------------------------------------------------------------------

def test_unauthenticated_access_denied(seed_data):
    client.cookies.clear()
    resp = client.get("/api/v3/hr-requests")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 16. Audit logging
# ---------------------------------------------------------------------------

def test_audit_log_for_hr_request_actions(seed_data):
    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        created = db.query(AuditLog).filter(AuditLog.action == "hr_request_created").first()
        assert created is not None, "Expected audit entry for hr_request_created"

        assigned = db.query(AuditLog).filter(AuditLog.action == "hr_request_assigned").first()
        assert assigned is not None, "Expected audit entry for hr_request_assigned"

        status_changed = db.query(AuditLog).filter(AuditLog.action == "hr_request_status_changed").first()
        assert status_changed is not None, "Expected audit entry for hr_request_status_changed"

        resolved = db.query(AuditLog).filter(AuditLog.action == "hr_request_resolved").first()
        assert resolved is not None, "Expected audit entry for hr_request_resolved"

        commented = db.query(AuditLog).filter(AuditLog.action == "hr_request_comment_added").first()
        assert commented is not None, "Expected audit entry for hr_request_comment_added"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 17. Filters work for HR
# ---------------------------------------------------------------------------

def test_hr_can_filter_by_status(seed_data):
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.get("/api/v3/hr-requests?status_filter=open")
    assert resp.status_code == 200
    for r in resp.json():
        assert r["status"] == "open"


def test_hr_can_filter_by_category(seed_data):
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.get("/api/v3/hr-requests?category_filter=payroll")
    assert resp.status_code == 200
    for r in resp.json():
        assert r["category"] == "payroll"
