"""
Module 12: India ESI (Employee State Insurance) Adapter Tests.
"""
import os
import pytest
from datetime import date
from app.database import SessionLocal
from app.adapters.india_statutory_adapter import ESIAdapter

CREDENTIALS = {
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
}


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


def test_esi_eligible_below_ceiling():
    """Gross wage ₹18,000 is <= ₹21,000 statutory wage ceiling.
    Employee deduction: 0.75% of 18,000 = 135.0.
    Employer contribution: 3.25% of 18,000 = 585.0.
    """
    db = SessionLocal()
    try:
        adapter = ESIAdapter(db)
        res = adapter.calculate(
            person_id="p-esi-1",
            as_of=date(2026, 10, 1),
            gross_wage=18000.0,
        )
        assert res["scheme"] == "esi"
        assert res["is_eligible"] is True
        assert res["employee_deduction"] == 135.0
        assert res["employer_contribution"] == 585.0
        assert res["total_statutory_amount"] == 720.0
    finally:
        db.close()


def test_esi_ineligible_above_ceiling():
    """Gross wage ₹25,000 is > ₹21,000 statutory wage ceiling.
    ESI is not applicable.
    Employee deduction = 0, Employer contribution = 0, is_eligible = False.
    """
    db = SessionLocal()
    try:
        adapter = ESIAdapter(db)
        res = adapter.calculate(
            person_id="p-esi-2",
            as_of=date(2026, 10, 1),
            gross_wage=25000.0,
        )
        assert res["scheme"] == "esi"
        assert res["is_eligible"] is False
        assert res["employee_deduction"] == 0.0
        assert res["employer_contribution"] == 0.0
        assert res["total_statutory_amount"] == 0.0
    finally:
        db.close()
