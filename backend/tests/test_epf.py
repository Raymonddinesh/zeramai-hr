"""
Module 12: India EPF (Employee Provident Fund) Adapter Tests.
"""
import os
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.adapters.india_statutory_adapter import EPFAdapter
from app.models_statutory import StatutoryRule, StatutoryAuthority, StatutoryScheme
from app.models_v3 import Tenant, LegalEntity

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


def test_epf_calculation_within_ceiling():
    """EPF calculation for basic wage ₹12,000 (below ₹15,000 ceiling).
    Employee deduction: 12% of 12,000 = 1,440.
    Employer contribution: 12% of 12,000 = 1,440.
    """
    db = SessionLocal()
    try:
        adapter = EPFAdapter(db)
        res = adapter.calculate(
            person_id="p-epf-1",
            as_of=date(2026, 10, 1),
            basic_wage=12000.0,
        )
        assert res["scheme"] == "epf"
        assert res["epf_wage"] == 12000.0
        assert res["employee_deduction"] == 1440.0
        assert res["employer_contribution"] == 1440.0
        assert res["breakdown"]["employee_epf"] == 1440.0
    finally:
        db.close()


def test_epf_calculation_above_ceiling():
    """EPF calculation for basic wage ₹30,000 (above statutory ceiling ₹15,000).
    Eligible EPF wage is capped at ₹15,000.
    Employee deduction: 12% of 15,000 = 1,800.
    Employer contribution: 12% of 15,000 = 1,800.
    """
    db = SessionLocal()
    try:
        adapter = EPFAdapter(db)
        res = adapter.calculate(
            person_id="p-epf-2",
            as_of=date(2026, 10, 1),
            basic_wage=30000.0,
        )
        assert res["epf_wage"] == 15000.0
        assert res["employee_deduction"] == 1800.0
        assert res["employer_contribution"] == 1800.0
    finally:
        db.close()


def test_epf_calculation_with_custom_effective_rule():
    """Custom effective-dated EPF rule with custom 10% rate and ₹20,000 ceiling."""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).first()
        le = db.query(LegalEntity).first()

        # Add custom rule effective from 2026-06-01
        custom_rule = StatutoryRule(
            tenant_id=tenant.id if tenant else "t1",
            legal_entity_id=le.id if le else "le1",
            authority=StatutoryAuthority.EPFO,
            scheme=StatutoryScheme.EPF,
            effective_from=date(2026, 6, 1),
            effective_to=date(2026, 12, 31),
            config={
                "employee_rate": 10.0,
                "employer_rate": 10.0,
                "wage_ceiling": 20000.0,
                "apply_ceiling": True,
            },
            is_active=True,
        )
        db.add(custom_rule)
        db.commit()

        adapter = EPFAdapter(db)
        res = adapter.calculate(
            person_id="p-epf-3",
            as_of=date(2026, 8, 1),
            basic_wage=25000.0,
            tenant_id=tenant.id if tenant else "t1",
        )
        assert res["epf_wage"] == 20000.0
        assert res["employee_deduction"] == 2000.0  # 10% of 20,000
        assert res["employer_contribution"] == 2000.0
    finally:
        db.close()
