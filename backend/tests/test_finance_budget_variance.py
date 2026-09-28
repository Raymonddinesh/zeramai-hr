"""
test_finance_budget_variance.py - Module 16: Workforce Cost, Budgeting & Variance Analysis Tests
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "FINANCE": ("finance@zeramai.com", "ChangeMe123!"),
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


def test_workforce_cost_generation_and_query():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    from app.database import SessionLocal
    from app.models import Person, PayrollRun, PayrollRunStatus, Tenant
    from datetime import date
    import uuid

    db = SessionLocal()
    tenant = db.query(Tenant).first()
    t_id = tenant.id if tenant else str(uuid.uuid4())
    person = db.query(Person).first()
    p_id = person.id if person else str(uuid.uuid4())

    payroll_run = db.query(PayrollRun).filter(PayrollRun.status == PayrollRunStatus.APPROVED).first()
    if not payroll_run:
        payroll_run = PayrollRun(
            month="2026-03",
            status=PayrollRunStatus.APPROVED,
            total_gross=600000.0,
            total_deductions=90000.0,
            total_net=510000.0,
        )
        db.add(payroll_run)
        db.commit()
        db.refresh(payroll_run)

    p_run_id = payroll_run.id
    db.close()

    # Generate workforce cost records for the run
    calc_resp = client.post(f"/api/v3/finance/workforce-costs/calculate-from-payroll?payroll_run_id={p_run_id}")
    assert calc_resp.status_code in [200, 201]
    results = calc_resp.json()
    assert len(results) >= 1
    wc = results[0]
    assert float(wc["total_cost"]) > 0
    assert float(wc["total_cost"]) == (
        float(wc["base_salary_amount"])
        + float(wc["bonus_amount"])
        + float(wc["employer_statutory_amount"])
        + float(wc["benefits_amount"])
        + float(wc["expense_reimbursements_amount"])
    )

    # Query workforce cost records list
    list_resp = client.get("/api/v3/finance/workforce-costs?period_key=2026-03")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_workforce_budget_and_variance():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Get a cost center
    cc_resp = client.get("/api/v3/finance/cost-centers")
    assert cc_resp.status_code == 200
    ccs = cc_resp.json()
    assert len(ccs) >= 1
    cc_id = ccs[0]["id"]

    # 2. Create budget
    b_resp = client.post("/api/v3/finance/budgets", json={
        "name": "FY2026-27 Strategic Workforce Plan",
        "fiscal_year": "2026-2027",
        "total_budget": 15000000.0,
        "status": "APPROVED",
        "lines": [
            {
                "cost_center_id": cc_id,
                "month": "2026-03",
                "category": "SALARY",
                "budget_amount": 990000.0,
            }
        ],
    })
    assert b_resp.status_code in [200, 201]
    b_data = b_resp.json()
    assert b_data["fiscal_year"] == "2026-2027"
    budget_id = b_data["id"]

    # 3. Retrieve budget by ID
    get_resp = client.get(f"/api/v3/finance/budgets/{budget_id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["lines"]) >= 1

    # 4. Variance analysis (Budget vs Actual)
    var_resp = client.get(f"/api/v3/finance/budgets/{budget_id}/variance?period_key=2026-03")
    assert var_resp.status_code == 200
    var_data = var_resp.json()
    assert var_data["budget_id"] == budget_id
    assert "cost_center_variances" in var_data


def test_payroll_period_variance_and_dashboard():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Query payroll variance across periods
    p_var = client.get("/api/v3/finance/payroll-variance?current_period=2026-03&prior_period=2026-02")
    assert p_var.status_code == 200
    var_result = p_var.json()
    assert var_result["current_period"] == "2026-03"
    assert "gross_variance" in var_result
    assert "headcount_variance" in var_result

    # 2. Finance Dashboard
    dash_resp = client.get("/api/v3/finance/dashboard")
    assert dash_resp.status_code == 200
    dash = dash_resp.json()
    assert "cost_centers_count" in dash
    assert "total_workforce_cost_ytd" in dash
    assert "posted_journals_count" in dash
