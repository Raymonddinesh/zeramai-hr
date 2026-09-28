"""
Module 12: India Professional Tax (PT) State-Configurable Adapter Tests.
"""
import os
import pytest
from datetime import date
from app.database import SessionLocal
from app.adapters.india_statutory_adapter import ProfessionalTaxAdapter
from app.models_statutory import StatutoryRule, StatutoryAuthority, StatutoryScheme
from app.models_v3 import Tenant, LegalEntity


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


def test_pt_karnataka_slabs():
    """Karnataka PT:
    Gross wage <= ₹14,999.99 -> ₹0.
    Gross wage >= ₹15,000 -> ₹200.
    """
    db = SessionLocal()
    try:
        adapter = ProfessionalTaxAdapter(db)
        res_below = adapter.calculate(
            person_id="p-pt-1",
            as_of=date(2026, 10, 1),
            gross_wage=12000.0,
            state="Karnataka",
        )
        assert res_below["employee_deduction"] == 0.0

        res_above = adapter.calculate(
            person_id="p-pt-2",
            as_of=date(2026, 10, 1),
            gross_wage=25000.0,
            state="Karnataka",
        )
        assert res_above["employee_deduction"] == 200.0
    finally:
        db.close()


def test_pt_maharashtra_slabs():
    """Maharashtra PT slabs:
    <= ₹7,500 -> ₹0.
    ₹7,501 to ₹10,000 -> ₹175.
    > ₹10,000 -> ₹200.
    """
    db = SessionLocal()
    try:
        adapter = ProfessionalTaxAdapter(db)
        res_tier2 = adapter.calculate(
            person_id="p-pt-3",
            as_of=date(2026, 10, 1),
            gross_wage=8500.0,
            state="Maharashtra",
        )
        assert res_tier2["employee_deduction"] == 175.0

        res_tier3 = adapter.calculate(
            person_id="p-pt-4",
            as_of=date(2026, 10, 1),
            gross_wage=40000.0,
            state="Maharashtra",
        )
        assert res_tier3["employee_deduction"] == 200.0
    finally:
        db.close()


def test_pt_custom_state_rule():
    """Custom state slab configured in StatutoryRule."""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).first()
        le = db.query(LegalEntity).first()

        # Add custom PT rule for Telangana
        custom_rule = StatutoryRule(
            tenant_id=tenant.id if tenant else "t1",
            legal_entity_id=le.id if le else "le1",
            authority=StatutoryAuthority.STATE_TAX,
            scheme=StatutoryScheme.PROFESSIONAL_TAX,
            state="Telangana",
            effective_from=date(2026, 1, 1),
            config={
                "slabs": [
                    {"min": 0, "max": 15000.0, "tax": 0.0},
                    {"min": 15000.01, "max": 20000.0, "tax": 150.0},
                    {"min": 20000.01, "max": None, "tax": 200.0},
                ]
            },
            is_active=True,
        )
        db.add(custom_rule)
        db.commit()

        adapter = ProfessionalTaxAdapter(db)
        res = adapter.calculate(
            person_id="p-pt-5",
            as_of=date(2026, 8, 1),
            gross_wage=18000.0,
            state="Telangana",
            tenant_id=tenant.id if tenant else "t1",
        )
        assert res["employee_deduction"] == 150.0
    finally:
        db.close()
