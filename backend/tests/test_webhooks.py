"""
test_webhooks.py - Module 14 Webhooks Platform Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models_integrations import WebhookEndpoint, WebhookDelivery, EncryptedSecret
from app.adapters.integration_adapter import GenericWebhookAdapter

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


def test_webhook_endpoint_lifecycle_and_hmac_signature():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Register Webhook Endpoint
    raw_secret = "whsec_custom_secret_key_12345"
    resp = client.post("/api/v3/integrations/webhooks", json={
        "name": "ERP Onboarding Subscriber",
        "url": "https://erp.company.com/api/webhooks/zeramai",
        "subscribed_events": ["employee.onboarded", "employee.offboarded"],
        "secret": raw_secret,
    })
    assert resp.status_code == 201
    data = resp.json()
    endpoint_id = data["id"]
    assert data["name"] == "ERP Onboarding Subscriber"
    assert "secret" not in data

    # 2. Verify signing secret is encrypted in database
    db: Session = SessionLocal()
    try:
        ep = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
        assert ep is not None
        assert ep.secret_reference is not None

        secret_rec = db.query(EncryptedSecret).filter(EncryptedSecret.id == ep.secret_reference).first()
        assert secret_rec is not None
        assert secret_rec.ciphertext != raw_secret
    finally:
        db.close()

    # 3. Test ping endpoint
    ping_resp = client.post(f"/api/v3/integrations/webhooks/{endpoint_id}/test", json={})
    assert ping_resp.status_code == 200
    assert ping_resp.json()["success"] is True

    # 4. Check delivery history
    deliv_resp = client.get(f"/api/v3/integrations/webhooks/{endpoint_id}/deliveries")
    assert deliv_resp.status_code == 200
    deliveries = deliv_resp.json()
    assert len(deliveries) >= 1
    assert deliveries[0]["status"] == "SUCCESS"
    assert deliveries[0]["event_type"] == "test.ping"

    # 5. Verify HMAC signature generation helper
    sig = GenericWebhookAdapter.generate_hmac_signature(
        secret=raw_secret,
        payload_bytes=b'{"test": 123}',
        timestamp=1700000000,
    )
    assert sig.startswith("t=1700000000,v1=")

    # 6. Cleanup
    del_resp = client.delete(f"/api/v3/integrations/webhooks/{endpoint_id}")
    assert del_resp.status_code == 204
