"""
test_engagement_recognition_culture.py - Module 19: Recognition, Awards & Culture Initiative Tests
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


def get_person_ids():
    db = SessionLocal()
    try:
        emp = db.query(Person).filter(Person.email == "employee@example.com").first()
        mgr = db.query(Person).filter(Person.email == "manager@zeramai.com").first()
        return emp.id, mgr.id
    finally:
        db.close()


def test_recognition_award_and_anti_self_recognition():
    emp_id, mgr_id = get_person_ids()

    # 1. HR Admin creates a recognition program
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    prog_resp = client.post("/api/v3/engagement/recognition/programs", json={
        "name": "Spotlight Peer Kudos",
        "description": "Celebrating daily wins, mentorship, and cross-team collaboration.",
        "recognition_type": "PEER",
        "points_reward": 25,
    })
    assert prog_resp.status_code == 201
    program_id = prog_resp.json()["id"]

    # 2. Employee sends recognition to Manager
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    award_resp = client.post("/api/v3/engagement/recognition/awards", json={
        "program_id": program_id,
        "recipient_person_id": mgr_id,
        "title": "Outstanding Mentorship on Architecture Migration",
        "message": "Thank you for the guidance during the service isolation refactoring!",
        "category": "VALUES",
        "visibility": "PUBLIC",
    })
    assert award_resp.status_code == 201
    award_data = award_resp.json()
    assert award_data["giver_person_id"] == emp_id
    assert award_data["recipient_person_id"] == mgr_id

    # 3. SELF-RECOGNITION PREVENTION INVARIANT:
    # Attempting to give recognition to oneself MUST return HTTP 400
    self_resp = client.post("/api/v3/engagement/recognition/awards", json={
        "program_id": program_id,
        "recipient_person_id": emp_id,  # Giver is employee, recipient is employee
        "title": "Self Praise",
        "message": "I did a great job today!",
    })
    assert self_resp.status_code == 400
    assert "self-recognition is not permitted" in self_resp.json()["detail"].lower()


def test_award_nomination_lifecycle():
    emp_id, mgr_id = get_person_ids()

    # 1. HR Admin creates Award Definition
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    award_def_resp = client.post("/api/v3/engagement/awards", json={
        "name": "Innovator of the Year 2026",
        "description": "Honoring exceptional product and architectural innovation.",
        "criteria": "Patent contributions, design excellence, or major platform performance gains.",
        "frequency": "ANNUAL",
        "active": True,
    })
    assert award_def_resp.status_code == 201
    award_def_id = award_def_resp.json()["id"]

    # 2. Manager nominates Employee
    mgr_token = login(*CREDENTIALS["MANAGER"])
    set_auth(mgr_token)

    nom_resp = client.post("/api/v3/engagement/awards/nominations", json={
        "award_definition_id": award_def_id,
        "nominee_person_id": emp_id,
        "justification": "Delivered high-performance async queue system reducing latency by 45%.",
    })
    assert nom_resp.status_code == 201
    nom_data = nom_resp.json()
    nom_id = nom_data["id"]
    assert nom_data["status"] == "NOMINATED"

    # Self-nomination check: Employee nominating self returns HTTP 400
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)
    self_nom_resp = client.post("/api/v3/engagement/awards/nominations", json={
        "award_definition_id": award_def_id,
        "nominee_person_id": emp_id,
        "justification": "I should win because I worked hard.",
    })
    assert self_nom_resp.status_code == 400

    # 3. HR Admin reviews and approves nomination
    set_auth(hr_token)
    rev_resp = client.put(f"/api/v3/engagement/awards/nominations/{nom_id}/review", json={
        "status": "APPROVED",
        "review_comments": "Endorsed by executive committee.",
    })
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "APPROVED"


def test_culture_initiative_lifecycle_and_duplicate_prevention():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "hr@zeramai.com").first()
    admin_user_id = admin_user.id
    db.close()

    # 1. Create Culture Initiative
    init_resp = client.post("/api/v3/engagement/culture/initiatives", json={
        "name": "Zeramai Hackathon & Social Good Sprint",
        "description": "48-hour open hackathon building community-driven open-source tooling.",
        "category": "INNOVATION",
        "owner_user_id": admin_user_id,
        "start_date": (date.today() + timedelta(days=20)).isoformat(),
        "end_date": (date.today() + timedelta(days=22)).isoformat(),
        "target_participants": 100,
    })
    assert init_resp.status_code == 201
    init_data = init_resp.json()
    init_id = init_data["id"]
    assert init_data["status"] == "ACTIVE"

    # 2. Employee joins initiative
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    join_resp = client.post(f"/api/v3/engagement/culture/initiatives/{init_id}/participation", json={
        "initiative_id": init_id,
        "participation_type": "HACKER",
        "feedback": "Excited to join the accessibility tools track!",
    })
    assert join_resp.status_code == 201
    join_data = join_resp.json()
    assert join_data["participation_type"] == "HACKER"

    # 3. DUPLICATE PARTICIPATION PREVENTION INVARIANT:
    # Joining a second time must return HTTP 400
    dup_resp = client.post(f"/api/v3/engagement/culture/initiatives/{init_id}/participation", json={
        "initiative_id": init_id,
        "participation_type": "HACKER",
    })
    assert dup_resp.status_code == 400
    assert "duplicate participation not permitted" in dup_resp.json()["detail"].lower()
