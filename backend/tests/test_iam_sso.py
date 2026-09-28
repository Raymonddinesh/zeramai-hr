"""
test_iam_sso.py - Module 14 Enterprise Identity Federation & SSO Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models_integrations import IdentityProviderConfig, EncryptedSecret

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
}


def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
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


def test_create_and_query_oidc_identity_provider():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create OIDC Provider with confidential client secret
    raw_secret = "super-secret-client-secret-xyz-12345"
    resp = client.post("/api/v3/integrations/identity/configs", json={
        "provider_name": "Corporate Okta OIDC",
        "protocol": "OIDC",
        "issuer": "https://company.okta.com/oauth2/default",
        "client_id": "0oa12345678abcdef",
        "client_secret": raw_secret,
        "authorization_url": "https://company.okta.com/oauth2/default/v1/authorize",
        "token_url": "https://company.okta.com/oauth2/default/v1/token",
        "enabled": True,
        "default_provider": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    config_id = data["id"]
    assert data["provider_name"] == "Corporate Okta OIDC"
    assert data["has_secret"] is True
    # Ensure raw secret is NEVER returned in response
    assert "client_secret" not in data or data.get("client_secret") is None
    assert raw_secret not in str(data)

    # 2. Verify raw secret is NOT stored in plaintext in the database
    db: Session = SessionLocal()
    try:
        cfg = db.query(IdentityProviderConfig).filter(IdentityProviderConfig.id == config_id).first()
        assert cfg is not None
        assert cfg.client_secret_reference is not None

        secret_record = db.query(EncryptedSecret).filter(EncryptedSecret.id == cfg.client_secret_reference).first()
        assert secret_record is not None
        assert secret_record.ciphertext != raw_secret
        assert raw_secret not in secret_record.ciphertext
    finally:
        db.close()

    # 3. Test IDP configuration endpoint
    test_resp = client.post(f"/api/v3/integrations/identity/configs/{config_id}/test", json={})
    assert test_resp.status_code == 200
    assert test_resp.json()["success"] is True

    # 4. List configs
    list_resp = client.get("/api/v3/integrations/identity/configs")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(i["id"] == config_id for i in items)

    # 5. Cleanup
    del_resp = client.delete(f"/api/v3/integrations/identity/configs/{config_id}")
    assert del_resp.status_code == 204


def test_create_saml_identity_provider():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    saml_xml = "<EntityDescriptor entityID='https://login.microsoftonline.com/tenant/v2'></EntityDescriptor>"
    raw_cert = "-----BEGIN CERTIFICATE-----\nMIIDXTCCAkWgAwIBAgIJAL...\n-----END CERTIFICATE-----"

    resp = client.post("/api/v3/integrations/identity/configs", json={
        "provider_name": "Microsoft Entra SAML",
        "protocol": "SAML",
        "saml_metadata": saml_xml,
        "saml_certificate": raw_cert,
        "enabled": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    config_id = data["id"]
    assert data["protocol"] == "SAML"
    assert data["has_certificate"] is True
    assert raw_cert not in str(data)

    # Cleanup
    del_resp = client.delete(f"/api/v3/integrations/identity/configs/{config_id}")
    assert del_resp.status_code == 204
