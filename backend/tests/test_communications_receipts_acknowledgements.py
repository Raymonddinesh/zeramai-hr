"""
test_communications_receipts_acknowledgements.py - Module 20: Read Receipts, Acknowledgements & Preferences
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, User, Person
from app.models_communications import CommunicationAcknowledgement
from app.models_policy_er import PolicyAcknowledgementRecord

client = TestClient(app)

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


def test_announcement_read_receipt_idempotency():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Create published announcement
    resp_ann = client.post("/api/v3/communications/announcements", json={
        "title": "Idempotent Read Receipt Test Announcement",
        "content_reference": "Read receipt test details.",
        "announcement_type": "GENERAL",
        "priority": "NORMAL",
    })
    ann_id = resp_ann.json()["id"]
    client.post(f"/api/v3/communications/announcements/{ann_id}/publish")

    # Employee records read receipt
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    resp_read1 = client.post(f"/api/v3/communications/announcements/{ann_id}/read")
    assert resp_read1.status_code == 200
    receipt1 = resp_read1.json()
    assert receipt1["announcement_id"] == ann_id

    # Call read again (idempotent verification)
    resp_read2 = client.post(f"/api/v3/communications/announcements/{ann_id}/read")
    assert resp_read2.status_code == 200
    receipt2 = resp_read2.json()
    assert receipt2["id"] == receipt1["id"]


def test_communication_acknowledgement_lifecycle():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create announcement that DOES require acknowledgement
    resp1 = client.post("/api/v3/communications/announcements", json={
        "title": "Mandatory Security Awareness Confirmation",
        "content_reference": "All staff must acknowledge reading the clean desk policy.",
        "announcement_type": "COMPLIANCE",
        "priority": "HIGH",
        "acknowledgement_required": True,
    })
    ann1_id = resp1.json()["id"]
    client.post(f"/api/v3/communications/announcements/{ann1_id}/publish")

    # 2. Create announcement that does NOT require acknowledgement
    resp2 = client.post("/api/v3/communications/announcements", json={
        "title": "Informational Campus Cafe Menu Update",
        "content_reference": "Weekly special menu options.",
        "announcement_type": "GENERAL",
        "priority": "LOW",
        "acknowledgement_required": False,
    })
    ann2_id = resp2.json()["id"]
    client.post(f"/api/v3/communications/announcements/{ann2_id}/publish")

    # 3. Employee acknowledges ann1 (must succeed)
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    resp_ack = client.post(f"/api/v3/communications/announcements/{ann1_id}/acknowledge", json={
        "announcement_id": ann1_id,
        "acknowledgement_reference": "CLEAN_DESK_ACK_2026",
    })
    assert resp_ack.status_code == 200
    assert resp_ack.json()["announcement_id"] == ann1_id

    # 4. Employee acknowledges ann2 (must fail because acknowledgement_required is False)
    resp_bad_ack = client.post(f"/api/v3/communications/announcements/{ann2_id}/acknowledge", json={
        "announcement_id": ann2_id,
    })
    assert resp_bad_ack.status_code == 400
    assert "does not require an acknowledgement" in resp_bad_ack.json()["detail"]


def test_policy_acknowledgement_separation():
    """Verify that communication announcements use CommunicationAcknowledgement, not PolicyAcknowledgementRecord."""
    db = SessionLocal()
    try:
        # Query CommunicationAcknowledgement table directly
        comm_acks = db.query(CommunicationAcknowledgement).all()
        assert len(comm_acks) >= 1

        # Verify they are separate model instances from Module 8 PolicyAcknowledgementRecord
        for ack in comm_acks:
            assert hasattr(ack, "announcement_id")
            assert not hasattr(ack, "policy_id")
    finally:
        db.close()


def test_communication_preferences_safety():
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    # 1. Update GENERAL preferences (disable email, enable in-app) - Should succeed
    resp_gen = client.put("/api/v3/communications/preferences/GENERAL", json={
        "email_enabled": False,
        "in_app_enabled": True,
    })
    assert resp_gen.status_code == 200
    assert resp_gen.json()["email_enabled"] is False

    # 2. Attempt to disable mandatory HR in-app delivery - Must be blocked with 400
    resp_hr = client.put("/api/v3/communications/preferences/HR", json={
        "in_app_enabled": False,
    })
    assert resp_hr.status_code == 400
    assert "Mandatory HR" in resp_hr.json()["detail"]
