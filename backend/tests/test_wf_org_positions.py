"""
test_wf_org_positions.py - Module 17: Organization Structure, Positions & Assignment Tests
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("admin@example.com", "ChangeMe123!"),
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


def test_org_unit_hierarchy_and_circular_prevention():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # 1. Create a parent organization unit (Unit A)
    u_a_resp = client.post("/api/v3/workforce-planning/organization-units", json={
        "code": "OU-TECH-CORE",
        "name": "Technology Core Organization",
        "unit_type": "DIVISION",
        "active": True,
        "effective_from": "2026-01-01",
    })
    assert u_a_resp.status_code in [200, 201]
    u_a = u_a_resp.json()
    u_a_id = u_a["id"]

    # 2. Create child organization unit (Unit B under A)
    u_b_resp = client.post("/api/v3/workforce-planning/organization-units", json={
        "code": "OU-INFRA-TEAM",
        "name": "Cloud Infrastructure Team",
        "unit_type": "TEAM",
        "parent_id": u_a_id,
        "active": True,
        "effective_from": "2026-01-01",
    })
    assert u_b_resp.status_code in [200, 201]
    u_b = u_b_resp.json()
    u_b_id = u_b["id"]

    # 3. Create grandchild organization unit (Unit C under B)
    u_c_resp = client.post("/api/v3/workforce-planning/organization-units", json={
        "code": "OU-SRE-POD",
        "name": "Site Reliability Pod",
        "unit_type": "PROJECT",
        "parent_id": u_b_id,
        "active": True,
        "effective_from": "2026-01-01",
    })
    assert u_c_resp.status_code in [200, 201]
    u_c = u_c_resp.json()
    u_c_id = u_c["id"]

    # 4. CIRCULAR HIERARCHY PREVENTION:
    # Attempting to make Unit A's parent be Unit C (its grandchild) MUST BE REJECTED (HTTP 400)
    cycle_resp = client.put(f"/api/v3/workforce-planning/organization-units/{u_a_id}", json={
        "parent_id": u_c_id,
    })
    assert cycle_resp.status_code == 400
    assert "circular" in cycle_resp.json().get("detail", "").lower()

    # Attempting to make Unit A's parent be itself MUST BE REJECTED (HTTP 400)
    self_cycle = client.put(f"/api/v3/workforce-planning/organization-units/{u_a_id}", json={
        "parent_id": u_a_id,
    })
    assert self_cycle.status_code == 400
    assert "own parent" in self_cycle.json().get("detail", "").lower()

    # 5. Tree Query
    tree_resp = client.get("/api/v3/workforce-planning/organization-units?tree=true")
    assert tree_resp.status_code == 200
    tree = tree_resp.json()
    assert len(tree) >= 1


def test_position_crud_and_capacity_validation():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # Fetch an org unit
    ou_resp = client.get("/api/v3/workforce-planning/organization-units")
    assert ou_resp.status_code == 200
    ous = ou_resp.json()
    assert len(ous) >= 1
    ou_id = ous[0]["id"]

    # 1. Create a Position with headcount capacity = 1.0
    pos_resp = client.post("/api/v3/workforce-planning/positions", json={
        "position_code": "POS-SEC-LEAD",
        "title": "Principal Security Engineer",
        "organization_unit_id": ou_id,
        "job_family": "Information Security",
        "job_level": "Principal / L6",
        "employment_type": "FULL_TIME",
        "location": "Remote",
        "status": "OPEN",
        "headcount_capacity": 1.0,
        "budgeted_cost": 4500000.0,
        "currency": "INR",
        "effective_from": "2026-01-01",
    })
    assert pos_resp.status_code in [200, 201]
    pos_data = pos_resp.json()
    pos_id = pos_data["id"]
    assert pos_data["position_code"] == "POS-SEC-LEAD"
    assert pos_data["filled_count"] == 0.0

    # 2. Get demo person
    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    persons = db.query(Person).all()
    assert len(persons) >= 2
    p1_id = persons[0].id
    p2_id = persons[1].id
    db.close()

    # 3. Assign Person 1 (100% allocation -> filled_count = 1.0)
    assign1_resp = client.post(f"/api/v3/workforce-planning/positions/{pos_id}/assign", json={
        "position_id": pos_id,
        "person_id": p1_id,
        "allocation_percentage": 100.0,
        "assignment_type": "PRIMARY",
        "effective_from": "2026-01-01",
    })
    assert assign1_resp.status_code in [200, 201]
    a1_data = assign1_resp.json()
    assert a1_data["person_id"] == p1_id

    # Verify position is now FILLED
    get_pos = client.get(f"/api/v3/workforce-planning/positions/{pos_id}")
    assert get_pos.status_code == 200
    pos_updated = get_pos.json()
    assert pos_updated["filled_count"] == 1.0
    assert pos_updated["status"] == "FILLED"

    # 4. CAPACITY EXCEEDED CHECK:
    # Attempting to assign Person 2 with additional 50% must be REJECTED (HTTP 400)
    assign2_resp = client.post(f"/api/v3/workforce-planning/positions/{pos_id}/assign", json={
        "position_id": pos_id,
        "person_id": p2_id,
        "allocation_percentage": 50.0,
        "assignment_type": "SECONDARY",
        "effective_from": "2026-01-01",
    })
    assert assign2_resp.status_code == 400
    assert "capacity" in assign2_resp.json().get("detail", "").lower()


def test_primary_assignment_overlap_prevention():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    ou_resp = client.get("/api/v3/workforce-planning/organization-units")
    ou_id = ou_resp.json()[0]["id"]

    # Create two separate positions
    p_a = client.post("/api/v3/workforce-planning/positions", json={
        "position_code": "POS-ROLE-A",
        "title": "Role A",
        "organization_unit_id": ou_id,
        "status": "OPEN",
        "headcount_capacity": 1.0,
        "effective_from": "2026-01-01",
    }).json()

    p_b = client.post("/api/v3/workforce-planning/positions", json={
        "position_code": "POS-ROLE-B",
        "title": "Role B",
        "organization_unit_id": ou_id,
        "status": "OPEN",
        "headcount_capacity": 1.0,
        "effective_from": "2026-01-01",
    }).json()

    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    target_person = db.query(Person).first()
    person_id = target_person.id
    db.close()

    # Delete any prior assignments for clean state
    cur_ass = client.get(f"/api/v3/workforce-planning/position-assignments?person_id={person_id}").json()
    for a in cur_ass:
        client.delete(f"/api/v3/workforce-planning/position-assignments/{a['id']}")

    # 1. Assign to Role A as PRIMARY
    res1 = client.post(f"/api/v3/workforce-planning/positions/{p_a['id']}/assign", json={
        "position_id": p_a["id"],
        "person_id": person_id,
        "allocation_percentage": 100.0,
        "assignment_type": "PRIMARY",
        "effective_from": "2026-01-01",
    })
    assert res1.status_code in [200, 201]

    # 2. Attempting another concurrent PRIMARY assignment to Role B must FAIL (HTTP 400)
    res2 = client.post(f"/api/v3/workforce-planning/positions/{p_b['id']}/assign", json={
        "position_id": p_b["id"],
        "person_id": person_id,
        "allocation_percentage": 100.0,
        "assignment_type": "PRIMARY",
        "effective_from": "2026-01-01",
    })
    assert res2.status_code == 400
    assert "primary" in res2.json().get("detail", "").lower()
