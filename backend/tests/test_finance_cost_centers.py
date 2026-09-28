"""
test_finance_cost_centers.py - Module 16: Cost Centers, Financial Dimensions & Allocations Tests
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


def test_cost_center_hierarchy_and_crud():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Create parent cost center
    p_resp = client.post("/api/v3/finance/cost-centers", json={
        "code": "CC-ENG-ROOT",
        "name": "Engineering Global",
        "description": "Global Engineering Division",
        "currency": "INR",
        "active": True,
    })
    assert p_resp.status_code in [200, 201]
    parent_data = p_resp.json()
    parent_id = parent_data["id"]
    assert parent_data["code"] == "CC-ENG-ROOT"

    # 2. Create child cost center linked to parent
    c_resp = client.post("/api/v3/finance/cost-centers", json={
        "code": "CC-ENG-AI",
        "name": "AI Platform Team",
        "description": "Core AI R&D and Model Engineering",
        "parent_cost_center_id": parent_id,
        "currency": "INR",
        "active": True,
    })
    assert c_resp.status_code in [200, 201]
    child_data = c_resp.json()
    assert child_data["parent_cost_center_id"] == parent_id

    # 3. List cost centers
    list_resp = client.get("/api/v3/finance/cost-centers")
    assert list_resp.status_code == 200
    ccs = list_resp.json()
    codes = [c["code"] for c in ccs]
    assert "CC-ENG-ROOT" in codes
    assert "CC-ENG-AI" in codes


def test_financial_dimensions_and_values():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Create Dimension
    dim_resp = client.post("/api/v3/finance/dimensions", json={
        "code": "PROJECT_TRACK",
        "name": "Project Tracking Dimension",
        "description": "Strategic project cost tracking",
        "is_active": True,
    })
    assert dim_resp.status_code in [200, 201]
    dim_data = dim_resp.json()
    dim_id = dim_data["id"]

    # 2. Add Dimension Values
    val_resp = client.post(f"/api/v3/finance/dimensions/{dim_id}/values", json={
        "code": "PRJ_NEBULA",
        "name": "Project Nebula NextGen",
        "is_active": True,
    })
    assert val_resp.status_code in [200, 201]
    val_data = val_resp.json()
    assert val_data["code"] == "PRJ_NEBULA"

    # 3. List Dimensions
    dims_resp = client.get("/api/v3/finance/dimensions")
    assert dims_resp.status_code == 200
    dims = dims_resp.json()
    assert any(d["code"] == "PROJECT_TRACK" for d in dims)


def test_employee_cost_allocation_validation():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    person = db.query(Person).first()
    person_id = person.id if person else "demo-person-1"
    db.close()

    # Get a cost center
    cc_resp = client.get("/api/v3/finance/cost-centers")
    assert cc_resp.status_code == 200
    cc_list = cc_resp.json()
    assert len(cc_list) >= 1
    cc1_id = cc_list[0]["id"]

    # 1. Create valid allocation of 60%
    alloc1 = client.post("/api/v3/finance/employee-allocations", json={
        "person_id": person_id,
        "cost_center_id": cc1_id,
        "percentage": 60.0,
        "effective_from": "2026-01-01",
        "is_active": True,
    })
    assert alloc1.status_code in [200, 201]

    # 2. Create another valid allocation of 40% (total = 100%)
    alloc2 = client.post("/api/v3/finance/employee-allocations", json={
        "person_id": person_id,
        "cost_center_id": cc1_id,
        "percentage": 40.0,
        "effective_from": "2026-01-01",
        "is_active": True,
    })
    assert alloc2.status_code in [200, 201]

    # 3. Attempting to add an additional 15% should be REJECTED (> 100%)
    alloc_fail = client.post("/api/v3/finance/employee-allocations", json={
        "person_id": person_id,
        "cost_center_id": cc1_id,
        "percentage": 15.0,
        "effective_from": "2026-01-01",
        "is_active": True,
    })
    assert alloc_fail.status_code == 400
    detail_msg = alloc_fail.json().get("detail", "")
    assert "exceed" in detail_msg.lower() and "100" in detail_msg
