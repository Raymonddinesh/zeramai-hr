"""
test_integrations_security.py - Module 14 RBAC, Cross-Tenant Isolation & Credential Security Tests.
"""
import os
import uuid
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
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


def test_rbac_denies_employee_access_to_admin_integrations():
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # 1. Employee cannot view or create connections
    assert client.get("/api/v3/integrations/connections").status_code == 403
    assert client.post("/api/v3/integrations/connections", json={
        "name": "Hacked Connection",
        "provider_id": "dummy",
    }).status_code == 403

    # 2. Employee cannot create API keys
    assert client.post("/api/v3/integrations/api-keys", json={
        "name": "Stolen Key",
        "scopes": ["*"],
    }).status_code == 403

    # 3. Employee cannot configure SSO
    assert client.post("/api/v3/integrations/identity/configs", json={
        "provider_name": "Rogue IDP",
        "protocol": "OIDC",
    }).status_code == 403

    # 4. Employee cannot configure webhooks
    assert client.post("/api/v3/integrations/webhooks", json={
        "name": "Rogue Webhook",
        "url": "https://attacker.com",
        "subscribed_events": ["*"],
    }).status_code == 403


def test_cross_tenant_isolation_on_connections_and_idp():
    # 1. Create connection as HR_ADMIN in Tenant A
    admin_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(admin_token)

    providers = client.get("/api/v3/integrations/providers").json()
    provider_id = providers[0]["id"]

    resp = client.post("/api/v3/integrations/connections", json={
        "name": "Tenant A Secret Connection",
        "provider_id": provider_id,
        "environment": "PRODUCTION",
    })
    assert resp.status_code == 201
    conn_id = resp.json()["id"]

    # 2. Query connection from another tenant
    foreign_tenant_id = str(uuid.uuid4())
    cross_resp = client.get(
        f"/api/v3/integrations/connections/{conn_id}",
        headers={"X-Tenant-ID": foreign_tenant_id},
    )
    assert cross_resp.status_code == 404

    # 3. Delete connection from another tenant fails with 404
    cross_del = client.delete(
        f"/api/v3/integrations/connections/{conn_id}",
        headers={"X-Tenant-ID": foreign_tenant_id},
    )
    assert cross_del.status_code == 404

    # 4. Cleanup in primary tenant
    client.delete(f"/api/v3/integrations/connections/{conn_id}")
