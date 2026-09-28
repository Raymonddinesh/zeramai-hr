"""
test_learning_career_mentoring.py - Module 18: Career Frameworks, Opportunities, Mentoring & Skill Evidence
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Person

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("admin@example.com", "ChangeMe123!"),
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


def get_demo_persons() -> tuple[str, str]:
    db = SessionLocal()
    try:
        persons = db.query(Person).limit(2).all()
        assert len(persons) >= 2
        return persons[0].id, persons[1].id
    finally:
        db.close()


def test_career_framework_and_opportunities():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)

    # 1. Create Career Framework
    cf_resp = client.post("/api/v3/learning/career-frameworks", json={
        "name": "Product Management Competency Framework",
        "job_family": "Product",
        "description": "Standardized progression for Associate to Director of Product.",
        "levels": [
            {"code": "PM-1", "name": "Associate Product Manager", "sequence": 1},
            {"code": "PM-2", "name": "Product Manager", "sequence": 2},
            {"code": "PM-3", "name": "Senior Product Manager", "sequence": 3},
        ]
    })
    assert cf_resp.status_code == 201
    framework = cf_resp.json()
    fw_id = framework["id"]
    assert len(framework["levels"]) == 3
    lvl1_id = framework["levels"][0]["id"]
    lvl2_id = framework["levels"][1]["id"]

    # 2. Add Career Progression Path
    path_resp = client.post(f"/api/v3/learning/career-frameworks/{fw_id}/paths", json={
        "from_level_id": lvl1_id,
        "to_level_id": lvl2_id,
        "typical_requirements": "Demonstrated ownership of 2 major feature launches and cross-functional leadership.",
    })
    assert path_resp.status_code == 201
    assert path_resp.json()["from_level_id"] == lvl1_id

    # 3. Create Internal Career Opportunity
    opp_resp = client.post("/api/v3/learning/career-opportunities", json={
        "title": "Senior Technical Product Manager - Platform Systems",
        "description": "Lead the core platform infrastructure and developer productivity initiatives.",
        "required_skills": "API Design, Distributed Systems, Roadmapping",
        "required_level": "PM-3",
        "application_deadline": str(date.today() + timedelta(days=45)),
    })
    assert opp_resp.status_code == 201
    opp = opp_resp.json()
    opp_id = opp["id"]

    # 4. Employee Applies for Career Opportunity
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    app_resp = client.post("/api/v3/learning/career-applications", json={
        "opportunity_id": opp_id
    })
    assert app_resp.status_code == 201
    application = app_resp.json()
    assert application["opportunity_id"] == opp_id
    assert application["status"] == "SUBMITTED"

    # Duplicate application check -> Expect HTTP 400
    app_dup = client.post("/api/v3/learning/career-applications", json={
        "opportunity_id": opp_id
    })
    assert app_dup.status_code == 400


def test_mentoring_and_self_assignment_prevention():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    mentor_id, mentee_id = get_demo_persons()

    # 1. Create Mentoring Program
    prog_resp = client.post("/api/v3/learning/mentoring/programs", json={
        "name": "Women in Tech Mentorship Cohort 2026",
        "description": "Structured 6-month career development and sponsorship program.",
        "duration_months": 6,
    })
    assert prog_resp.status_code == 201
    program = prog_resp.json()
    program_id = program["id"]

    # 2. Self-Mentoring Prevention Rule: mentor_id == mentee_id MUST FAIL with HTTP 400
    self_resp = client.post("/api/v3/learning/mentoring/relationships", json={
        "program_id": program_id,
        "mentor_person_id": mentor_id,
        "mentee_person_id": mentor_id,  # SAME PERSON!
        "start_date": str(date.today()),
        "goals": "Invalid self-mentoring",
    })
    assert self_resp.status_code == 400
    assert "self-mentoring" in self_resp.json()["detail"].lower()

    # 3. Create Valid Mentoring Relationship (mentor != mentee)
    valid_resp = client.post("/api/v3/learning/mentoring/relationships", json={
        "program_id": program_id,
        "mentor_person_id": mentor_id,
        "mentee_person_id": mentee_id,
        "start_date": str(date.today()),
        "goals": "Develop technical leadership and executive presentation skills.",
    })
    assert valid_resp.status_code == 201
    rel = valid_resp.json()
    assert rel["status"] == "ACTIVE"

    # 4. Duplicate Active Relationship in Same Program MUST FAIL with HTTP 400
    dup_rel = client.post("/api/v3/learning/mentoring/relationships", json={
        "program_id": program_id,
        "mentor_person_id": mentor_id,
        "mentee_person_id": mentee_id,
        "start_date": str(date.today()),
    })
    assert dup_rel.status_code == 400


def test_skill_remediation_and_evidence_verification():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    person_id, _ = get_demo_persons()

    # Fetch or create skill from Module 17
    skills_resp = client.get("/api/v3/workforce-planning/skills")
    assert skills_resp.status_code == 200
    skills = skills_resp.json()
    skill_id = skills[0]["id"] if skills else client.post("/api/v3/workforce-planning/skills", json={
        "code": "SKILL-DOCKER",
        "name": "Docker & Containers",
        "category": "TECHNICAL"
    }).json()["id"]

    # 1. Create Skill Development Remediation Action
    act_resp = client.post("/api/v3/learning/skill-development-actions", json={
        "person_id": person_id,
        "skill_id": skill_id,
        "skill_gap_reference": "GAP-Q2-2026",
        "action_type": "PROJECT",
        "due_date": str(date.today() + timedelta(days=60)),
    })
    assert act_resp.status_code == 201
    action = act_resp.json()
    assert action["action_type"] == "PROJECT"
    assert action["status"] == "PLANNED"

    # 2. Record Skill Evidence (Unverified)
    ev_resp = client.post("/api/v3/learning/skill-evidence", json={
        "person_id": person_id,
        "skill_id": skill_id,
        "evidence_type": "PROJECT",
        "source_reference": "PR-9421 Containerized Core Gateway",
        "evidence_date": str(date.today()),
        "notes": "Engineered multi-stage production Docker build reducing image size by 65%.",
    })
    assert ev_resp.status_code == 201
    evidence = ev_resp.json()
    evidence_id = evidence["id"]
    assert evidence["verified"] is False

    # 3. Manager/Admin Verifies Skill Evidence -> Triggers Controlled Skill Progression
    ver_resp = client.post(f"/api/v3/learning/skill-evidence/{evidence_id}/verify")
    assert ver_resp.status_code == 200
    verified = ver_resp.json()
    assert verified["verified"] is True
    assert verified["verified_by"] is not None


def test_individual_development_plan_and_goals():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    person_id, _ = get_demo_persons()

    # 1. Create IDP
    idp_resp = client.post("/api/v3/learning/development-plans", json={
        "person_id": person_id,
        "current_role": "Senior Cloud Engineer",
        "target_role": "Lead Architect",
        "career_direction": "Systems Architecture",
        "review_period": "FY2027",
        "employee_notes": "Focused on enterprise security and multi-region resilience.",
        "goals": [
            {
                "title": "Publish Multi-Region Disaster Recovery Blueprint",
                "description": "Deliver cross-cloud failover design and automation runbooks.",
                "due_date": str(date.today() + timedelta(days=90)),
            }
        ]
    })
    assert idp_resp.status_code == 201
    idp = idp_resp.json()
    assert idp["status"] == "ACTIVE"
    assert len(idp["goals"]) == 1

    # 2. Add another goal to plan
    g_resp = client.post(f"/api/v3/learning/development-goals?plan_id={idp['id']}", json={
        "title": "Complete SOC2 Compliance Readiness Assessment",
        "description": "Align platform security controls with AICPA trust criteria.",
        "due_date": str(date.today() + timedelta(days=120)),
    })
    assert g_resp.status_code == 201
    assert g_resp.json()["title"] == "Complete SOC2 Compliance Readiness Assessment"

