"""
test_integrations_hub.py - Module 14 Integration Catalog, Connections, Outbox & Telemetry Tests.
"""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Person, User
from app.models_integrations import (
    IntegrationConnection,
    IntegrationEvent,
    IntegrationExecutionLog,
    IntegrationProvider,
    OutboxStatus,
)
from app.services.integration_service import IntegrationService

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
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


def test_integration_catalog_and_connection_lifecycle():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Query Providers Catalog
    cat_resp = client.get("/api/v3/integrations/providers")
    assert cat_resp.status_code == 200
    providers = cat_resp.json()
    assert len(providers) >= 4
    codes = [p["code"] for p in providers]
    assert "entra_id" in codes
    assert "slack" in codes

    entra_provider = next(p for p in providers if p["code"] == "entra_id")

    # 2. Create Connection to Entra ID
    conn_resp = client.post("/api/v3/integrations/connections", json={
        "provider_id": entra_provider["id"],
        "name": "Production Azure AD Directory",
        "environment": "PRODUCTION",
        "configuration_json": {
            "tenant_domain": "zeramai.onmicrosoft.com",
            "client_id": "client-id-12345",
        },
        "secret_value": "mock_client_secret_value",
    })
    assert conn_resp.status_code == 201
    conn_data = conn_resp.json()
    conn_id = conn_data["id"]
    assert conn_data["has_credentials"] is True

    # 3. Test Connection
    test_resp = client.post(f"/api/v3/integrations/connections/{conn_id}/test", json={})
    assert test_resp.status_code == 200
    assert test_resp.json()["success"] is True

    # 4. Trigger Outbox Event for Employee Onboarding
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "employee@example.com").first()
        assert user is not None
        evt = IntegrationService.handle_employee_onboarded(
            db=db,
            tenant_id=conn_data["tenant_id"],
            person_id=user.person_id,
            user_id=user.id,
        )
        db.commit()
        evt_id = evt.id
    finally:
        db.close()

    # 5. Verify Outbox Listing
    outbox_resp = client.get("/api/v3/integrations/outbox")
    assert outbox_resp.status_code == 200
    events = outbox_resp.json()
    assert any(e["id"] == evt_id for e in events)

    # 6. Process Outbox Batch
    proc_resp = client.post("/api/v3/integrations/outbox/process")
    assert proc_resp.status_code == 200
    assert proc_resp.json()["processed_count"] >= 1

    # 7. Check Execution Telemetry Logs
    logs_resp = client.get("/api/v3/integrations/logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) >= 1
    assert any(l["connection_id"] == conn_id for l in logs)

    # 8. Cleanup Connection
    del_resp = client.delete(f"/api/v3/integrations/connections/{conn_id}")
    assert del_resp.status_code == 204
