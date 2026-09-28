"""
test_engagement_surveys_campaigns.py - Module 19: Survey Templates & Campaign Lifecycle Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, Person, User

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


def test_survey_template_crud_and_questions():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create survey template with questions
    t_payload = {
        "name": "Q3 Pulse Engagement Survey",
        "description": "Quarterly temperature check on team velocity and wellbeing.",
        "survey_type": "PULSE",
        "estimated_minutes": 5,
        "anonymous_by_default": True,
        "questions": [
            {
                "question_type": "RATING",
                "question_text": "I feel valued and recognized for my contributions.",
                "category": "RECOGNITION",
                "sequence": 1,
                "required": True,
                "anonymous": True,
                "scale_min": 1,
                "scale_max": 5,
            },
            {
                "question_type": "SCALE",
                "question_text": "Team psychological safety allows open discussion of challenges.",
                "category": "CULTURE",
                "sequence": 2,
                "required": True,
                "anonymous": True,
                "scale_min": 1,
                "scale_max": 5,
            }
        ]
    }
    create_resp = client.post("/api/v3/engagement/templates", json=t_payload)
    assert create_resp.status_code == 201
    tmpl_data = create_resp.json()
    tmpl_id = tmpl_data["id"]
    assert tmpl_data["name"] == "Q3 Pulse Engagement Survey"
    assert tmpl_data["status"] == "DRAFT"
    assert len(tmpl_data["questions"]) == 2

    # 2. Add an additional question via question bank endpoint
    q_payload = {
        "template_id": tmpl_id,
        "question_type": "TEXT",
        "question_text": "Any additional feedback for leadership?",
        "category": "GENERAL",
        "sequence": 3,
        "required": False,
        "anonymous": True,
    }
    q_resp = client.post("/api/v3/engagement/questions", json=q_payload)
    assert q_resp.status_code == 201
    q_data = q_resp.json()
    assert q_data["question_text"] == "Any additional feedback for leadership?"

    # 3. Read template
    get_resp = client.get(f"/api/v3/engagement/templates/{tmpl_id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["questions"]) == 3

    # 4. Publish template
    pub_resp = client.post(f"/api/v3/engagement/templates/{tmpl_id}/publish")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "PUBLISHED"


def test_survey_campaign_lifecycle_and_recipients():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create a template first
    tmpl_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Org Climate Survey 2026",
        "survey_type": "ENGAGEMENT",
        "estimated_minutes": 8,
        "anonymous_by_default": True,
        "questions": [
            {
                "question_type": "RATING",
                "question_text": "I am motivated to go beyond formal job duties.",
                "category": "ENGAGEMENT",
                "sequence": 1,
                "required": True,
                "anonymous": True,
                "scale_min": 1,
                "scale_max": 5,
            }
        ]
    })
    assert tmpl_resp.status_code == 201
    template_id = tmpl_resp.json()["id"]

    # 2. Create Campaign
    now = datetime.utcnow()
    start_at = now - timedelta(hours=1)
    end_at = now + timedelta(days=14)

    camp_payload = {
        "template_id": template_id,
        "name": "Spring 2026 Company-Wide Engagement Campaign",
        "description": "Annual benchmark engagement survey for all personnel.",
        "audience_type": "ALL_EMPLOYEES",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "anonymous": True,
        "minimum_anonymity_threshold": 5,
        "visibility_type": "ANONYMOUS",
    }
    camp_resp = client.post("/api/v3/engagement/campaigns", json=camp_payload)
    assert camp_resp.status_code == 201
    camp_data = camp_resp.json()
    campaign_id = camp_data["id"]
    assert camp_data["status"] == "DRAFT"

    # 3. Publish Campaign -> Distributes invitations
    pub_resp = client.post(f"/api/v3/engagement/campaigns/{campaign_id}/publish")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "ACTIVE"

    # 4. Check recipient list (administrative view)
    recip_resp = client.get(f"/api/v3/engagement/campaigns/{campaign_id}/participation")
    assert recip_resp.status_code == 200
    recipients = recip_resp.json()
    assert len(recipients) > 0
    assert all(r["participation_status"] in ["INVITED", "STARTED", "COMPLETED"] for r in recipients)

    # 5. Close Campaign
    close_resp = client.post(f"/api/v3/engagement/campaigns/{campaign_id}/close")
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"


def test_question_bank_filtering_and_template_deletion():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create a template to delete
    tmpl_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Temporary Test Template",
        "survey_type": "CUSTOM",
        "estimated_minutes": 2,
        "questions": [
            {
                "question_type": "YES_NO",
                "question_text": "Do you have all necessary hardware for your work?",
                "category": "TOOLS",
                "sequence": 1,
            }
        ]
    })
    assert tmpl_resp.status_code == 201
    tmpl_id = tmpl_resp.json()["id"]

    # 2. Filter questions by category TOOLS
    q_resp = client.get("/api/v3/engagement/questions?category=TOOLS")
    assert q_resp.status_code == 200
    tools_qs = q_resp.json()
    assert any(q["question_text"] == "Do you have all necessary hardware for your work?" for q in tools_qs)

    # 3. Delete template
    del_resp = client.delete(f"/api/v3/engagement/templates/{tmpl_id}")
    assert del_resp.status_code == 204

    # Confirm 404
    get_del = client.get(f"/api/v3/engagement/templates/{tmpl_id}")
    assert get_del.status_code == 404
