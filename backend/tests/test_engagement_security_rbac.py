"""
test_engagement_security_rbac.py - Module 19: Security, RBAC & Multi-Tenant IDOR Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, Person, User

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
    "MANAGER": ("manager@zeramai.com", "ChangeMe123!"),
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


def test_rbac_access_controls():
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    # 1. Employee cannot create survey template -> Expect HTTP 403
    t_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Unauthorized Template",
        "survey_type": "ENGAGEMENT",
    })
    assert t_resp.status_code == 403

    # 2. Employee cannot create survey campaign -> Expect HTTP 403
    c_resp = client.post("/api/v3/engagement/campaigns", json={
        "template_id": "dummy-id",
        "name": "Unauthorized Campaign",
        "start_at": datetime.utcnow().isoformat(),
        "end_at": (datetime.utcnow() + timedelta(days=5)).isoformat(),
    })
    assert c_resp.status_code == 403

    # 3. Employee cannot review award nominations -> Expect HTTP 403
    rev_resp = client.put("/api/v3/engagement/awards/nominations/dummy-id/review", json={
        "status": "APPROVED",
    })
    assert rev_resp.status_code == 403

    # 4. Employee cannot access HR dashboard -> Expect HTTP 403
    dash_resp = client.get("/api/v3/engagement/dashboard")
    assert dash_resp.status_code == 403

    # 5. Employee CAN access own experience dashboard -> Expect HTTP 200
    my_exp = client.get("/api/v3/engagement/my-experience")
    assert my_exp.status_code == 200

    # 6. Manager CAN access team dashboard -> Expect HTTP 200
    mgr_token = login(*CREDENTIALS["MANAGER"])
    set_auth(mgr_token)
    team_dash = client.get("/api/v3/engagement/team-dashboard")
    assert team_dash.status_code == 200

    # 7. HR Admin CAN access tenant HR dashboard -> Expect HTTP 200
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    hr_dash = client.get("/api/v3/engagement/dashboard")
    assert hr_dash.status_code == 200


def test_multi_tenant_idor_isolation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create a template in tenant A (default)
    t_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Tenant A Secret Survey Template",
        "survey_type": "ENGAGEMENT",
    })
    assert t_resp.status_code == 201
    tmpl_id = t_resp.json()["id"]

    # 2. Attempt to read this template from Tenant B via X-Tenant-ID header -> Expect HTTP 404
    headers = {"X-Tenant-ID": "foreign-isolated-tenant-999"}
    idor_resp = client.get(f"/api/v3/engagement/templates/{tmpl_id}", headers=headers)
    assert idor_resp.status_code == 404

    # 3. Attempt to delete from Tenant B -> Expect HTTP 404
    del_resp = client.delete(f"/api/v3/engagement/templates/{tmpl_id}", headers=headers)
    assert del_resp.status_code == 404
