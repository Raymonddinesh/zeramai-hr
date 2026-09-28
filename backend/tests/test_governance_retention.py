"""
test_governance_retention.py - Module 15: Data Classification, Retention Policies, Lifecycle Evaluation & Legal Holds.
"""
import os
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models_governance import (
    DataClassification,
    DataAsset,
    RetentionPolicy,
    DataLifecycleRecord,
    LegalHold,
    LegalHoldTarget,
    RecordLifecycleStatus,
    LegalHoldStatus,
)
from app.models import Document, DocumentStatus, Person

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


def test_data_classification_catalog():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. List default classifications
    resp = client.get("/api/v3/governance/classifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    codes = [c["code"] for c in data]
    assert "PUBLIC" in codes
    assert "CONFIDENTIAL" in codes
    assert "RESTRICTED" in codes

    # 2. Create custom classification
    create_resp = client.post("/api/v3/governance/classifications", json={
        "code": "FINANCIAL_AUDIT",
        "name": "Financial Audit Records",
        "description": "Sensitive tax and accounting ledger items",
        "sensitivity_level": "RESTRICTED",
        "default_retention_days": 2555,
        "enabled": True,
    })
    assert create_resp.status_code == 201
    class_id = create_resp.json()["id"]

    # 3. Update classification
    update_resp = client.put(f"/api/v3/governance/classifications/{class_id}", json={
        "description": "Updated description for audit records"
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated description for audit records"


def test_data_assets_catalog():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # Get a classification ID
    classes = client.get("/api/v3/governance/classifications").json()
    conf_class_id = classes[0]["id"]

    resp = client.post("/api/v3/governance/assets", json={
        "name": "Employee Aadhaar and Tax Filings",
        "asset_type": "DATABASE_TABLE",
        "source_module": "Statutory",
        "classification_id": conf_class_id,
        "contains_personal_data": True,
        "contains_sensitive_personal_data": True,
        "data_residency": "IN-CENTRAL",
        "owner_user_id": "test-admin",
        "status": "ACTIVE",
    })
    assert resp.status_code == 201
    asset_id = resp.json()["id"]
    assert resp.json()["source_module"] == "Statutory"

    # List assets
    list_resp = client.get("/api/v3/governance/assets")
    assert list_resp.status_code == 200
    assets = list_resp.json()
    assert any(a["id"] == asset_id for a in assets)


def test_retention_policy_and_assignment():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create Retention Policy
    resp = client.post("/api/v3/governance/retention-policies", json={
        "name": "Candidate Interview Logs Retention",
        "description": "Retain interview recordings and scorecard records for 180 days",
        "record_type": "CANDIDATE",
        "retention_period_days": 180,
        "archive_after_days": 60,
        "deletion_after_days": 180,
        "legal_basis": "Internal Talent Acquisition Governance Standard",
        "jurisdiction": "IN",
        "enabled": True,
    })
    assert resp.status_code == 201
    policy_id = resp.json()["id"]

    # 2. Assign Policy
    assign_resp = client.post(f"/api/v3/governance/retention-policies/{policy_id}/assignments", json={
        "target_type": "DEPARTMENT",
        "target_reference": "Engineering",
        "effective_from": "2026-01-01",
    })
    assert assign_resp.status_code == 201
    assert assign_resp.json()["target_reference"] == "Engineering"


def test_lifecycle_evaluation_and_legal_hold_blocking():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    db = SessionLocal()
    try:
        # Create test document and aged lifecycle record
        now = datetime.utcnow()
        doc = Document(
            person_id="test-person-governance",
            document_type="ID_PROOF",
            file_name="passport_scan.pdf",
            storage_key="docs/passport_scan.pdf",
            status=DocumentStatus.VERIFIED,
            created_at=now - timedelta(days=400)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        from app.models_v3 import Tenant
        tenant = db.query(Tenant).first()
        t_id = tenant.id if tenant else "default-tenant"

        # Create retention policy for ID_PROOF / DOCUMENT: archive after 365 days, delete after 730 days
        policy = RetentionPolicy(
            tenant_id=t_id,
            name="Identity Documents Retention",
            record_type="DOCUMENT",
            retention_period_days=730,
            archive_after_days=365,
            deletion_after_days=730,
            legal_basis="KYC Norms",
            jurisdiction="IN",
            enabled=True,
            created_by="admin",
        )
        db.add(policy)

        # Create Lifecycle record aged 400 days
        lifecycle_rec = DataLifecycleRecord(
            tenant_id=t_id,
            asset_type="DOCUMENT",
            asset_id=doc.id,
            retention_policy_id=policy.id,
            lifecycle_status=RecordLifecycleStatus.ACTIVE.value,
            created_at=now - timedelta(days=400),
            last_evaluated_at=now - timedelta(days=30),
        )
        db.add(lifecycle_rec)
        db.commit()
        db.refresh(lifecycle_rec)

        # Run evaluation -> should become ARCHIVE_ELIGIBLE
        eval_resp = client.post("/api/v3/governance/lifecycle/evaluate", json={"dry_run": False})
        assert eval_resp.status_code == 200

        db.refresh(lifecycle_rec)
        assert lifecycle_rec.lifecycle_status == RecordLifecycleStatus.ARCHIVE_ELIGIBLE.value

        # Now place a LEGAL HOLD on this document
        hold_resp = client.post("/api/v3/governance/legal-holds", json={
            "name": "Investigation Hold on Passport",
            "matter_reference": "DISPUTE-2026-99",
            "targets": [{"target_type": "DOCUMENT", "target_reference": doc.id}]
        })
        assert hold_resp.status_code == 201
        hold_id = hold_resp.json()["id"]

        # Age the lifecycle record further past deletion threshold (800 days)
        lifecycle_rec.created_at = now - timedelta(days=800)
        db.commit()

        # Run evaluation -> legal hold must FREEZE and BLOCK deletion transition
        eval_resp2 = client.post("/api/v3/governance/lifecycle/evaluate", json={"dry_run": False})
        assert eval_resp2.status_code == 200
        assert eval_resp2.json()["blocked_by_legal_hold"] >= 1

        db.refresh(lifecycle_rec)
        assert lifecycle_rec.legal_hold is True
        # Status remains untouched, NOT DELETION_ELIGIBLE
        assert lifecycle_rec.lifecycle_status == RecordLifecycleStatus.ARCHIVE_ELIGIBLE.value

        # Release the legal hold
        rel_resp = client.post(f"/api/v3/governance/legal-holds/{hold_id}/release")
        assert rel_resp.status_code == 200
        assert rel_resp.json()["status"] == LegalHoldStatus.RELEASED.value

        # Re-evaluate -> now deletion eligibility can proceed
        eval_resp3 = client.post("/api/v3/governance/lifecycle/evaluate", json={"dry_run": False})
        assert eval_resp3.status_code == 200

        db.refresh(lifecycle_rec)
        assert lifecycle_rec.legal_hold is False
        assert lifecycle_rec.lifecycle_status == RecordLifecycleStatus.DELETION_ELIGIBLE.value

    finally:
        db.close()
