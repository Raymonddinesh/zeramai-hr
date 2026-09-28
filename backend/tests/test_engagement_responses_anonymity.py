"""
test_engagement_responses_anonymity.py - Module 19: Survey Submission, Anonymity Separation & Threshold Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, Person, User
from app.models_engagement import (
    SurveyCampaign,
    SurveyRecipient,
    SurveyResponse,
    SurveyAnswer,
    SurveyCampaignStatus,
    ParticipationStatus,
)

client = TestClient(app)

CREDENTIALS = {
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
    "MANAGER": ("manager@zeramai.com", "ChangeMe123!"),
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


def test_anonymous_survey_response_submission_and_separation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create a survey template and active anonymous campaign
    tmpl_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Anonymous Pulse Test",
        "survey_type": "PULSE",
        "estimated_minutes": 3,
        "anonymous_by_default": True,
        "questions": [
            {
                "question_type": "RATING",
                "question_text": "I feel supported by my immediate leadership.",
                "category": "MANAGEMENT",
                "sequence": 1,
                "required": True,
                "anonymous": True,
                "scale_min": 1,
                "scale_max": 5,
            },
            {
                "question_type": "NPS",
                "question_text": "How likely are you to recommend Zeramai to friends?",
                "category": "CULTURE",
                "sequence": 2,
                "required": True,
                "anonymous": True,
                "scale_min": 0,
                "scale_max": 10,
            }
        ]
    })
    assert tmpl_resp.status_code == 201
    tmpl = tmpl_resp.json()
    template_id = tmpl["id"]
    q1_id = tmpl["questions"][0]["id"]
    q2_id = tmpl["questions"][1]["id"]

    now = datetime.utcnow()
    camp_resp = client.post("/api/v3/engagement/campaigns", json={
        "template_id": template_id,
        "name": "Live Anonymous Pulse Campaign",
        "audience_type": "ALL_EMPLOYEES",
        "start_at": (now - timedelta(hours=1)).isoformat(),
        "end_at": (now + timedelta(days=7)).isoformat(),
        "anonymous": True,
        "minimum_anonymity_threshold": 5,
        "visibility_type": "ANONYMOUS",
    })
    assert camp_resp.status_code == 201
    camp_id = camp_resp.json()["id"]

    # Publish campaign
    pub_resp = client.post(f"/api/v3/engagement/campaigns/{camp_id}/publish")
    assert pub_resp.status_code == 200

    # 2. Switch to Employee and submit response
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    sub_payload = {
        "answers": [
            {"question_id": q1_id, "answer_numeric": 5.0, "answer_text": "Great leadership"},
            {"question_id": q2_id, "answer_numeric": 10.0},
        ],
        "completion_time_seconds": 120,
    }
    sub_resp = client.post(f"/api/v3/engagement/surveys/{camp_id}/submit", json=sub_payload)
    assert sub_resp.status_code == 201
    sub_data = sub_resp.json()

    # CRITICAL PRIVACY INVARIANT: recipient_id MUST be None in response
    assert sub_data["recipient_id"] is None
    assert len(sub_data["answers"]) == 2

    # 3. Direct DB verification of anonymity separation
    db = SessionLocal()
    try:
        resp_row = db.query(SurveyResponse).filter(SurveyResponse.id == sub_data["id"]).first()
        assert resp_row is not None
        assert resp_row.recipient_id is None
        assert resp_row.anonymous_response_id is not None
        assert len(resp_row.anonymous_response_id) > 10

        # Recipient status must be completed
        emp_user = db.query(User).filter(User.email == "employee@example.com").first()
        recipient_row = db.query(SurveyRecipient).filter(
            SurveyRecipient.campaign_id == camp_id,
            SurveyRecipient.person_id == emp_user.person_id,
        ).first()
        assert recipient_row is not None
        assert recipient_row.participation_status == ParticipationStatus.COMPLETED
        assert recipient_row.completed_at is not None
    finally:
        db.close()

    # 4. Attempting to resubmit MUST be rejected with HTTP 400
    resub_resp = client.post(f"/api/v3/engagement/surveys/{camp_id}/submit", json=sub_payload)
    assert resub_resp.status_code == 400
    assert "already completed" in resub_resp.json()["detail"].lower()


def test_anonymity_threshold_enforcement_and_metric_aggregation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create a campaign with threshold = 5
    tmpl_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Threshold Benchmark Survey",
        "survey_type": "ENGAGEMENT",
        "estimated_minutes": 5,
        "anonymous_by_default": True,
        "questions": [
            {
                "question_type": "RATING",
                "question_text": "I see clear opportunities for career growth at Zeramai.",
                "category": "GROWTH",
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
    q_id = tmpl_resp.json()["questions"][0]["id"]

    now = datetime.utcnow()
    camp_resp = client.post("/api/v3/engagement/campaigns", json={
        "template_id": template_id,
        "name": "Threshold Enforcement Test Campaign",
        "audience_type": "ALL_EMPLOYEES",
        "start_at": (now - timedelta(hours=1)).isoformat(),
        "end_at": (now + timedelta(days=7)).isoformat(),
        "anonymous": True,
        "minimum_anonymity_threshold": 5,
        "visibility_type": "ANONYMOUS",
    })
    assert camp_resp.status_code == 201
    camp_id = camp_resp.json()["id"]

    pub_resp = client.post(f"/api/v3/engagement/campaigns/{camp_id}/publish")
    assert pub_resp.status_code == 200

    # 2. Before reaching threshold (e.g. only 1 response submitted)
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)
    client.post(f"/api/v3/engagement/surveys/{camp_id}/submit", json={
        "answers": [{"question_id": q_id, "answer_numeric": 4.0}],
        "completion_time_seconds": 60,
    })

    # Switch back to HR to check results
    set_auth(hr_token)
    res_below = client.get(f"/api/v3/engagement/campaigns/{camp_id}/results")
    assert res_below.status_code == 200
    data_below = res_below.json()
    assert data_below["sample_size"] == 1
    assert data_below["is_threshold_met"] is False
    assert "below the minimum anonymity threshold" in data_below["threshold_notice"]
    # Granular scores MUST BE suppressed
    assert data_below["overall_engagement_score"] is None
    assert len(data_below["category_scores"]) == 0
    assert len(data_below["question_metrics"]) == 0

    # 3. Simulate reaching threshold by adding 4 more responses directly into DB
    db = SessionLocal()
    try:
        camp = db.query(SurveyCampaign).filter(SurveyCampaign.id == camp_id).first()
        for i in range(4):
            r = SurveyResponse(
                tenant_id=camp.tenant_id,
                campaign_id=camp.id,
                recipient_id=None,
                anonymous_response_id=f"simulated-anon-{i}",
                submitted_at=datetime.utcnow(),
                completion_time_seconds=90,
            )
            db.add(r)
            db.flush()
            ans = SurveyAnswer(
                tenant_id=camp.tenant_id,
                response_id=r.id,
                question_id=q_id,
                answer_numeric=5.0 if i % 2 == 0 else 4.0,
            )
            db.add(ans)
        db.commit()
    finally:
        db.close()

    # 4. Now results check: sample_size is 5 (>= threshold 5)
    res_met = client.get(f"/api/v3/engagement/campaigns/{camp_id}/results")
    assert res_met.status_code == 200
    data_met = res_met.json()
    assert data_met["sample_size"] == 5
    assert data_met["is_threshold_met"] is True
    assert data_met["threshold_notice"] is None
    assert data_met["overall_engagement_score"] is not None
    assert data_met["overall_engagement_score"] >= 4.0
    assert len(data_met["category_scores"]) == 1
    assert data_met["category_scores"][0]["category"] == "GROWTH"
    assert len(data_met["question_metrics"]) == 1
    assert data_met["metric_labels"]["type"] == "SURVEY RESULT"
    assert data_met["metric_labels"]["aggregation"] == "AGGREGATED RESULT"


def test_non_anonymous_survey_submission_and_tracking():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create a non-anonymous survey template (e.g. Training Feedback)
    tmpl_resp = client.post("/api/v3/engagement/templates", json={
        "name": "Identified Training Feedback",
        "survey_type": "TRAINING_FEEDBACK",
        "anonymous_by_default": False,
        "questions": [
            {
                "question_type": "RATING",
                "question_text": "The workshop was relevant to my role.",
                "category": "LEARNING",
                "sequence": 1,
                "required": True,
                "anonymous": False,
                "scale_min": 1,
                "scale_max": 5,
            }
        ]
    })
    assert tmpl_resp.status_code == 201
    tmpl_id = tmpl_resp.json()["id"]
    q_id = tmpl_resp.json()["questions"][0]["id"]

    now = datetime.utcnow()
    camp_resp = client.post("/api/v3/engagement/campaigns", json={
        "template_id": tmpl_id,
        "name": "Workshop Evaluation Q3",
        "audience_type": "ALL_EMPLOYEES",
        "start_at": (now - timedelta(hours=1)).isoformat(),
        "end_at": (now + timedelta(days=7)).isoformat(),
        "anonymous": False,
        "visibility_type": "PUBLIC",
    })
    assert camp_resp.status_code == 201
    camp_id = camp_resp.json()["id"]

    pub_resp = client.post(f"/api/v3/engagement/campaigns/{camp_id}/publish")
    assert pub_resp.status_code == 200

    # 2. Employee submits response
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    sub_resp = client.post(f"/api/v3/engagement/surveys/{camp_id}/submit", json={
        "answers": [{"question_id": q_id, "answer_numeric": 5.0}],
    })
    assert sub_resp.status_code == 201
    sub_data = sub_resp.json()
    # In non-anonymous campaign, recipient_id is tracked
    assert sub_data["recipient_id"] is not None
