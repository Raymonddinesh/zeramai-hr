"""
Module 12: Compliance Calendar Events and Due Dates Tests.
"""
import os
import pytest
from datetime import date, timedelta
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


_shared: dict = {}


def test_calendar_create_and_list_events(seed_data):
    """Create a compliance calendar event and list events."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    due = date.today() + timedelta(days=15)
    resp = client.post("/api/v3/compliance-calendar", json={
        "compliance_type": "statutory",
        "authority": "EPFO",
        "title": "EPF ECR Filing Due Date",
        "description": "Monthly ECR filing deadline for previous month wage period",
        "period": "2026-10",
        "due_date": str(due),
        "priority": 3,
    })
    assert resp.status_code == 201, f"Create event failed: {resp.text}"
    evt = resp.json()
    assert evt["title"] == "EPF ECR Filing Due Date"
    evt_id = evt["id"]
    _shared["evt_id"] = evt_id

    # List events
    list_resp = client.get("/api/v3/compliance-calendar")
    assert list_resp.status_code == 200
    ids = [e["id"] for e in list_resp.json()]
    assert evt_id in ids


def test_calendar_update_event(seed_data):
    """Update event status to completed."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    evt_id = _shared["evt_id"]
    resp = client.patch(f"/api/v3/compliance-calendar/{evt_id}", json={
        "status": "completed",
    })
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["status"] == "completed"
    assert updated["completed_at"] is not None


def test_calendar_filtering(seed_data):
    """Filter calendar events by compliance type."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/compliance-calendar?compliance_type=statutory")
    assert resp.status_code == 200
    for e in resp.json():
        assert e["compliance_type"] == "statutory"
