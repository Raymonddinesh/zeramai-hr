"""
test_analytics_performance.py - Module 13 Performance & Learning Analytics Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
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


def test_performance_review_completion_analytics():
    """HR admin can fetch review completion rates and rating distributions."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_reviews" in data
    assert "completed_reviews" in data
    assert "review_completion_rate" in data
    assert "rating_distribution" in data
    assert isinstance(data["rating_distribution"], list)


def test_learning_and_training_hours_analytics():
    """HR admin can fetch LMS course completion rates and training hours."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/learning")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_courses" in data
    assert "total_enrollments" in data
    assert "completion_rate" in data
    assert "training_hours" in data
    assert "mandatory_training_compliance_rate" in data


def test_manager_scoped_performance_analytics():
    """Hiring manager can access performance analytics scoped to team reports."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert "review_completion_rate" in data
