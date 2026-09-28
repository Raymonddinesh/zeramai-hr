"""
Module 12: India TDS (Income Tax Withholding) & Declarations Tests.
"""
import os
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.adapters.india_statutory_adapter import TDSAdapter

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
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


def test_tds_new_regime_rebate_below_7l():
    """Under Section 115BAC New Regime, net taxable income <= ₹7,00,000 gets full 87A rebate.
    Annual CTC ₹6,00,000 -> Projected annual tax = ₹0.
    """
    db = SessionLocal()
    try:
        adapter = TDSAdapter(db)
        res = adapter.calculate(
            person_id="p-tds-1",
            as_of=date(2026, 10, 1),
            monthly_gross=50000.0,
            annual_ctc=600000.0,
        )
        assert res["scheme"] == "tds"
        assert res["regime"] == "new"
        assert res["projected_annual_tax"] == 0.0
        assert res["monthly_tds_deduction"] == 0.0
    finally:
        db.close()


def test_tds_new_regime_above_rebate():
    """Annual CTC ₹12,00,000.
    Standard deduction: ₹75,000.
    Net taxable: ₹11,25,000.
    Generates positive projected tax and monthly TDS.
    """
    db = SessionLocal()
    try:
        adapter = TDSAdapter(db)
        res = adapter.calculate(
            person_id="p-tds-2",
            as_of=date(2026, 10, 1),
            monthly_gross=100000.0,
            annual_ctc=1200000.0,
        )
        assert res["net_taxable_income"] == 1125000.0
        assert res["projected_annual_tax"] > 0
        assert res["monthly_tds_deduction"] > 0
    finally:
        db.close()


def test_employee_tax_declaration_submission_and_hr_verification(seed_data):
    """Employee submits tax declaration; HR reviews and verifies it."""
    # 1. Employee submits declaration
    token_emp = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token_emp)

    resp = client.post("/api/v3/tax/declarations", json={
        "financial_year": "2026-2027",
        "regime": "new",
        "projected_income": 1500000.0,
        "deductions_json": [],
    })
    assert resp.status_code == 201, f"Declaration submit failed: {resp.text}"
    decl = resp.json()
    assert decl["status"] == "submitted"
    assert decl["financial_year"] == "2026-2027"
    decl_id = decl["id"]
    _shared["decl_id"] = decl_id

    # 2. HR verifies the declaration
    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)

    verify_resp = client.patch(f"/api/v3/tax/declarations/{decl_id}", json={
        "action": "verify",
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "verified"
    assert verify_resp.json()["verified_by_id"] is not None
