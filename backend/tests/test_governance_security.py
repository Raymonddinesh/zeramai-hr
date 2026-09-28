"""
test_governance_security.py - Module 15: RBAC Enforcement & Multi-Tenant Isolation Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

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


def test_rbac_governance_access_control():
    # 1. Employee cannot view governance dashboard
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    dash_resp = client.get("/api/v3/governance/dashboard")
    assert dash_resp.status_code == 403

    # 2. Employee cannot trigger lifecycle evaluation
    eval_resp = client.post("/api/v3/governance/lifecycle/evaluate", json={"dry_run": False})
    assert eval_resp.status_code == 403

    # 3. Employee cannot create legal holds
    hold_resp = client.post("/api/v3/governance/legal-holds", json={
        "name": "Unauthorized Hold",
        "matter_reference": "ILLEGAL-01"
    })
    assert hold_resp.status_code == 403

    # 4. Employee cannot create retention policies
    ret_resp = client.post("/api/v3/governance/retention-policies", json={
        "name": "Unauthorized Retention",
        "record_type": "PAYROLL",
        "retention_period_days": 30,
        "archive_after_days": 10,
    })
    assert ret_resp.status_code == 403


def test_multi_tenant_isolation_in_governance():
    admin_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(admin_token)

    # 1. Tenant Alpha creates a legal hold
    alpha_resp = client.post(
        "/api/v3/governance/legal-holds",
        json={
            "name": "Alpha Confidential Investigation",
            "matter_reference": "ALPHA-CASE-101",
        },
        headers={"X-Tenant-ID": "tenant-alpha"}
    )
    assert alpha_resp.status_code == 201
    alpha_hold_id = alpha_resp.json()["id"]

    # 2. Tenant Beta queries legal holds -> Alpha hold must NOT be present
    beta_list_resp = client.get(
        "/api/v3/governance/legal-holds",
        headers={"X-Tenant-ID": "tenant-beta"}
    )
    assert beta_list_resp.status_code == 200
    beta_holds = beta_list_resp.json()
    assert not any(h["id"] == alpha_hold_id for h in beta_holds)

    # 3. Tenant Beta attempts direct IDOR fetch of Alpha's legal hold -> MUST RETURN 404
    beta_get_resp = client.get(
        f"/api/v3/governance/legal-holds/{alpha_hold_id}",
        headers={"X-Tenant-ID": "tenant-beta"}
    )
    assert beta_get_resp.status_code == 404
