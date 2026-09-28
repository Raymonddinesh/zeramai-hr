"""
test_analytics_compensation.py - Module 13 Compensation & Workforce Cost Analytics Tests.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
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


def test_compensation_analytics_for_hr_and_finance():
    """HR and Finance can view compensation totals and distribution."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/compensation?min_threshold=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_redacted" in data
    assert "salary_distribution" in data
    assert isinstance(data["salary_distribution"], list)


def test_compensation_privacy_redaction_below_threshold():
    """When population is below the privacy threshold, sensitive values are redacted."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/compensation?min_threshold=9999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_redacted"] is True
    assert data["total_payroll_cost"] is None
    assert "redaction_reason" in data
    assert "below privacy aggregation threshold" in data["redaction_reason"]


def test_payroll_and_workforce_cost_breakdown():
    """Finance user can query payroll totals and workforce cost structure."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/workforce-cost")
    assert resp.status_code == 200
    data = resp.json()
    assert "employee_compensation" in data
    assert "employer_statutory_cost" in data
    assert "benefits_cost" in data
    assert "total_workforce_cost" in data
    assert data["total_workforce_cost"] >= data["employee_compensation"]


def test_employee_cannot_view_compensation_analytics():
    """Regular employee is denied access to company-wide compensation analytics."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/compensation")
    assert resp.status_code == 403
