"""
test_governance_privacy.py - Module 15: DSR / Privacy Requests, Sanitized Data Subject Export, Controlled Anonymization.
"""
import os
from datetime import datetime, date
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Person, User, UserRole, Engagement, Document, DocumentStatus, EngagementStatus, EngagementType
from app.models_governance import LegalHold, LegalHoldTarget, LegalHoldStatus, PrivacyRequestStatus

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


def test_privacy_request_lifecycle():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Register a privacy request
    resp = client.post("/api/v3/governance/privacy-requests", json={
        "request_type": "ACCESS",
        "processing_notes": "Employee requesting full personal data record",
    })
    assert resp.status_code == 201
    data = resp.json()
    req_id = data["id"]
    assert data["status"] == "SUBMITTED"
    assert data["request_type"] == "ACCESS"
    assert data["due_at"] is not None

    # 2. Update status to IN_REVIEW
    patch_resp = client.patch(f"/api/v3/governance/privacy-requests/{req_id}/status", json={
        "status": "IN_REVIEW",
        "processing_notes": "Identity verified with corporate email",
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "IN_REVIEW"


def test_privacy_sanitized_export():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    db = SessionLocal()
    try:
        # Create test person with sensitive details
        person = Person(
            full_name="Rajesh Kumar Sharma",
            preferred_name="Raj",
            email="rajesh.sharma@example.com",
            phone="+91-9876543210",
            current_address="123 Tech Residency, Bengaluru",
            permanent_address="456 Heritage Enclave, Delhi",
            emergency_contact="Sunita Sharma (+91-9876543211)",
            date_of_birth=date(1992, 5, 14),
            gender="Male"
        )
        db.add(person)
        db.commit()
        db.refresh(person)

        # Create user account with hashed password
        user = User(
            email="rajesh.sharma@example.com",
            hashed_password="bcrypt$supersecret_password_hash",
            role=UserRole.EMPLOYEE,
            person_id=person.id,
            is_active=True
        )
        db.add(user)

        # Create Engagement
        eng = Engagement(
            person_id=person.id,
            designation="Lead Software Engineer",
            department="Engineering",
            start_date=date(2022, 1, 1),
            status=EngagementStatus.ACTIVE,
            engagement_type=EngagementType.FULL_TIME_EMPLOYEE
        )
        db.add(eng)

        # Create Document
        doc = Document(
            person_id=person.id,
            document_type="PAN_CARD",
            file_name="pan_card_verified.pdf",
            storage_key="docs/pan_card_verified.pdf",
            status=DocumentStatus.VERIFIED
        )
        db.add(doc)
        db.commit()

        # Create privacy request for export
        req_resp = client.post("/api/v3/governance/privacy-requests", json={
            "person_id": person.id,
            "request_type": "EXPORT"
        })
        assert req_resp.status_code == 201
        req_id = req_resp.json()["id"]

        # Call export endpoint
        export_resp = client.post(f"/api/v3/governance/privacy-requests/{req_id}/export")
        assert export_resp.status_code == 200
        payload = export_resp.json()
        assert payload["person_id"] == person.id
        data = payload["data"]

        # Verify Person info is accurately assembled
        assert data["person"]["full_name"] == "Rajesh Kumar Sharma"
        assert data["person"]["email"] == "rajesh.sharma@example.com"

        # STRICT SECURITY CHECK: No passwords or secret keys leaked
        assert data["user_account"]["password_hash"] == "[REDACTED_SECURITY_POLICY]"
        export_str = str(data)
        assert "supersecret_password_hash" not in export_str
        assert "bcrypt" not in export_str

        # Verify engagements and documents metadata included
        assert len(data["engagements"]) >= 1
        assert data["engagements"][0]["designation"] == "Lead Software Engineer"
        assert len(data["documents"]) >= 1
        assert data["documents"][0]["document_type"] == "PAN_CARD"

        # Verify statutory retention notice is present
        assert "Income Tax Act 1961" in data["statutory_records_notice"]

    finally:
        db.close()


def test_privacy_controlled_anonymization_and_legal_hold_blocking():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    db = SessionLocal()
    try:
        # Create person for erasure testing
        person = Person(
            full_name="Priya Patel",
            preferred_name="Priya",
            email="priya.patel@example.com",
            phone="+91-9123456789",
            current_address="Flat 4B, Cyber Towers, Hyderabad",
        )
        db.add(person)
        db.commit()
        db.refresh(person)

        user = User(
            email="priya.patel@example.com",
            hashed_password="hashed_pass_priya",
            role=UserRole.EMPLOYEE,
            person_id=person.id,
            is_active=True
        )
        db.add(user)
        db.commit()

        from app.models_v3 import Tenant
        tenant = db.query(Tenant).first()
        t_id = tenant.id if tenant else "default-tenant"

        # Step 1: Place an active Legal Hold on Priya Patel
        hold = LegalHold(
            tenant_id=t_id,
            name="Regulatory Inquiry",
            matter_reference="REG-2026-001",
            status=LegalHoldStatus.ACTIVE.value,
            issued_at=datetime.utcnow(),
            created_by="admin"
        )
        db.add(hold)
        db.flush()

        target = LegalHoldTarget(
            tenant_id=t_id,
            legal_hold_id=hold.id,
            target_type="PERSON",
            target_reference=person.id
        )
        db.add(target)
        db.commit()

        # Step 2: Attempt erasure while legal hold is active -> MUST BE BLOCKED
        req_resp = client.post("/api/v3/governance/privacy-requests", json={
            "person_id": person.id,
            "request_type": "ANONYMIZATION"
        })
        assert req_resp.status_code == 201
        req_id = req_resp.json()["id"]

        anon_resp = client.post(f"/api/v3/governance/privacy-requests/{req_id}/anonymize")
        assert anon_resp.status_code == 200
        res_data = anon_resp.json()
        assert res_data["blocked_by_legal_hold"] is True
        assert res_data["success"] is False
        assert "blocked" in res_data["message"].lower()

        # Verify person PII is STILL INTACT because hold was active
        db.refresh(person)
        assert person.full_name == "Priya Patel"
        assert person.email == "priya.patel@example.com"

        # Step 3: Release the legal hold
        hold.status = LegalHoldStatus.RELEASED.value
        hold.released_at = datetime.utcnow()
        db.commit()

        # Step 4: Re-attempt anonymization -> SHOULD NOW SUCCEED
        anon_resp2 = client.post(f"/api/v3/governance/privacy-requests/{req_id}/anonymize")
        assert anon_resp2.status_code == 200
        res_data2 = anon_resp2.json()
        assert res_data2["blocked_by_legal_hold"] is False
        assert res_data2["success"] is True

        # Verify person PII is pseudonymized
        db.refresh(person)
        assert person.full_name == "Anonymized Employee"
        assert person.preferred_name is None
        assert person.email.startswith("anonymized_")
        assert person.phone == "REDACTED"
        assert person.current_address == "REDACTED"

        # Verify user account is deactivated
        db.refresh(user)
        assert user.is_active is False
        assert user.email.startswith("anonymized_")

        # Verify statutory preservation notice
        preserved = res_data2["preserved_records"]
        assert any("Income Tax" in p for p in preserved)
        assert any("Provident Fund" in p for p in preserved)

    finally:
        db.close()
