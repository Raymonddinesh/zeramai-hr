"""
test_global_payroll_engine_calculation.py - Module 21: Calculation Engine, Adapters & Decimal Tests
Zeramai Enterprise HRMS
"""
import pytest
from decimal import Decimal
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


def test_decimal_gross_to_net_calculation():
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

    # Ensure employee has at least one salary input on this calendar
    client.post("/api/v3/global-payroll/inputs", json={
        "payroll_calendar_id": cal_id,
        "person_id": person_id,
        "pay_component_id": basic_comp["id"],
        "amount": "80000.00",
        "currency": "INR",
        "source": "SALARY",
        "reference": "SAL-M21-TEST",
    })

    # Trigger gross-to-net calculation
    calc_resp = client.post(f"/api/v3/global-payroll/runs/{cal_id}/calculate", json={
        "recalculate_existing": True
    })
    assert calc_resp.status_code == 200
    summary = calc_resp.json()
    assert summary["calendar_id"] == cal_id
    assert summary["total_employees"] >= 1
    assert Decimal(summary["total_gross"]) > Decimal("0.00")
    assert Decimal(summary["total_net_pay"]) > Decimal("0.00")


def test_india_adapter_reuse_module12_statutory():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal = next((c for c in cals if (c.get("pay_group") and c.get("pay_group", {}).get("currency") == "INR") or "IND" in c.get("name", "")), cals[0])
    cal_id = cal["id"]

    results = client.get(f"/api/v3/global-payroll/results?calendar_id={cal_id}").json()
    assert len(results) >= 1
    res = results[0]
    assert "Module 12 India Statutory Engine" in res["calculation_notes"]
    assert Decimal(res["employee_deductions"]) > Decimal("0.00")
    assert Decimal(res["tax"]) >= Decimal("0.00")


def test_generic_international_adapter_framework():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # Create a US Pay group and calendar
    cfgs = client.get("/api/v3/global-payroll/configurations").json()
    countries = client.get("/api/v3/global-payroll/countries").json()
    us_country = next(c for c in countries if c["country_code"] == "USA")

    # Create US Config
    us_cfg = client.post("/api/v3/global-payroll/configurations", json={
        "legal_entity_id": cfgs[0]["legal_entity_id"],
        "country_id": us_country["id"],
        "default_currency": "USD",
        "timezone": "America/New_York",
        "payroll_frequency": "MONTHLY",
        "payroll_day": 30,
        "cutoff_day": 25,
        "adapter_code": "GENERIC_INTERNATIONAL_ADAPTER",
    }).json()

    # Create US Pay group
    us_pg = client.post("/api/v3/global-payroll/pay-groups", json={
        "payroll_configuration_id": us_cfg["id"],
        "name": "US Monthly Salaried Group",
        "code": "USA-MTH-SAL",
        "currency": "USD",
        "frequency": "MONTHLY",
    }).json()

    # Create US Calendar
    us_cal = client.post("/api/v3/global-payroll/calendars", json={
        "pay_group_id": us_pg["id"],
        "period_start": "2026-11-01",
        "period_end": "2026-11-30",
        "cutoff_date": "2026-11-25",
        "pay_date": "2026-11-30",
        "status": "OPEN",
    }).json()

    # Create US component & input
    us_comp = client.post("/api/v3/global-payroll/components", json={
        "code": "US_BASE_SAL",
        "name": "US Base Salary",
        "component_type": "EARNING",
        "country_code": "USA",
    }).json()

    db = SessionLocal()
    try:
        person = db.query(Person).filter(Person.email == "employee@example.com").first()
        person_id = person.id
    finally:
        db.close()

    client.post("/api/v3/global-payroll/inputs", json={
        "payroll_calendar_id": us_cal["id"],
        "person_id": person_id,
        "pay_component_id": us_comp["id"],
        "amount": "12000.00",
        "currency": "USD",
        "source": "SALARY",
    })

    # Calculate run via Generic International Adapter
    calc_res = client.post(f"/api/v3/global-payroll/runs/{us_cal['id']}/calculate", json={}).json()
    assert calc_res["country_code"] == "USA"
    assert calc_res["currency"] == "USD"
    assert Decimal(calc_res["total_gross"]) == Decimal("12000.00")
    assert Decimal(calc_res["total_net_pay"]) > Decimal("0.00")


def test_payroll_result_component_traceability():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal_id = cals[0]["id"]

    results = client.get(f"/api/v3/global-payroll/results?calendar_id={cal_id}").json()
    res_id = results[0]["id"]

    detailed = client.get(f"/api/v3/global-payroll/results/{res_id}").json()
    assert "components" in detailed
    assert len(detailed["components"]) >= 1
    for comp in detailed["components"]:
        assert "component_code" in comp
        assert "amount" in comp
        assert "currency" in comp
        assert "calculation_reference" in comp


def test_historical_fx_snapshot_protection():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    cals = client.get("/api/v3/global-payroll/calendars").json()
    cal_id = cals[0]["id"]

    results = client.get(f"/api/v3/global-payroll/results?calendar_id={cal_id}").json()
    res = results[0]

    # Verify that FX rate snapshot is stored on the result record
    assert "fx_rate_used" in res
    assert Decimal(res["fx_rate_used"]) > Decimal("0.00")
