"""
test_wf_scenarios_mobility.py - Module 17: Scenarios, Hiring Plans, Mobility & Plan vs Actual Tests
"""
import pytest
from datetime import date
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


def test_workforce_scenarios_modeling():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    ou_resp = client.get("/api/v3/workforce-planning/organization-units")
    ou_id = ou_resp.json()[0]["id"]

    # 1. Create a Growth Scenario
    scen_resp = client.post("/api/v3/workforce-planning/scenarios", json={
        "name": "Aggressive International Expansion FY27",
        "description": "Model hiring ramp of 20 engineers for EU/US expansion",
        "scenario_type": "EXPANSION",
        "planning_horizon": "FY2026-27",
        "lines": [
            {
                "organization_unit_id": ou_id,
                "job_family": "Engineering",
                "job_level": "Senior / L4",
                "period": "2026-Q3",
                "headcount_delta": 15.0,
                "hiring_delta": 15.0,
                "exit_delta": 0.0,
                "cost_delta": 2250000.0,
                "notes": "Backend and Infrastructure capacity expansion",
            },
            {
                "organization_unit_id": ou_id,
                "job_family": "Product Management",
                "job_level": "Principal / L6",
                "period": "2026-Q3",
                "headcount_delta": 5.0,
                "hiring_delta": 5.0,
                "exit_delta": 0.0,
                "cost_delta": 1200000.0,
                "notes": "Regional product leadership",
            }
        ]
    })
    assert scen_resp.status_code in [200, 201]
    scen = scen_resp.json()
    assert scen["total_headcount_delta"] == 20.0
    assert scen["total_cost_delta"] == 3450000.0


def test_workforce_hiring_plans():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    ou_resp = client.get("/api/v3/workforce-planning/organization-units")
    ou_id = ou_resp.json()[0]["id"]

    hp_resp = client.post("/api/v3/workforce-planning/hiring-plans", json={
        "name": "Q3 Engineering Recruitment Pipeline",
        "fiscal_year": "2026-2027",
        "lines": [
            {
                "organization_unit_id": ou_id,
                "job_family": "Engineering",
                "job_level": "Staff / L5",
                "planned_open_date": "2026-07-01",
                "planned_join_date": "2026-09-01",
                "planned_headcount": 3.0,
                "estimated_cost": 750000.0,
                "recruitment_priority": "HIGH",
            }
        ]
    })
    assert hp_resp.status_code in [200, 201]
    hp = hp_resp.json()
    assert hp["total_planned_hires"] == 3.0


def test_internal_mobility_planning():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    person = db.query(Person).first()
    person_id = person.id
    db.close()

    # Create mobility plan (e.g. Promotion)
    mp_resp = client.post("/api/v3/workforce-planning/mobility-plans", json={
        "person_id": person_id,
        "mobility_type": "PROMOTION",
        "target_date": "2026-10-01",
    })
    assert mp_resp.status_code in [200, 201]
    mp = mp_resp.json()
    mp_id = mp["id"]
    assert mp["status"] == "DRAFT"
    assert mp["mobility_type"] == "PROMOTION"

    # Update to APPROVED
    up_resp = client.put(f"/api/v3/workforce-planning/mobility-plans/{mp_id}", json={
        "status": "APPROVED"
    })
    assert up_resp.status_code == 200
    assert up_resp.json()["status"] == "APPROVED"


def test_attrition_scenario_impact_and_plan_vs_actual():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # 1. Attrition scenario impact
    att_resp = client.get("/api/v3/workforce-planning/attrition-impact?assumed_rate=15.0")
    assert att_resp.status_code == 200
    att = att_resp.json()
    assert att["assumed_attrition_rate_pct"] == 15.0
    assert "projected_exits_count" in att
    assert "estimated_replacement_cost" in att
    assert "SCENARIO" in att["notes"]

    # 2. Plan vs. Actual comparison
    pva_resp = client.get("/api/v3/workforce-planning/plan-vs-actual?fiscal_year=2026-2027")
    assert pva_resp.status_code == 200
    pva = pva_resp.json()
    assert "planned_headcount" in pva
    assert "actual_headcount" in pva
    assert "headcount_variance" in pva
    assert "planned_workforce_cost" in pva
    assert "actual_workforce_cost" in pva
