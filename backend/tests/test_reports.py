"""
test_reports.py - Module 13 Report Builder, Execution & Export Tests.
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


def test_report_definition_crud_and_execution():
    """HR admin can create, read, update, execute, and export custom reports."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create report definition
    payload = {
        "name": "Q3 Headcount & Department Distribution",
        "description": "Quarterly headcount report by department",
        "report_type": "WORKFORCE",
        "metrics": ["total_employees", "active_employees", "exits"],
        "dimensions": ["department"],
        "visibility": "PUBLIC",
        "min_aggregation_threshold": 3,
    }
    resp = client.post("/api/v3/reports", json=payload)
    assert resp.status_code == 201
    report_data = resp.json()
    report_id = report_data["id"]
    assert report_data["name"] == payload["name"]

    # 2. Get report definition
    get_resp = client.get(f"/api/v3/reports/{report_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == report_id

    # 3. Update report definition
    patch_resp = client.patch(f"/api/v3/reports/{report_id}", json={"description": "Updated quarterly description"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["description"] == "Updated quarterly description"

    # 4. Execute report
    exec_resp = client.post(f"/api/v3/reports/{report_id}/execute", json={})
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["report_definition_id"] == report_id
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["row_count"] >= 1
    assert "execution_time_ms" in exec_data

    # 5. Export report as CSV
    export_resp = client.post(f"/api/v3/reports/{report_id}/export?format=CSV")
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers.get("content-type", "")
    assert "Total Employees" in export_resp.text

    # 6. Delete report definition
    del_resp = client.delete(f"/api/v3/reports/{report_id}")
    assert del_resp.status_code == 204
