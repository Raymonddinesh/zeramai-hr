"""
test_api_keys.py - Module 14 Scoped API Key Management Tests.
"""
import hashlib
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models_integrations import APIKey
from app.services.integration_service import IntegrationService

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


def test_api_key_lifecycle_creation_verification_rotation_revocation():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create API Key
    resp = client.post("/api/v3/integrations/api-keys", json={
        "name": "Payroll Service CI",
        "scopes": ["employee:read", "payroll:read"],
        "expires_in_days": 30,
    })
    assert resp.status_code == 201
    data = resp.json()
    key_id = data["id"]
    raw_key = data["raw_api_key"]
    assert raw_key.startswith("zm_live_")
    assert data["key_prefix"] == raw_key[:12]

    # 2. Verify database security: raw key must NEVER be stored in the database
    db: Session = SessionLocal()
    try:
        record = db.query(APIKey).filter(APIKey.id == key_id).first()
        assert record is not None
        assert record.key_hash == hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        assert raw_key != record.key_hash

        # 3. Verify key validation logic
        valid_key = IntegrationService.verify_api_key(db, raw_key, required_scope="employee:read")
        assert valid_key is not None
        assert valid_key.id == key_id

        # Verify denied scope
        unauthorized_key = IntegrationService.verify_api_key(db, raw_key, required_scope="admin:write")
        assert unauthorized_key is None
    finally:
        db.close()

    # 4. List keys endpoint must only return prefix, never raw key or hash
    list_resp = client.get("/api/v3/integrations/api-keys")
    assert list_resp.status_code == 200
    keys_list = list_resp.json()
    target_key = next((k for k in keys_list if k["id"] == key_id), None)
    assert target_key is not None
    assert "raw_api_key" not in target_key
    assert "key_hash" not in target_key
    assert target_key["key_prefix"] == raw_key[:12]

    # 5. Rotate key
    rotate_resp = client.post(f"/api/v3/integrations/api-keys/{key_id}/rotate")
    assert rotate_resp.status_code == 200
    new_raw_key = rotate_resp.json()["new_raw_api_key"]
    assert new_raw_key.startswith("zm_live_")
    assert new_raw_key != raw_key

    # Old key must no longer work, new key works
    db = SessionLocal()
    try:
        assert IntegrationService.verify_api_key(db, raw_key, "employee:read") is None
        assert IntegrationService.verify_api_key(db, new_raw_key, "employee:read") is not None
    finally:
        db.close()

    # 6. Revoke key
    revoke_resp = client.delete(f"/api/v3/integrations/api-keys/{key_id}")
    assert revoke_resp.status_code == 204

    # Revoked key must not validate
    db = SessionLocal()
    try:
        assert IntegrationService.verify_api_key(db, new_raw_key, "employee:read") is None
    finally:
        db.close()
