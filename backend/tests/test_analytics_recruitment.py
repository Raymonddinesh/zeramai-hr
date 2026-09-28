"""
test_analytics_recruitment.py - Module 13 ATS & Recruitment Analytics Tests.
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


def test_recruitment_funnel_and_conversion_rates():
    """HR admin can fetch recruitment funnel stages and conversion metrics."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/recruitment")
    assert resp.status_code == 200
    data = resp.json()
    assert "open_positions" in data
    assert "total_candidates" in data
    assert "screening_rate" in data
    assert "interview_rate" in data
    assert "offer_acceptance_rate" in data
    assert "funnel" in data
    assert len(data["funnel"]) == 5


def test_recruitment_time_to_hire_metrics():
    """HR admin can view average time-to-hire and time-to-fill metrics."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/recruitment")
    assert resp.status_code == 200
    data = resp.json()
    assert "average_time_to_hire_days" in data
    assert "average_time_to_fill_days" in data
    assert data["average_time_to_hire_days"] > 0


def test_employee_forbidden_from_recruitment_analytics():
    """Regular employee is rejected with 403 when requesting recruitment analytics."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/recruitment")
    assert resp.status_code == 403
