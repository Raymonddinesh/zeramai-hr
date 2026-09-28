"""
test_governance_bcp_dr.py - Module 15: Backup Policies, DR Drills, BCP Resilience & Data Residency.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

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
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed_rbac import main as run_rbac
    from app.seed import run as run_seed
    run_rbac()
    run_seed()
    yield


def test_backup_policy_and_execution():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create backup policy
    bp_resp = client.post("/api/v3/governance/backup-policies", json={
        "name": "Hourly Incremental Snapshot Policy",
        "frequency": "HOURLY",
        "retention_days": 14,
        "encryption_required": True,
        "offsite_required": True,
        "cross_region_required": True,
        "enabled": True,
    })
    assert bp_resp.status_code == 201
    policy_id = bp_resp.json()["id"]

    # 2. Record a verified backup execution
    exec_resp = client.post(f"/api/v3/governance/backup-executions?policy_id={policy_id}", json={
        "backup_reference": "snap-20260928-001",
        "size_bytes": 104857600,
        "checksum": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "region": "IN-SOUTH",
        "status": "COMPLETED",
    })
    assert exec_resp.status_code == 201
    exec_data = exec_resp.json()
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["encryption_status"] == "ENCRYPTED_AES256"
    assert exec_data["verification_status"] == "VERIFIED"

    # 3. List executions
    list_resp = client.get(f"/api/v3/governance/backup-executions?policy_id={policy_id}")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_dr_policy_and_drill_simulation():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create DR policy
    dr_resp = client.post("/api/v3/governance/dr-policies", json={
        "name": "Critical Payroll DR Plan",
        "rpo_minutes": 15,
        "rto_minutes": 60,
        "primary_region": "IN-SOUTH",
        "recovery_region": "IN-WEST",
        "priority": "MISSION_CRITICAL",
        "enabled": True,
    })
    assert dr_resp.status_code == 201
    policy_id = dr_resp.json()["id"]

    # 2. Record drill simulation test
    test_resp = client.post(f"/api/v3/governance/dr-tests?policy_id={policy_id}", json={
        "test_type": "FAILOVER_SIMULATION",
        "status": "PASSED",
        "actual_rpo_minutes": 12,
        "actual_rto_minutes": 45,
        "findings": "Failover completed well within 60-minute statutory threshold.",
        "corrective_actions": "None required.",
    })
    assert test_resp.status_code == 201
    data = test_resp.json()
    assert data["status"] == "PASSED"
    assert data["actual_rpo_minutes"] <= 15
    assert data["actual_rto_minutes"] <= 60


def test_business_continuity_plan_lifecycle():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create BCP with sequential action steps
    bcp_resp = client.post("/api/v3/governance/bcp", json={
        "name": "Statutory Monthly Wage Disbursement Continuity",
        "description": "Contingency plan in case of banking API gateway outage",
        "criticality": "CRITICAL",
        "recovery_strategy": "Switch to secondary offline batch NACH files via sponsor bank SFTP",
        "status": "ACTIVE",
        "actions": [
            {"sequence": 1, "action": "Notify Finance Ops Lead & Treasury", "status": "PENDING"},
            {"sequence": 2, "action": "Generate encrypted NACH XML batch", "status": "PENDING"},
            {"sequence": 3, "action": "Upload to secondary bank SFTP endpoint", "status": "PENDING"},
        ]
    })
    assert bcp_resp.status_code == 201
    plan_data = bcp_resp.json()
    plan_id = plan_data["id"]
    assert len(plan_data["actions"]) == 3
    action1_id = plan_data["actions"][0]["id"]

    # 2. Update step status
    act_resp = client.patch(f"/api/v3/governance/bcp/actions/{action1_id}", json={
        "status": "COMPLETED"
    })
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "COMPLETED"
    assert act_resp.json()["completed_at"] is not None


def test_data_residency_policy_and_dashboard_metrics():
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create Residency Policy
    res_resp = client.post("/api/v3/governance/residency-policies", json={
        "data_category": "BIOMETRIC_ATTENDANCE",
        "allowed_regions": ["IN-CENTRAL", "IN-SOUTH"],
        "primary_region": "IN-CENTRAL",
        "cross_border_transfer_allowed": False,
        "transfer_basis": "India DPDP Act 2023 - Strict Sovereign Biometric Data Protection",
        "enabled": True,
    })
    assert res_resp.status_code == 201
    assert res_resp.json()["cross_border_transfer_allowed"] is False

    # 2. Query Dashboard Metrics
    dash_resp = client.get("/api/v3/governance/dashboard")
    assert dash_resp.status_code == 200
    metrics = dash_resp.json()
    assert metrics["classifications_count"] >= 5
    assert metrics["retention_policies_count"] >= 1
    assert metrics["backup_status"] in ("HEALTHY", "WARNING")
    assert metrics["dr_readiness_status"] in ("READY", "ATTENTION_REQUIRED")
