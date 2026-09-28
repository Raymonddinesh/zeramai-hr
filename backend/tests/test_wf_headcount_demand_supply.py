"""
test_wf_headcount_demand_supply.py - Module 17: Headcount, Demand, Supply & Gap Analysis Tests
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("admin@example.com", "ChangeMe123!"),
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


def test_headcount_plan_lifecycle_and_approval():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # Fetch an org unit
    ou_resp = client.get("/api/v3/workforce-planning/organization-units")
    assert ou_resp.status_code == 200
    ou_id = ou_resp.json()[0]["id"]

    # 1. Create a Headcount Plan
    hp_resp = client.post("/api/v3/workforce-planning/headcount-plans", json={
        "name": "FY2027 Expansion Workforce Plan",
        "fiscal_year": "2026-2027",
        "currency": "INR",
        "lines": [
            {
                "organization_unit_id": ou_id,
                "job_family": "Engineering",
                "job_level": "Senior / L4",
                "month": "2026-05",
                "planned_headcount": 5.0,
                "planned_hires": 2.0,
                "planned_exits": 0.0,
                "planned_cost": 800000.0,
                "currency": "INR",
            },
            {
                "organization_unit_id": ou_id,
                "job_family": "Product Management",
                "job_level": "Lead / L5",
                "month": "2026-05",
                "planned_headcount": 2.0,
                "planned_hires": 1.0,
                "planned_exits": 0.0,
                "planned_cost": 450000.0,
                "currency": "INR",
            }
        ]
    })
    assert hp_resp.status_code in [200, 201]
    hp_data = hp_resp.json()
    assert hp_data["status"] == "DRAFT"
    assert hp_data["total_planned_headcount"] == 7.0
    assert hp_data["total_planned_cost"] == 1250000.0
    plan_id = hp_data["id"]

    # 2. Approve Headcount Plan
    appr_resp = client.post(f"/api/v3/workforce-planning/headcount-plans/{plan_id}/approve", json={})
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["status"] == "APPROVED"
    assert appr_data["approved_by"] is not None


def test_workforce_demand_supply_and_gap_analysis():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    ou_resp = client.get("/api/v3/workforce-planning/organization-units")
    ou_id = ou_resp.json()[0]["id"]

    # 1. Create a Workforce Demand Plan
    dp_resp = client.post("/api/v3/workforce-planning/demand-plans", json={
        "name": "Q2 Strategic Delivery Demand",
        "planning_horizon": "6_MONTHS",
        "methodology": "BOTTOM_UP",
        "lines": [
            {
                "organization_unit_id": ou_id,
                "job_family": "Engineering",
                "job_level": "Senior / L4",
                "period": "2026-Q2",
                "required_headcount": 10.0,
                "required_skills": "Python, Distributed Systems, Cloud Architecture",
                "estimated_cost": 1500000.0,
                "currency": "INR",
                "rationale": "Enterprise client scaling and multi-region deployment",
            }
        ]
    })
    assert dp_resp.status_code in [200, 201]
    dp_data = dp_resp.json()
    dp_id = dp_data["id"]
    assert dp_data["total_required_headcount"] == 10.0

    # 2. Query Workforce Supply
    sup_resp = client.get("/api/v3/workforce-planning/supply?period=2026-Q2")
    assert sup_resp.status_code == 200
    supply = sup_resp.json()
    assert "total_supply_headcount" in supply
    assert "headcount_by_org_unit" in supply

    # 3. Calculate Workforce Gaps (Demand - Supply = Gap)
    gap_resp = client.post(f"/api/v3/workforce-planning/gaps/calculate?demand_plan_id={dp_id}", json={})
    assert gap_resp.status_code == 200
    gaps = gap_resp.json()
    assert len(gaps) >= 1
    g = gaps[0]
    assert g["demand_headcount"] == 10.0
    assert g["gap_headcount"] == (g["demand_headcount"] - g["supply_headcount"])
    assert g["gap_type"] in ["SHORTAGE", "SURPLUS", "BALANCED"]
