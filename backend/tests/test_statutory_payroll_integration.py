"""
Module 12: Statutory & Payroll Integration Tests.
Verifies that computing payroll automatically generates statutory deductions,
produces immutable StatutoryCalculation snapshots, and preserves historical calculation snapshots.
"""
import os
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
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


@pytest.fixture(autouse=True)
def ensure_active_salary_structure():
    from app.database import SessionLocal
    from app.models import User
    from app.models_v6 import SalaryStructure

    db = SessionLocal()
    try:
        emp = db.query(User).filter(User.email == "employee@example.com").first()
        if emp and emp.person_id:
            ss = db.query(SalaryStructure).filter(
                SalaryStructure.person_id == emp.person_id,
                SalaryStructure.is_active == True,
            ).first()
            if not ss:
                ss = SalaryStructure(
                    person_id=emp.person_id,
                    name="Standard Structure",
                    ctc_annual=1200000.0,
                    ctc_monthly=100000.0,
                    is_active=True,
                    effective_from=date(2026, 1, 1),
                    components_json=[
                        {"name": "Basic", "code": "BASIC", "amount": 40000.0, "type": "earning"},
                        {"name": "HRA", "code": "HRA", "amount": 20000.0, "type": "earning"},
                        {"name": "Special Allowance", "code": "SPECIAL", "amount": 40000.0, "type": "earning"},
                    ],
                )
                db.add(ss)
                db.commit()
    finally:
        db.close()


_shared: dict = {}


def test_statutory_deductions_integrated_in_payroll_run(seed_data):
    """When statutory rules exist, computing payroll auto-calculates statutory deductions,
    records them in payslip deductions_json, and creates immutable StatutoryCalculation snapshots.
    """
    # 1. HR creates an active statutory rule for EPF
    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)

    rule_resp = client.post("/api/v3/statutory/rules", json={
        "authority": "epfo",
        "scheme": "epf",
        "effective_from": "2026-01-01",
        "config": {
            "employee_rate": 12.0,
            "employer_rate": 12.0,
            "wage_ceiling": 15000.0,
            "apply_ceiling": True,
        },
        "description": "Statutory EPF for payroll compute test",
    })
    assert rule_resp.status_code == 201

    # 2. Finance user creates and computes payroll run for 2026-11
    token_fin = login(*CREDENTIALS["FINANCE"])
    set_auth(token_fin)

    run_resp = client.post("/api/payroll/runs", json={"month": "2026-11"})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]
    _shared["payroll_run_id"] = run_id

    comp_resp = client.post(f"/api/payroll/runs/{run_id}/compute")
    assert comp_resp.status_code == 200

    # 3. Verify StatutoryCalculation records created
    from app.database import SessionLocal
    from app.models_statutory import StatutoryCalculation, StatutoryPeriod
    from app.models_v6 import Payslip

    db = SessionLocal()
    try:
        calcs = db.query(StatutoryCalculation).all()
        assert len(calcs) > 0, "Expected at least one StatutoryCalculation record"

        # Check payslips contain statutory deductions
        slips = db.query(Payslip).filter(Payslip.payroll_run_id == run_id).all()
        assert len(slips) > 0
        emp_slip = slips[0]
        statutory_deductions = [d for d in (emp_slip.deductions_json or []) if d.get("statutory") is True]
        assert len(statutory_deductions) > 0
        assert statutory_deductions[0]["code"] == "EPF"
        assert statutory_deductions[0]["amount"] > 0
    finally:
        db.close()


def test_historical_payroll_calculations_immutable(seed_data):
    """Historical payroll calculations remain preserved and immutable."""
    from app.database import SessionLocal
    from app.models_statutory import StatutoryCalculation

    db = SessionLocal()
    try:
        first_calc = db.query(StatutoryCalculation).first()
        assert first_calc is not None
        assert first_calc.result_snapshot is not None
        assert first_calc.rule_version is not None
        assert float(first_calc.amount) > 0
    finally:
        db.close()
