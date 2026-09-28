"""
test_scheduled_reports.py - Module 13 Scheduled Reports Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
}


def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.cookies.get("access_token") or resp.json().get("access_token")
    assert token, f"No token for {email}"
    return token


def set_auth(token: str):
    client.cookies.set("access_token", token)


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


def test_scheduled_report_lifecycle():
    """HR admin can configure and manage recurring scheduled reports."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create a base report definition
    rep_resp = client.post("/api/v3/reports", json={
        "name": "Monthly Compliance & Task Status",
        "report_type": "COMPLIANCE",
        "visibility": "PUBLIC",
    })
    assert rep_resp.status_code == 201
    report_id = rep_resp.json()["id"]

    # 2. Schedule the report
    sched_payload = {
        "report_definition_id": report_id,
        "frequency": "MONTHLY",
        "recipients": ["compliance_officer@zeramai.com", "hr_head@zeramai.com"],
        "format": "CSV",
        "status": "ACTIVE",
    }
    sched_resp = client.post("/api/v3/reports/scheduled", json=sched_payload)
    assert sched_resp.status_code == 201
    sched_data = sched_resp.json()
    sched_id = sched_data["id"]
    assert sched_data["frequency"] == "MONTHLY"
    assert len(sched_data["recipients"]) == 2

    # 3. List scheduled reports
    list_resp = client.get("/api/v3/reports/scheduled")
    assert list_resp.status_code == 200
    ids = [s["id"] for s in list_resp.json()]
    assert sched_id in ids

    # 4. Update scheduled report
    patch_resp = client.patch(f"/api/v3/reports/scheduled/{sched_id}", json={"status": "PAUSED"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "PAUSED"

    # Cleanup
    client.delete(f"/api/v3/reports/{report_id}")
