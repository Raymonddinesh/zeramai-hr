"""
test_analytics_attendance.py - Module 13 Attendance & Leave Analytics Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com", "ChangeMe123!"),
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


def test_attendance_analytics_metrics():
    """HR admin can fetch attendance rate and working hours."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/attendance")
    assert resp.status_code == 200
    data = resp.json()
    assert "attendance_rate" in data
    assert "absence_rate" in data
    assert "late_arrivals" in data
    assert "working_hours" in data
    assert "overtime_hours" in data


def test_leave_analytics_and_utilization():
    """HR admin can fetch leave utilization metrics and request status breakdowns."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/leave")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert "approved_requests" in data
    assert "leave_utilization_rate" in data
    assert "by_type" in data
    assert isinstance(data["by_type"], list)


def test_manager_scoped_attendance_analytics():
    """Hiring manager can view attendance analytics scoped to their team."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/attendance")
    assert resp.status_code == 200
    data = resp.json()
    assert "attendance_rate" in data
