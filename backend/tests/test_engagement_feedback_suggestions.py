"""
test_engagement_feedback_suggestions.py - Module 19: Feedback, Suggestions & Action Plans Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, Person, User

client = TestClient(app)

CREDENTIALS = {
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


def test_employee_feedback_and_grievance_referral():
    # 1. Employee submits constructive feedback
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    fb_resp = client.post("/api/v3/engagement/feedback", json={
        "category": "WORKPLACE",
        "subject": "Hybrid Workspace Acoustic Booths",
        "message": "The open plan floor has high echo. Additional soundproof phone booths would improve focus.",
        "visibility": "PRIVATE_HR",
    })
    assert fb_resp.status_code == 201
    fb_data = fb_resp.json()
    fb_id = fb_data["id"]
    assert fb_data["status"] == "SUBMITTED"
    assert fb_data["is_grievance_referral"] is False

    # 2. HR Admin reviews feedback and updates status
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    update_resp = client.put(f"/api/v3/engagement/feedback/{fb_id}", json={
        "status": "UNDER_REVIEW",
        "admin_notes": "Facilities team has received the request for acoustic pods.",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "UNDER_REVIEW"

    # 3. If feedback is deemed formal grievance, refer to existing ER system
    ref_resp = client.post(f"/api/v3/engagement/feedback/{fb_id}/refer-grievance?er_case_id=er-case-demo-123")
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert ref_data["is_grievance_referral"] is True
    assert ref_data["er_case_id"] == "er-case-demo-123"
    assert ref_data["status"] == "ACTIONED"


def test_anonymous_suggestion_and_voting():
    # 1. Employee submits an anonymous suggestion
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    sugg_resp = client.post("/api/v3/engagement/suggestions", json={
        "category": "WELLBEING",
        "title": "Wellness Wednesdays Meeting-Free Afternoons",
        "description": "Dedicate Wednesday afternoons to deep work without internal status meetings.",
        "anonymous": True,
    })
    assert sugg_resp.status_code == 201
    sugg_data = sugg_resp.json()
    sugg_id = sugg_data["id"]
    assert sugg_data["anonymous"] is True
    # Privacy check: person_id must be None
    assert sugg_data["person_id"] is None
    assert sugg_data["person_name"] == "Anonymous Employee"

    # 2. Upvote suggestion
    vote_resp = client.post(f"/api/v3/engagement/suggestions/{sugg_id}/vote")
    assert vote_resp.status_code == 200
    assert vote_resp.json()["votes_count"] == 1

    # 3. HR Admin reviews and accepts suggestion
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    rev_resp = client.put(f"/api/v3/engagement/suggestions/{sugg_id}", json={
        "status": "ACCEPTED",
        "admin_notes": "Approved by Leadership Committee for trial starting next sprint.",
    })
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "ACCEPTED"


def test_engagement_action_plans_and_items():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Fetch admin user id
    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "hr@zeramai.com").first()
    admin_user_id = admin_user.id
    db.close()

    # 1. Create Action Plan with items
    plan_resp = client.post("/api/v3/engagement/action-plans", json={
        "title": "Engineering Communication & Transparency Action Plan",
        "description": "Remediation actions derived from Spring 2026 Pulse Survey results.",
        "owner_user_id": admin_user_id,
        "due_date": (date.today() + timedelta(days=60)).isoformat(),
        "items": [
            {
                "action": "Host bi-weekly engineering AMA with VP of Engineering",
                "owner_user_id": admin_user_id,
                "due_date": (date.today() + timedelta(days=14)).isoformat(),
            },
            {
                "action": "Publish open roadmap and architecture decision logs",
                "owner_user_id": admin_user_id,
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
            }
        ]
    })
    assert plan_resp.status_code == 201
    plan_data = plan_resp.json()
    plan_id = plan_data["id"]
    assert plan_data["status"] == "OPEN"
    assert len(plan_data["items"]) == 2
    item_id = plan_data["items"][0]["id"]

    # 2. Update Action Item to COMPLETED
    item_resp = client.put(f"/api/v3/engagement/action-plans/{plan_id}/items/{item_id}", json={
        "status": "COMPLETED",
        "notes": "First session concluded with 88% positive attendee feedback.",
    })
    assert item_resp.status_code == 200
    assert item_resp.json()["status"] == "COMPLETED"
    assert item_resp.json()["completed_at"] is not None


def test_feedback_privacy_and_unauthorized_isolation():
    # 1. Employee submits private HR feedback
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    fb_resp = client.post("/api/v3/engagement/feedback", json={
        "category": "MANAGEMENT",
        "subject": "Confidential Compensation Query",
        "message": "Inquiring about market compensation adjustment timeline.",
        "visibility": "PRIVATE_HR",
    })
    assert fb_resp.status_code == 201
    fb_id = fb_resp.json()["id"]

    # 2. Another user (e.g. manager who is not HR admin and not author) tries to view private HR feedback
    mgr_token = login("manager@zeramai.com", "ChangeMe123!")
    set_auth(mgr_token)

    unauth_resp = client.get(f"/api/v3/engagement/feedback/{fb_id}")
    assert unauth_resp.status_code == 403
