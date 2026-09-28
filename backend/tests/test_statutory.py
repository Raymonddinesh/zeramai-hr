"""
Module 12: Statutory Framework, Rules, Registrations, Filings and Payments Tests.
"""
import os
import pytest
from datetime import date, timedelta
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


def test_list_statutory_schemes(seed_data):
    """List supported statutory schemes."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/statutory/schemes")
    assert resp.status_code == 200
    schemes = resp.json()
    assert "epf" in schemes
    assert "esi" in schemes
    assert "professional_tax" in schemes
    assert "tds" in schemes


def test_create_and_manage_statutory_rule(seed_data):
    """HR creates an effective-dated statutory rule and updates it."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create rule
    resp = client.post("/api/v3/statutory/rules", json={
        "authority": "epfo",
        "scheme": "epf",
        "effective_from": "2026-04-01",
        "effective_to": "2027-03-31",
        "config": {
            "employee_rate": 12.0,
            "employer_rate": 12.0,
            "wage_ceiling": 15000.0,
        },
        "description": "FY26-27 Standard EPF rule",
    })
    assert resp.status_code == 201, f"Failed to create rule: {resp.text}"
    rule = resp.json()
    assert rule["scheme"] == "epf"
    assert rule["authority"] == "epfo"
    rule_id = rule["id"]
    _shared["rule_id"] = rule_id

    # 2. Get rule
    get_resp = client.get(f"/api/v3/statutory/rules/{rule_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["config"]["wage_ceiling"] == 15000.0

    # 3. Update rule description
    update_resp = client.patch(f"/api/v3/statutory/rules/{rule_id}", json={
        "description": "FY26-27 EPF rule updated",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "FY26-27 EPF rule updated"


def test_statutory_registration_lifecycle(seed_data):
    """HR creates a statutory registration (EPF code), verifies, and updates it."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create registration
    resp = client.post("/api/v3/statutory/registrations", json={
        "authority": "epfo",
        "registration_number": "KN/BNG/1234567/000",
        "state": "Karnataka",
        "effective_date": "2026-01-01",
        "status": "active",
        "verification_metadata": {"verified_by": "EPFO Portal"},
    })
    assert resp.status_code == 201, f"Failed to create registration: {resp.text}"
    reg = resp.json()
    assert reg["registration_number"] == "KN/BNG/1234567/000"
    reg_id = reg["id"]

    # 2. List registrations
    list_resp = client.get("/api/v3/statutory/registrations")
    assert list_resp.status_code == 200
    reg_ids = [r["id"] for r in list_resp.json()]
    assert reg_id in reg_ids

    # 3. Update registration
    up_resp = client.patch(f"/api/v3/statutory/registrations/{reg_id}", json={
        "status": "verified",
    })
    assert up_resp.status_code == 200
    assert up_resp.json()["status"] == "verified"


def test_statutory_filings_and_payments_lifecycle(seed_data):
    """Create a statutory filing (ECR), update its status, and record payment challan."""
    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)

    # 1. Create Filing
    filing_resp = client.post("/api/v3/statutory/filings", json={
        "authority": "epfo",
        "scheme": "epf",
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
        "due_date": "2026-11-15",
        "status": "ready",
        "reference_number": "ECR-2026-10-001",
    })
    assert filing_resp.status_code == 201, f"Failed to create filing: {filing_resp.text}"
    filing = filing_resp.json()
    filing_id = filing["id"]

    # 2. Finance user creates Payment for this filing
    token_fin = login(*CREDENTIALS["FINANCE"])
    set_auth(token_fin)

    pay_resp = client.post("/api/v3/statutory/payments", json={
        "filing_id": filing_id,
        "amount": 450000.0,
        "payment_date": "2026-11-14",
        "due_date": "2026-11-15",
        "reference_number": "CHALLAN-EPF-998877",
        "status": "paid",
    })
    assert pay_resp.status_code == 201, f"Failed to create payment: {pay_resp.text}"
    payment = pay_resp.json()
    assert payment["amount"] == 450000.0
    assert payment["status"] == "paid"

    # 3. Update filing to paid
    up_filing = client.patch(f"/api/v3/statutory/filings/{filing_id}", json={
        "status": "paid",
        "filed_date": "2026-11-14",
    })
    assert up_filing.status_code == 200
    assert up_filing.json()["status"] == "paid"
