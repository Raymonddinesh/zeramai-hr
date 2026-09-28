"""
test_scim_provisioning.py - RFC 7643 & RFC 7644 SCIM 2.0 Inbound Provisioning Tests.
"""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import User, Person
from app.models_integrations import SCIMConfiguration, SCIMProvisioningEvent

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


def test_scim_discovery_endpoints():
    # 1. ServiceProviderConfig
    resp = client.get("/api/v3/scim/v2/ServiceProviderConfig")
    assert resp.status_code == 200
    data = resp.json()
    assert "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig" in data["schemas"]
    assert data["patch"]["supported"] is True

    # 2. Schemas
    resp = client.get("/api/v3/scim/v2/Schemas")
    assert resp.status_code == 200
    assert resp.json()["totalResults"] >= 2

    # 3. ResourceTypes
    resp = client.get("/api/v3/scim/v2/ResourceTypes")
    assert resp.status_code == 200
    assert len(resp.json()["Resources"]) >= 2


def test_scim_user_lifecycle_provision_patch_deprovision():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # Configure SCIM bearer token
    scim_token = f"zm_scim_{uuid.uuid4().hex}"
    client.post("/api/v3/integrations/scim/config", json={
        "provider_name": "Microsoft Entra ID",
        "bearer_token": scim_token,
        "enabled": True,
        "auto_provision": True,
        "auto_deprovision": True,
    })

    # SCIM Headers
    headers = {"Authorization": f"Bearer {scim_token}"}

    # 1. Provision User via SCIM POST /Users
    test_email = f"scim.employee.{uuid.uuid4().hex[:6]}@example.com"
    create_payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": test_email,
        "name": {
            "givenName": "Alex",
            "familyName": "Vance",
        },
        "emails": [{"value": test_email, "type": "work", "primary": True}],
        "active": True,
        "externalId": f"ext-{test_email}",
    }

    create_resp = client.post("/api/v3/scim/v2/Users", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    scim_user = create_resp.json()
    user_id = scim_user["id"]
    assert scim_user["userName"] == test_email
    assert scim_user["active"] is True
    assert "Location" in create_resp.headers

    # 2. Retrieve SCIM User via GET /Users/{id}
    get_resp = client.get(f"/api/v3/scim/v2/Users/{user_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == user_id

    # 3. Filter Users via GET /Users?filter=userName eq "..."
    filter_resp = client.get(f"/api/v3/scim/v2/Users?filter=userName eq \"{test_email}\"", headers=headers)
    assert filter_resp.status_code == 200
    assert filter_resp.json()["totalResults"] >= 1

    # 4. Inbound SCIM PATCH to deprovision/deactivate (active=False)
    patch_payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "active",
                "value": False,
            }
        ],
    }
    patch_resp = client.patch(f"/api/v3/scim/v2/Users/{user_id}", json=patch_payload, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["active"] is False

    # 5. Check Person and historical records are preserved in database
    db: Session = SessionLocal()
    try:
        user_record = db.query(User).filter(User.id == user_id).first()
        assert user_record is not None
        assert user_record.is_active is False
        assert user_record.person_id is not None

        person_record = db.query(Person).filter(Person.id == user_record.person_id).first()
        assert person_record is not None
        assert person_record.email == test_email

        # 6. Verify SCIM Provisioning Events were logged
        events = db.query(SCIMProvisioningEvent).filter(SCIMProvisioningEvent.user_id == user_id).all()
        assert len(events) >= 2  # USER_CREATED and USER_DEPROVISIONED/USER_UPDATED
    finally:
        db.close()

    # 7. Deprovision User via SCIM DELETE /Users/{id}
    del_resp = client.delete(f"/api/v3/scim/v2/Users/{user_id}", headers=headers)
    assert del_resp.status_code == 204


def test_scim_groups_endpoint():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/scim/v2/Groups")
    assert resp.status_code == 200
    data = resp.json()
    assert "urn:ietf:params:scim:api:messages:2.0:ListResponse" in data["schemas"]
    assert data["totalResults"] > 0
    first_group = data["Resources"][0]
    assert "displayName" in first_group
