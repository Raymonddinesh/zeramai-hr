"""
test_global_payroll_core_models.py - Module 21: Core Models & Validation Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app

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


def test_payroll_country_crud_and_validation():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Fetch countries list seeded
    resp = client.get("/api/v3/global-payroll/countries")
    assert resp.status_code == 200
    countries = resp.json()
    assert len(countries) >= 7
    ind = next((c for c in countries if c["country_code"] == "IND"), None)
    assert ind is not None
    assert ind["default_currency"] == "INR"
    assert ind["adapter_status"] == "PRODUCTION_VALIDATED"

    # 2. Duplicate country registration rejected
    dup_resp = client.post("/api/v3/global-payroll/countries", json={
        "country_code": "IND",
        "country_name": "India Duplicate",
        "default_currency": "INR",
        "adapter_status": "CONFIGURED_ONLY",
    })
    assert dup_resp.status_code == 400


def test_payroll_configuration_and_pay_group():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. List configurations
    configs = client.get("/api/v3/global-payroll/configurations").json()
    assert len(configs) >= 1
    cfg_id = configs[0]["id"]

    # 2. Create custom pay group
    pg_resp = client.post("/api/v3/global-payroll/pay-groups", json={
        "payroll_configuration_id": cfg_id,
        "name": "Bangalore Engineering Pay Group",
        "code": "BLR-ENG-MTH",
        "currency": "INR",
        "frequency": "MONTHLY",
        "description": "Monthly salaried engineering staff in Bangalore",
    })
    assert pg_resp.status_code == 201
    pg_data = pg_resp.json()
    assert pg_data["code"] == "BLR-ENG-MTH"

    # 3. Duplicate pay group code rejected
    dup_resp = client.post("/api/v3/global-payroll/pay-groups", json={
        "payroll_configuration_id": cfg_id,
        "name": "Duplicate Code",
        "code": "BLR-ENG-MTH",
        "currency": "INR",
        "frequency": "MONTHLY",
    })
    assert dup_resp.status_code == 400


def test_payroll_calendar_overlap_prevention():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    pgs = client.get("/api/v3/global-payroll/pay-groups").json()
    pg_id = pgs[0]["id"]

    # 1. Create first calendar period: Oct 1 - Oct 31, 2026
    c1_resp = client.post("/api/v3/global-payroll/calendars", json={
        "pay_group_id": pg_id,
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
        "cutoff_date": "2026-10-20",
        "pay_date": "2026-10-28",
        "status": "OPEN",
    })
    assert c1_resp.status_code == 201

    # 2. Attempt overlapping calendar period: Oct 15 - Nov 15, 2026 -> 400 Bad Request
    overlap_resp = client.post("/api/v3/global-payroll/calendars", json={
        "pay_group_id": pg_id,
        "period_start": "2026-10-15",
        "period_end": "2026-11-15",
        "cutoff_date": "2026-11-05",
        "pay_date": "2026-11-10",
        "status": "OPEN",
    })
    assert overlap_resp.status_code == 400
    assert "overlaps" in overlap_resp.json()["detail"].lower()

    # 3. Invalid date sequence: start >= end -> 400 Bad Request
    seq_resp = client.post("/api/v3/global-payroll/calendars", json={
        "pay_group_id": pg_id,
        "period_start": "2026-12-31",
        "period_end": "2026-12-01",
        "cutoff_date": "2026-12-20",
        "pay_date": "2026-12-28",
        "status": "OPEN",
    })
    assert seq_resp.status_code == 400


def test_global_pay_components_catalog():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    comps = client.get("/api/v3/global-payroll/components").json()
    assert len(comps) >= 6

    # Create new custom component
    c_resp = client.post("/api/v3/global-payroll/components", json={
        "code": "HEALTH_STIPEND",
        "name": "Monthly Health & Wellness Stipend",
        "component_type": "REIMBURSEMENT",
        "taxable": False,
        "pensionable": False,
        "recurring": True,
        "description": "Non-taxable health allowance",
    })
    assert c_resp.status_code == 201
    assert c_resp.json()["component_type"] == "REIMBURSEMENT"


def test_country_payroll_rules_versioning():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    r_resp = client.post("/api/v3/global-payroll/rules", json={
        "country_code": "USA",
        "rule_code": "US_SOC_SEC_2026",
        "rule_name": "US Social Security Standard 6.2%",
        "rule_type": "SOCIAL_SECURITY",
        "configuration_reference": {"rate_pct": "6.20"},
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-31",
        "active": True,
        "version": 1,
    })
    assert r_resp.status_code == 201
    data = r_resp.json()
    assert data["rule_code"] == "US_SOC_SEC_2026"
    assert data["version"] == 1
