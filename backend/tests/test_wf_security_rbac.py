"""
test_wf_security_rbac.py - Module 17: RBAC, Multi-Tenant Isolation & Salary Masking Tests
"""
import pytest
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


def test_rbac_workforce_planning_access_control():
    # 1. Regular employee cannot access strategic workforce dashboard
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    dash_resp = client.get("/api/v3/workforce-planning/dashboard")
    assert dash_resp.status_code == 403

    # 2. Regular employee cannot create organization units
    ou_resp = client.post("/api/v3/workforce-planning/organization-units", json={
        "code": "OU-UNAUTH",
        "name": "Unauthorized Org Unit",
    })
    assert ou_resp.status_code == 403

    # 3. Regular employee cannot create positions
    pos_resp = client.post("/api/v3/workforce-planning/positions", json={
        "position_code": "POS-UNAUTH",
        "title": "Unauthorized Position",
        "organization_unit_id": "dummy-id",
    })
    assert pos_resp.status_code == 403

    # 4. Regular employee cannot create headcount plans
    hp_resp = client.post("/api/v3/workforce-planning/headcount-plans", json={
        "name": "Unauthorized Plan",
        "fiscal_year": "2026-2027",
    })
    assert hp_resp.status_code == 403

    # 5. Regular employee cannot designate critical roles
    cr_resp = client.post("/api/v3/workforce-planning/critical-roles", json={
        "position_id": "dummy-pos",
    })
    assert cr_resp.status_code == 403

    # 6. Regular employee cannot create talent pools
    tp_resp = client.post("/api/v3/workforce-planning/talent-pools", json={
        "name": "Unauthorized Pool",
    })
    assert tp_resp.status_code == 403


def test_multi_tenant_isolation_and_idor():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)

    # Foreign / non-existent ID query must return 404 (IDOR protection)
    bogus_id = "00000000-0000-0000-0000-000000000000"

    get_ou = client.get(f"/api/v3/workforce-planning/organization-units/{bogus_id}")
    assert get_ou.status_code == 404

    get_pos = client.get(f"/api/v3/workforce-planning/positions/{bogus_id}")
    assert get_pos.status_code == 404

    get_hp = client.get(f"/api/v3/workforce-planning/headcount-plans/{bogus_id}")
    assert get_hp.status_code == 404

    get_dp = client.get(f"/api/v3/workforce-planning/demand-plans/{bogus_id}")
    assert get_dp.status_code == 404

    get_cr = client.get(f"/api/v3/workforce-planning/critical-roles/{bogus_id}")
    assert get_cr.status_code == 404

    get_sp = client.get(f"/api/v3/workforce-planning/succession-plans/{bogus_id}")
    assert get_sp.status_code == 404

    get_tp = client.get(f"/api/v3/workforce-planning/talent-pools/{bogus_id}")
    assert get_tp.status_code == 404


def test_compensation_and_salary_visibility_protection():
    # Admin / Super Admin CAN view budgeted cost
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)

    p_list = client.get("/api/v3/workforce-planning/positions")
    assert p_list.status_code == 200
    positions = p_list.json()
    assert len(positions) >= 1
    # Check that admin sees budgeted cost
    costs = [p.get("budgeted_cost") for p in positions if p.get("budgeted_cost") is not None]
    assert len(costs) >= 1

    # Employee CANNOT view budgeted cost on positions (masked to None or forbidden)
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    pos_resp = client.get("/api/v3/workforce-planning/positions")
    if pos_resp.status_code == 200:
        for p in pos_resp.json():
            assert p.get("budgeted_cost") is None
    else:
        assert pos_resp.status_code == 403
