"""
test_learning_enrollments_progress.py - Module 18: Enrollments, Progress, Mandatory Training & Learning Plans
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


def get_demo_person_id() -> str:
    db = SessionLocal()
    try:
        p = db.query(Person).filter(Person.email == "employee@example.com").first()
        if not p:
            p = db.query(Person).first()
        return p.id
    finally:
        db.close()


def test_enrollment_lifecycle_and_idempotency():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    person_id = get_demo_person_id()

    # Create published course
    c_resp = client.post("/api/v3/learning/courses", json={
        "course_code": f"CRS-ENR-{datetime.utcnow().timestamp()}",
        "title": "Data Privacy & Enterprise Security",
        "category": "COMPLIANCE",
        "learning_type": "COURSE",
        "difficulty": "BEGINNER",
        "duration_minutes": 60,
        "delivery_mode": "ONLINE",
        "language": "en",
        "status": "PUBLISHED"
    })
    assert c_resp.status_code == 201
    course_id = c_resp.json()["id"]

    # 1. Enroll Person in Course
    enr_resp = client.post("/api/v3/learning/enrollments", json={
        "person_id": person_id,
        "course_id": course_id,
        "enrollment_type": "ASSIGNED",
    })
    assert enr_resp.status_code == 201
    enrollment = enr_resp.json()
    enrollment_id = enrollment["id"]
    assert enrollment["status"] in ("ENROLLED", "ASSIGNED")
    assert enrollment["progress_percentage"] == 0.0

    # 2. Idempotency: Duplicate enrollment request returns existing active record
    enr_dup = client.post("/api/v3/learning/enrollments", json={
        "person_id": person_id,
        "course_id": course_id,
        "enrollment_type": "ASSIGNED",
    })
    assert enr_dup.status_code in (200, 201)
    assert enr_dup.json()["id"] == enrollment_id

    # 3. Track Learning Progress: Partial (50%)
    prog_resp = client.post(f"/api/v3/learning/enrollments/{enrollment_id}/progress", json={
        "progress_percentage": 50.0,
        "time_spent_minutes": 30,
    })
    assert prog_resp.status_code == 200
    updated = prog_resp.json()
    assert updated["progress_percentage"] == 50.0
    assert updated["status"] == "IN_PROGRESS"

    # 4. Complete Learning: (100%) -> Status transitions to COMPLETED
    comp_resp = client.post(f"/api/v3/learning/enrollments/{enrollment_id}/progress", json={
        "progress_percentage": 100.0,
        "time_spent_minutes": 60,
    })
    assert comp_resp.status_code == 200
    completed = comp_resp.json()
    assert completed["progress_percentage"] == 100.0
    assert completed["status"] == "COMPLETED"


def test_mandatory_training_and_learning_plans():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    person_id = get_demo_person_id()

    # Create compliance course
    c_resp = client.post("/api/v3/learning/courses", json={
        "course_code": f"CRS-MAND-{datetime.utcnow().timestamp()}",
        "title": "Anti-Harassment & Ethics 2026",
        "category": "COMPLIANCE",
        "learning_type": "COURSE",
        "difficulty": "BEGINNER",
        "duration_minutes": 45,
        "delivery_mode": "ONLINE",
        "language": "en",
        "status": "PUBLISHED"
    })
    assert c_resp.status_code == 201
    course_id = c_resp.json()["id"]

    # 1. Create Training Requirement
    req_resp = client.post("/api/v3/learning/training-requirements", json={
        "name": "Annual Code of Conduct Certification",
        "course_id": course_id,
        "applicability_rule": "ALL_EMPLOYEES",
        "due_days": 30,
        "recurrence": "ANNUAL",
        "mandatory": True,
        "compliance_reference": "POSH-2026",
    })
    assert req_resp.status_code == 201
    requirement = req_resp.json()
    req_id = requirement["id"]
    assert requirement["mandatory"] is True

    # 2. Assign Training to Employee
    due_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    assign_resp = client.post("/api/v3/learning/training-assignments", json={
        "requirement_id": req_id,
        "person_id": person_id,
        "due_at": due_date,
    })
    assert assign_resp.status_code == 201
    assignment = assign_resp.json()
    assert assignment["status"] == "ASSIGNED"

    # 3. Create Learning Plan for Employee
    plan_resp = client.post("/api/v3/learning/learning-plans", json={
        "person_id": person_id,
        "name": "H2 2026 Growth & Mastery Plan",
        "period_start": str(date.today()),
        "period_end": str(date.today() + timedelta(days=180)),
        "items": [
            {
                "course_id": course_id,
                "target_date": str(date.today() + timedelta(days=30)),
                "priority": "HIGH",
            }
        ]
    })
    assert plan_resp.status_code == 201
    plan = plan_resp.json()
    assert plan["name"] == "H2 2026 Growth & Mastery Plan"
    assert plan["status"] == "DRAFT"
    assert len(plan["items"]) == 1


def test_manager_team_dashboard_metrics():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)

    team_resp = client.get("/api/v3/learning/dashboard/team")
    assert team_resp.status_code == 200
    team_data = team_resp.json()
    assert "team_member_count" in team_data
    assert "team_enrollments_count" in team_data
    assert "team_completion_rate_pct" in team_data

