"""
test_global_payroll_lifecycle_adjustments.py - Module 21: Lifecycle, Immutability & Adjustments Tests
Zeramai Enterprise HRMS
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Person

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
}


def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    token = resp.cookies.get("access_token") or resp.json().get("access_token")
    assert token
    return token


def set_auth(token: str):
    client.cookies.set("access_token", token)


@pytest.fixture(scope="module", autouse=True)
def seed_data():
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed_rbac import main as run_rbac
    from app.seed import run as run_seed
    run_rbac()
    run_seed()
    yield


def test_payroll_calendar_approval_workflow():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal = next((c for c in cals if (c.get("pay_group") and c.get("pay_group", {}).get("currency") == "INR") or "IND" in c.get("name", "")), cals[0])
    cal_id = cal["id"]

    db = SessionLocal()
    try:
        person = db.query(Person).filter(Person.email == "employee@example.com").first()
        person_id = person.id
    finally:
        db.close()

    comps = client.get("/api/v3/global-payroll/components").json()
    basic_comp = next((c for c in comps if c["code"] == "BASIC"), comps[0])

    client.post("/api/v3/global-payroll/inputs", json={
        "payroll_calendar_id": cal_id,
        "person_id": person_id,
        "pay_component_id": basic_comp["id"],
        "amount": "80000.00",
        "currency": "INR",
        "source": "SALARY",
        "reference": "SAL-M21-TEST",
    })

    # 1. Ensure calculated
    client.post(f"/api/v3/global-payroll/runs/{cal_id}/calculate", json={"recalculate_existing": True})

    # 2. Approve calendar run
    appr_resp = client.post(f"/api/v3/global-payroll/runs/{cal_id}/approve")
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVED"


def test_finalized_payroll_immutability():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal = next((c for c in cals if (c.get("pay_group") and c.get("pay_group", {}).get("currency") == "INR") or "IND" in c.get("name", "")), cals[0])
    cal_id = cal["id"]

    # Finalize run
    fin_resp = client.post(f"/api/v3/global-payroll/runs/{cal_id}/finalize")
    assert fin_resp.status_code == 200
    assert fin_resp.json()["status"] == "CLOSED"

    # Attempt to recalculate finalized/closed run -> 400 Bad Request (Immutability enforced!)
    recalc_resp = client.post(f"/api/v3/global-payroll/runs/{cal_id}/calculate", json={
        "recalculate_existing": True
    })
    assert recalc_resp.status_code == 400
    assert "cannot recalculate" in recalc_resp.json()["detail"].lower()


def test_payroll_adjustments_workflow():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    db = SessionLocal()
    try:
        person = db.query(Person).filter(Person.email == "employee@example.com").first()
        person_id = person.id
    finally:
        db.close()

    # Create retro underpayment adjustment
    adj_resp = client.post("/api/v3/global-payroll/adjustments", json={
        "person_id": person_id,
        "adjustment_type": "UNDERPAYMENT",
        "amount": "5000.00",
        "currency": "INR",
        "reason": "Retroactive shift allowance adjustment for previous cycle",
        "effective_period": "2026-10",
    })
    assert adj_resp.status_code == 201
    adj_data = adj_resp.json()
    assert adj_data["adjustment_type"] == "UNDERPAYMENT"
    assert adj_data["status"] == "PENDING"

    # List adjustments
    adjs = client.get("/api/v3/global-payroll/adjustments").json()
    assert len(adjs) >= 1


def test_payroll_reconciliation_variance_tracking():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal_id = cals[0]["id"]

    rec_resp = client.get(f"/api/v3/global-payroll/reconciliation?calendar_id={cal_id}")
    assert rec_resp.status_code == 200
    rec = rec_resp.json()
    assert "calculated_total" in rec
    assert "variance" in rec
    assert rec["status"] in ["MATCHED", "VARIANCE"]


def test_global_payslip_generation():
    # As employee, view generated payslip
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    slips_resp = client.get("/api/v3/global-payroll/payslips")
    assert slips_resp.status_code == 200
    slips = slips_resp.json()
    assert len(slips) >= 1
    slip = slips[0]
    assert slip["currency"] in ["INR", "USD"]
    assert Decimal(slip["net_pay"]) > Decimal("0.00")
