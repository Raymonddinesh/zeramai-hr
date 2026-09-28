"""
test_analytics_compliance.py - Module 13 Compliance Analytics & Executive Dashboard Tests.
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


def test_compliance_analytics_health_score():
    """HR admin can view statutory compliance health and task counts."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/compliance")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks" in data
    assert "completed_tasks" in data
    assert "overdue_tasks" in data
    assert "compliance_score_percent" in data


def test_statutory_filings_and_payments_status_counts():
    """Finance user can query compliance filing and payment status breakdowns."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/compliance")
    assert resp.status_code == 200
    data = resp.json()
    assert "statutory_filings_by_status" in data
    assert "statutory_payments_by_status" in data
    assert "tax_declarations_completion_percent" in data


def test_executive_dashboard_unification():
    """Executive dashboard unifies all functional analytics into a single response."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "headcount" in data
    assert "attrition" in data
    assert "attendance" in data
    assert "leave" in data
    assert "recruitment" in data
    assert "workforce_cost" in data
    assert "compliance" in data
    assert "pending_hr_tasks_count" in data
