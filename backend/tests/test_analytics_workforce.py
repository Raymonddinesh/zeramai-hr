"""
test_analytics_workforce.py - Module 13 Workforce & Headcount Analytics Tests.
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


@pytest.fixture(scope="module", autouse=True)
def setup_seed():
    os.system("python -m app.seed_rbac")
    os.system("python -m app.seed")
    yield


def test_headcount_analytics_totals_and_breakdowns():
    """HR admin can fetch organizational headcount and breakdowns."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/headcount")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_employees" in data
    assert "active_employees" in data
    assert "inactive_employees" in data
    assert "new_hires" in data
    assert "exits" in data
    assert data["total_employees"] >= 1
    assert data["active_employees"] >= 1
    assert isinstance(data["by_department"], list)
    assert isinstance(data["by_legal_entity"], list)
    assert isinstance(data["by_location"], list)
    assert isinstance(data["by_employment_type"], list)
    assert isinstance(data["trend"], list)


def test_attrition_analytics_and_tenure_bands():
    """HR admin can retrieve attrition metrics and tenure band distributions."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/attrition")
    assert resp.status_code == 200
    data = resp.json()
    assert "exits" in data
    assert "voluntary_exits" in data
    assert "involuntary_exits" in data
    assert "turnover_rate" in data
    assert "resignation_rate" in data
    assert "average_tenure_months" in data
    assert isinstance(data["by_tenure_band"], list)
    assert len(data["by_tenure_band"]) >= 1


def test_headcount_filter_by_department():
    """Headcount can be filtered by specific department."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.get("/api/v3/analytics/headcount?department=Engineering")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_employees" in data
    assert "active_employees" in data
