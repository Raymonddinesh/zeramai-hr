"""
test_communications_announcements_audience.py - Module 20: Announcements & Audience Targeting Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, User, Person, Engagement

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
}


def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    token = resp.cookies.get("access_token") or resp.json().get("access_token")
    assert token
    return token


def set_auth(token: str):
    client.cookies.set("access_token", token)


@pytest.fixture(scope="module", autouse=True)
def seed_data():
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed_rbac import main as run_rbac
    from app.seed import run as run_seed
    run_rbac()
    run_seed()
    yield


def test_announcement_crud_and_scheduling():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    future_time = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"

    # 1. Create a scheduled announcement
    payload = {
        "title": "Upcoming Enterprise System Upgrade (Downtime Notice)",
        "summary": "Scheduled maintenance on core application servers.",
        "content_reference": "Database cluster failover testing will take place on Saturday midnight.",
        "announcement_type": "IT",
        "priority": "HIGH",
        "publish_at": future_time,
        "acknowledgement_required": False,
    }
    resp = client.post("/api/v3/communications/announcements", json=payload)
    assert resp.status_code == 201, resp.text
    ann = resp.json()
    ann_id = ann["id"]
    assert ann["status"] == "SCHEDULED"

    # 2. Publish immediately
    resp_pub = client.post(f"/api/v3/communications/announcements/{ann_id}/publish")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == "PUBLISHED"

    # 3. Cancel announcement
    resp_cancel = client.post(f"/api/v3/communications/announcements/{ann_id}/cancel")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCELLED"


def test_announcement_audience_targeting_and_isolation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create announcement targeted strictly to "finance" role
    resp = client.post("/api/v3/communications/announcements", json={
        "title": "Finance FY27 Budget Submission Deadline",
        "summary": "Required filing deadline for department budget projections.",
        "content_reference": "All finance controllers must upload templates by Friday 17:00.",
        "announcement_type": "PAYROLL",
        "priority": "NORMAL",
        "publish_at": datetime.utcnow().isoformat() + "Z",
        "acknowledgement_required": False,
        "audience_rules": [
            {
                "audience_type": "ROLE",
                "role_reference": "FINANCE",
            }
        ],
    })
    assert resp.status_code == 201
    finance_ann = resp.json()

    # Publish it
    client.post(f"/api/v3/communications/announcements/{finance_ann['id']}/publish")

    # 2. Employee (role = EMPLOYEE) lists announcements
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    emp_announcements = client.get("/api/v3/communications/announcements").json()
    ann_ids = [a["id"] for a in emp_announcements]

    # Employee must NOT see the finance-targeted announcement
    assert finance_ann["id"] not in ann_ids

    # Direct access check returns 403
    resp_direct = client.get(f"/api/v3/communications/announcements/{finance_ann['id']}")
    assert resp_direct.status_code == 403


def test_critical_priority_announcement():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Create CRITICAL priority notice requiring acknowledgement
    resp = client.post("/api/v3/communications/announcements", json={
        "title": "URGENT: Evacuation Drill & Safety Preparedness Protocol",
        "summary": "Mandatory safety protocol acknowledgement for all campus personnel.",
        "content_reference": "Safety wardens will conduct fire drill testing today at 14:00.",
        "announcement_type": "SAFETY",
        "priority": "CRITICAL",
        "publish_at": datetime.utcnow().isoformat() + "Z",
        "acknowledgement_required": True,
    })
    assert resp.status_code == 201
    crit_ann = resp.json()

    # Publish
    client.post(f"/api/v3/communications/announcements/{crit_ann['id']}/publish")

    # Employee lists announcements with priority=CRITICAL filter
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    resp_crit = client.get("/api/v3/communications/announcements?priority=CRITICAL")
    assert resp_crit.status_code == 200
    crit_list = resp_crit.json()
    assert any(a["id"] == crit_ann["id"] for a in crit_list)


def test_audience_reach_preview():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Create broadcast announcement
    resp = client.post("/api/v3/communications/announcements", json={
        "title": "Townhall Preview Reach Test",
        "content_reference": "Reach preview verification.",
        "announcement_type": "GENERAL",
        "priority": "LOW",
    })
    ann_id = resp.json()["id"]

    # Preview reach
    resp_reach = client.get(f"/api/v3/communications/announcements/{ann_id}/reach")
    assert resp_reach.status_code == 200
    reach_data = resp_reach.json()
    assert reach_data["target_count"] >= 1
    assert "Estimated" in reach_data["note"]
