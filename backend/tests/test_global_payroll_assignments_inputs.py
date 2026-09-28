"""
test_global_payroll_assignments_inputs.py - Module 21: Assignments, Overlaps, Inputs & FX Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Person, LegalEntity

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


def test_employee_payroll_assignment():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    assignments = client.get("/api/v3/global-payroll/assignments").json()
    assert len(assignments) >= 1
    assert assignments[0]["country_code"] == "IND"
    assert assignments[0]["payroll_status"] == "ACTIVE"


def test_overlapping_assignment_prevention():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    db = SessionLocal()
    try:
        person = db.query(Person).filter(Person.email == "employee@example.com").first()
        le = db.query(LegalEntity).first()
        assert person is not None
        assert le is not None
        person_id = person.id
        le_id = le.id
    finally:
        db.close()

    pgs = client.get("/api/v3/global-payroll/pay-groups").json()
    pg_id = pgs[0]["id"]

    # Existing assignment starts 2026-01-01 ongoing.
    # Attempting to add an overlapping active assignment -> 400 Bad Request
    overlap_resp = client.post("/api/v3/global-payroll/assignments", json={
        "person_id": person_id,
        "legal_entity_id": le_id,
        "country_code": "IND",
        "pay_group_id": pg_id,
        "currency": "INR",
        "effective_from": "2026-06-01",
        "effective_to": "2026-12-31",
        "payroll_status": "ACTIVE",
    })
    assert overlap_resp.status_code == 400
    assert "already has an active payroll assignment" in overlap_resp.json()["detail"].lower()


def test_payroll_input_traceability():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal_id = cals[0]["id"]
    comps = client.get("/api/v3/global-payroll/components").json()
    basic_comp = next((c for c in comps if c["code"] == "BASIC"), comps[0])

    db = SessionLocal()
    try:
        person = db.query(Person).filter(Person.email == "employee@example.com").first()
        person_id = person.id
    finally:
        db.close()

    # Create traceable payroll input
    inp_resp = client.post("/api/v3/global-payroll/inputs", json={
        "payroll_calendar_id": cal_id,
        "person_id": person_id,
        "pay_component_id": basic_comp["id"],
        "amount": "75000.00",
        "currency": "INR",
        "source": "SALARY",
        "reference": "SAL-REV-2026-09-01",
    })
    assert inp_resp.status_code == 201
    inp_data = inp_resp.json()
    assert inp_data["source"] == "SALARY"
    assert inp_data["reference"] == "SAL-REV-2026-09-01"
    assert inp_data["amount"] == "75000.00"


def test_payroll_exchange_rate_snapshot():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    rates = client.get("/api/v3/global-payroll/exchange-rates").json()
    assert len(rates) >= 5

    # Create new FX snapshot for historical currency conversion
    rate_resp = client.post("/api/v3/global-payroll/exchange-rates", json={
        "base_currency": "SGD",
        "quote_currency": "INR",
        "rate": "62.450000",
        "source": "CONFIGURED",
    })
    assert rate_resp.status_code == 201
    assert rate_resp.json()["rate"] == "62.450000"
