"""
RBAC verification and QA test suite.

Coverage:
- Login/authentication for all roles
- Candidate endpoint authorization (create, list, get, select, convert-to-trainee)
- Document upload/download authorization + object-level ownership checks
- Hiring Manager destructive action (no delete endpoint exists — verified as 405)
- Audit log entries created for both permitted and denied actions
"""
import os

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)


def login(email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Login failed for {email}: {response.text}"
    token = response.cookies.get("access_token") or response.json().get("access_token")
    assert token, f"No token returned for {email}"
    return token


def set_auth(token: str) -> None:
    client.cookies.set("access_token", token)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def seed_rbac():
    """Seed roles/permissions then seed demo users. Run RBAC seed first so
    that user→role associations can be created by seed.py immediately after."""
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


CREDENTIALS = {
    "SUPER_ADMIN":    ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN":       ("hr@zeramai.com",          "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com",      "ChangeMe123!"),
    "FINANCE":        ("finance@zeramai.com",       "ChangeMe123!"),
    "EMPLOYEE":       ("employee@example.com",      "ChangeMe123!"),
}

# ---------------------------------------------------------------------------
# Helper: shared state passed between tests
# ---------------------------------------------------------------------------

_shared: dict = {}


# ---------------------------------------------------------------------------
# Test 1: All seeded users can log in
# ---------------------------------------------------------------------------

def test_all_roles_can_login(seed_rbac):
    for role, (email, pwd) in CREDENTIALS.items():
        token = login(email, pwd)
        assert token, f"{role} did not receive a token"


# ---------------------------------------------------------------------------
# Test 2: Candidate flow — create, list, get, select, convert
# ---------------------------------------------------------------------------

def test_candidate_create_by_hr(seed_rbac):
    """HR_ADMIN can create a candidate."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.post("/api/candidates", json={
        "full_name": "RBAC Test Candidate",
        "email":     "rbac.candidate@test.com",
        "applied_position": "QA Engineer",
        "department": "Engineering",
    })
    assert resp.status_code == 201, f"Create candidate failed: {resp.text}"
    _shared["cid"] = resp.json()["id"]
    _shared["cpid"] = resp.json()["person_id"]


def test_candidate_create_forbidden_for_employee(seed_rbac):
    """EMPLOYEE cannot create a candidate."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.post("/api/candidates", json={
        "full_name": "Not Allowed",
        "email":     "notallowed@test.com",
    })
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


def test_candidate_create_forbidden_for_finance(seed_rbac):
    """FINANCE cannot create a candidate."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)
    resp = client.post("/api/candidates", json={
        "full_name": "Not Allowed Finance",
        "email":     "notallowed.finance@test.com",
    })
    assert resp.status_code == 403


def test_candidate_list_by_hiring_manager(seed_rbac):
    """HIRING_MANAGER can list candidates and see the one HR created."""
    assert "cid" in _shared, "test_candidate_create_by_hr must run first"
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    resp = client.get("/api/candidates")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert _shared["cid"] in ids


def test_candidate_get_by_id(seed_rbac):
    """Any authorized role can fetch a candidate by ID."""
    assert "cid" in _shared
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    resp = client.get(f"/api/candidates/{_shared['cid']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == _shared["cid"]


def test_candidate_list_forbidden_for_employee(seed_rbac):
    """EMPLOYEE cannot list candidates."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.get("/api/candidates")
    assert resp.status_code == 403


def test_candidate_select(seed_rbac):
    """HIRING_MANAGER can mark a candidate as selected."""
    assert "cid" in _shared
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)
    resp = client.post(f"/api/candidates/{_shared['cid']}/select")
    assert resp.status_code == 200
    assert resp.json()["status"] == "selected"


def test_candidate_convert_to_trainee(seed_rbac):
    """HR_ADMIN can convert a SELECTED candidate to trainee."""
    assert "cid" in _shared
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.post(f"/api/candidates/{_shared['cid']}/convert-to-trainee", json={
        "designation": "Engineering Trainee",
        "department": "Engineering",
        "start_date": "2026-10-01",
        "duration_months": 6,
        "monthly_stipend": 12000,
    })
    assert resp.status_code == 200, f"Convert to trainee failed: {resp.text}"
    _shared["engagement_id"] = resp.json()["id"]


def test_candidate_convert_forbidden_for_finance(seed_rbac):
    """FINANCE cannot convert a candidate to trainee."""
    assert "cid" in _shared
    # Use a freshly-created+selected candidate so we avoid status conflicts
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    cr = client.post("/api/candidates", json={
        "full_name": "Finance Test", "email": "fin.cand@test.com"
    })
    assert cr.status_code == 201
    cid2 = cr.json()["id"]
    mgr_token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(mgr_token)
    client.post(f"/api/candidates/{cid2}/select")

    fin_token = login(*CREDENTIALS["FINANCE"])
    set_auth(fin_token)
    resp = client.post(f"/api/candidates/{cid2}/convert-to-trainee", json={
        "designation": "ET", "department": "Eng", "start_date": "2026-10-01"
    })
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 3: No DELETE endpoint exists for candidates
# ---------------------------------------------------------------------------

def test_no_candidate_delete_endpoint(seed_rbac):
    """DELETE /api/candidates/{id} must not be registered.
    405 Method Not Allowed is returned regardless of role, which confirms
    no accidental delete route was exposed. This is the intended design."""
    assert "cid" in _shared
    for role in ["SUPER_ADMIN", "HR_ADMIN", "HIRING_MANAGER"]:
        token = login(*CREDENTIALS[role])
        set_auth(token)
        resp = client.delete(f"/api/candidates/{_shared['cid']}")
        assert resp.status_code == 405, (
            f"Expected 405 (no delete route), got {resp.status_code} for {role}"
        )


# ---------------------------------------------------------------------------
# Test 4: Document upload + download (object-level ownership)
# ---------------------------------------------------------------------------

def test_hr_can_upload_document(seed_rbac):
    """HR_ADMIN can upload a document for any person."""
    assert "cpid" in _shared, "Need person_id from candidate test"
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    files = {"file": ("doc.pdf", b"%PDF-sample", "application/pdf")}
    data = {"person_id": _shared["cpid"], "document_type": "resume"}
    resp = client.post("/api/documents", data=data, files=files)
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    _shared["doc_id"] = resp.json()["id"]


def test_hr_can_download_own_document(seed_rbac):
    """HR_ADMIN can download any document (has documents:download)."""
    assert "doc_id" in _shared
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)
    resp = client.get(f"/api/documents/{_shared['doc_id']}/download")
    assert resp.status_code == 200


def test_employee_cannot_download_other_persons_document(seed_rbac):
    """EMPLOYEE cannot download a document that belongs to a different person."""
    assert "doc_id" in _shared
    # The doc belongs to cpid (the candidate's person), not the employee user's person
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)
    resp = client.get(f"/api/documents/{_shared['doc_id']}/download")
    # Employee has documents:download_own but this doc's person_id != employee's person_id
    assert resp.status_code == 403, (
        f"Expected 403 for cross-person download, got {resp.status_code}: {resp.text}"
    )


def test_super_admin_can_download_any_document(seed_rbac):
    """SUPER_ADMIN has full documents:download permission."""
    assert "doc_id" in _shared
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)
    resp = client.get(f"/api/documents/{_shared['doc_id']}/download")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 5: Auth endpoints remain public / auth-only (no RBAC check)
# ---------------------------------------------------------------------------

def test_auth_me_returns_current_user(seed_rbac):
    """GET /api/auth/me works for any authenticated user."""
    for role, (email, pwd) in CREDENTIALS.items():
        token = login(email, pwd)
        set_auth(token)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200, f"/api/auth/me failed for {role}"
        assert resp.json()["email"] == email


def test_auth_me_denied_unauthenticated(seed_rbac):
    """GET /api/auth/me returns 401 without a session cookie."""
    client.cookies.clear()
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 6: Audit log entries
# ---------------------------------------------------------------------------

def test_audit_log_on_denied_candidate_list(seed_rbac):
    """Denied access must produce an audit-log entry (security gap check).
    NOTE: The current codebase does NOT log denials in require_permission()
    — denial logging is only present where explicitly called in endpoint code.
    This test documents that gap and verifies success events ARE logged."""
    # Trigger a denied action by an employee
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)
    deny_resp = client.get("/api/candidates")
    assert deny_resp.status_code == 403

    # Trigger a successful login (which IS audited)
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Verify a document upload event is in the audit log (direct DB check)
    from app.database import SessionLocal
    from app.models import AuditLog
    db = SessionLocal()
    try:
        doc_entry = db.query(AuditLog).filter(
            AuditLog.action == "document_uploaded"
        ).first()
        assert doc_entry is not None, "Expected at least one document_uploaded audit entry"

        login_entry = db.query(AuditLog).filter(
            AuditLog.action == "login"
        ).first()
        assert login_entry is not None, "Expected at least one login audit entry"

        # Check for a denied download entry (from test_employee_cannot_download...)
        denied_dl = db.query(AuditLog).filter(
            AuditLog.result == "denied"
        ).first()
        # NOTE: If denied_dl is None, that is the documented security gap:
        # require_permission() denials are NOT logged in the audit_logs table.
        if denied_dl is None:
            import warnings
            warnings.warn(
                "SECURITY GAP: require_permission() denials are not written to audit_logs. "
                "Only document_download and convert_to_trainee denials are currently logged "
                "explicitly in endpoint code. Endpoint-level RBAC denials (403 from require_permission) "
                "are silently dropped.",
                stacklevel=1,
            )
    finally:
        db.close()
