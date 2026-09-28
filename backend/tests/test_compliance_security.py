"""
Module 12: Compliance & Statutory Security, RBAC, IDOR, Anti-Self-Approval and Audit Log Tests.
"""
import os
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com", "ChangeMe123!"),
    "FINANCE": ("finance@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
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


def test_employee_cannot_create_statutory_rule(seed_data):
    """Employee attempting to create statutory rule is rejected with 403."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post("/api/v3/statutory/rules", json={
        "authority": "epfo",
        "scheme": "epf",
        "effective_from": "2026-04-01",
        "config": {"employee_rate": 5.0},
    })
    assert resp.status_code == 403


def test_employee_cannot_modify_statutory_registrations(seed_data):
    """Employee attempting to create or modify registrations is rejected with 403."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post("/api/v3/statutory/registrations", json={
        "authority": "epfo",
        "registration_number": "HACK-123",
        "effective_date": "2026-01-01",
    })
    assert resp.status_code == 403


def test_tax_declaration_idor_protection(seed_data):
    """Employee A cannot access Employee B's tax declarations."""
    from app.database import SessionLocal
    from app.models import User, Person, UserRole
    from app.auth import hash_password

    # Setup Employee B
    db = SessionLocal()
    try:
        p2 = db.query(Person).filter(Person.email == "tax.emp2@test.com").first()
        if not p2:
            p2 = Person(full_name="Tax Employee Two", email="tax.emp2@test.com")
            db.add(p2)
            db.flush()
            u2 = User(
                email="tax.emp2@test.com",
                hashed_password=hash_password("ChangeMe123!"),
                role=UserRole.EMPLOYEE,
                person_id=p2.id,
                is_active=True,
            )
            db.add(u2)
            db.commit()
        _shared["emp2_person_id"] = p2.id
    finally:
        db.close()

    # Create declaration for Employee B using HR credentials
    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)
    decl_resp = client.post(f"/api/v3/tax/declarations?person_id={_shared['emp2_person_id']}", json={
        "financial_year": "2026-2027",
        "regime": "new",
        "projected_income": 900000.0,
    })
    assert decl_resp.status_code == 201
    emp2_decl_id = decl_resp.json()["id"]

    # Employee 1 logs in and attempts to access Employee 2's declaration
    token_emp1 = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token_emp1)

    # 1. Attempt IDOR by querying with person_id filter
    filter_resp = client.get(f"/api/v3/tax/declarations?person_id={_shared['emp2_person_id']}")
    assert filter_resp.status_code == 403

    # 2. Attempt IDOR by querying declaration directly by id
    direct_resp = client.get(f"/api/v3/tax/declarations/{emp2_decl_id}")
    assert direct_resp.status_code == 403


def test_anti_self_approval_on_tax_declaration(seed_data):
    """User cannot review / verify their own tax declaration."""
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        hr_user = db.query(User).filter(User.email == CREDENTIALS["HR_ADMIN"][0]).first()
        hr_person_id = hr_user.person_id
    finally:
        db.close()

    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)

    # HR creates declaration for themselves
    decl_resp = client.post(f"/api/v3/tax/declarations?person_id={hr_person_id}", json={
        "financial_year": "2026-2027",
        "regime": "old",
        "projected_income": 2000000.0,
    })
    assert decl_resp.status_code == 201
    hr_decl_id = decl_resp.json()["id"]

    # HR tries to self-approve / self-verify
    verify_resp = client.patch(f"/api/v3/tax/declarations/{hr_decl_id}", json={
        "action": "verify",
    })
    assert verify_resp.status_code == 403
    assert "Self-approval prohibited" in verify_resp.text


def test_cross_tenant_statutory_isolation(seed_data):
    """Cross-tenant requests return 403 Forbidden."""
    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)

    # Create rule in tenant-alpha
    create_resp = client.post(
        "/api/v3/statutory/rules",
        json={
            "authority": "epfo",
            "scheme": "epf",
            "effective_from": "2026-04-01",
            "config": {"employee_rate": 12.0},
        },
        headers={"X-Tenant-ID": "tenant-alpha"},
    )
    assert create_resp.status_code == 201
    alpha_rule_id = create_resp.json()["id"]

    # Access rule using tenant-beta
    access_resp = client.get(
        f"/api/v3/statutory/rules/{alpha_rule_id}",
        headers={"X-Tenant-ID": "tenant-beta"},
    )
    assert access_resp.status_code == 403


def test_audit_logs_recorded_for_statutory_and_tax(seed_data):
    """Critical statutory and tax events are recorded in audit_logs."""
    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        actions = [a[0] for a in db.query(AuditLog.action).all()]
        assert "statutory_rule_created" in actions
        assert "tax_declaration_submitted" in actions
    finally:
        db.close()
