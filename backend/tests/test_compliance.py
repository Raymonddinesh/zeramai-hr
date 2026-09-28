"""
Module 12: Compliance Dashboard and Tasks Tests.
"""
import os
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com", "ChangeMe123!"),
    "FINANCE": ("finance@zeramai.com", "ChangeMe123!"),
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


_shared: dict = {}


def test_compliance_dashboard_summary(seed_data):
    """Compliance dashboard aggregates task counts, filings, and upcoming deadlines."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/compliance/dashboard")
    assert resp.status_code == 200, f"Dashboard failed: {resp.text}"
    data = resp.json()
    assert "upcoming_deadlines_count" in data
    assert "overdue_count" in data
    assert "pending_filings_count" in data
    assert "active_registrations_count" in data


def test_compliance_task_lifecycle(seed_data):
    """HR creates a compliance task, updates status to completed, and verifies completion timestamp."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create task
    resp = client.post("/api/v3/compliance/tasks", json={
        "compliance_type": "statutory",
        "authority": "EPFO",
        "title": "File Monthly ECR for EPF",
        "description": "Upload monthly electronic challan cum return",
        "period": "2026-10",
        "due_date": str(date.today() + timedelta(days=10)),
        "priority": 3,
    })
    assert resp.status_code == 201, f"Failed to create task: {resp.text}"
    task = resp.json()
    assert task["status"] == "open"
    task_id = task["id"]
    _shared["task_id"] = task_id

    # 2. Get task
    get_resp = client.get(f"/api/v3/compliance/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "File Monthly ECR for EPF"

    # 3. Complete task
    update_resp = client.patch(f"/api/v3/compliance/tasks/{task_id}", json={
        "status": "completed",
    })
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "completed"
    assert updated["completed_at"] is not None


def test_compliance_task_filters(seed_data):
    """Filter tasks by compliance type and status."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/compliance/tasks?compliance_type=statutory")
    assert resp.status_code == 200
    for t in resp.json():
        assert t["compliance_type"] == "statutory"

    resp_completed = client.get("/api/v3/compliance/tasks?status_filter=completed")
    assert resp_completed.status_code == 200
    for t in resp_completed.json():
        assert t["status"] == "completed"
