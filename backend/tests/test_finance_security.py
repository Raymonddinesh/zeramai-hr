"""
test_finance_security.py - Module 16: RBAC Enforcement, Multi-Tenant Isolation & Export Tests
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "FINANCE": ("finance@zeramai.com", "ChangeMe123!"),
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


def test_rbac_finance_access_control():
    # 1. Employee cannot view finance dashboard
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    dash_resp = client.get("/api/v3/finance/dashboard")
    assert dash_resp.status_code == 403

    # 2. Employee cannot create cost centers
    cc_resp = client.post("/api/v3/finance/cost-centers", json={
        "code": "CC-UNAUTHORIZED",
        "name": "Unauthorized Cost Center",
    })
    assert cc_resp.status_code == 403

    # 3. Employee cannot create GL accounts
    gl_resp = client.post("/api/v3/finance/gl-accounts", json={
        "account_code": "99999",
        "account_name": "Unauthorized Account",
        "account_type": "EXPENSE",
        "normal_balance": "DEBIT",
    })
    assert gl_resp.status_code == 403

    # 4. Employee cannot generate payroll journals
    j_resp = client.post("/api/v3/finance/payroll-journals/generate", json={
        "payroll_run_id": "dummy-run",
        "period_key": "2026-03",
    })
    assert j_resp.status_code == 403

    # 5. Employee cannot create budgets
    b_resp = client.post("/api/v3/finance/budgets", json={
        "name": "Unauthorized Budget",
        "fiscal_year": "2026-2027",
    })
    assert b_resp.status_code == 403

    # 6. Employee cannot register vendors
    v_resp = client.post("/api/v3/finance/vendors", json={
        "name": "Unauthorized Vendor",
        "category": "GENERAL",
    })
    assert v_resp.status_code == 403


def test_accounting_export_csv_and_json():
    fin_token = login(*CREDENTIALS["FINANCE"])
    set_auth(fin_token)

    # Fetch a journal
    j_list = client.get("/api/v3/finance/payroll-journals")
    assert j_list.status_code == 200
    journals = j_list.json()
    assert len(journals) >= 1
    journal_id = journals[0]["id"]

    # 1. Export in CSV format
    csv_resp = client.get(f"/api/v3/finance/payroll-journals/{journal_id}/export?export_format=CSV")
    assert csv_resp.status_code == 200
    csv_data = csv_resp.json()
    assert "csv_data" in csv_data
    assert "journal_number,posting_date" in csv_data["csv_data"]

    # 2. Export in JSON format
    json_resp = client.get(f"/api/v3/finance/payroll-journals/{journal_id}/export?export_format=JSON")
    assert json_resp.status_code == 200
    json_data = json_resp.json()
    assert json_data["id"] == journal_id
    assert "lines" in json_data


def test_finance_multi_tenant_isolation():
    fin_token = login(*CREDENTIALS["FINANCE"])
    set_auth(fin_token)

    # Non-existent foreign tenant ID query returns 404 or empty list
    bogus_id = "00000000-0000-0000-0000-000000000000"
    get_cc = client.get(f"/api/v3/finance/cost-centers/{bogus_id}")
    assert get_cc.status_code == 404

    get_j = client.get(f"/api/v3/finance/payroll-journals/{bogus_id}")
    assert get_j.status_code == 404

    get_b = client.get(f"/api/v3/finance/budgets/{bogus_id}")
    assert get_b.status_code == 404

    get_v = client.get(f"/api/v3/finance/vendors/{bogus_id}")
    assert get_v.status_code == 404
