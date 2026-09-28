"""
test_learning_security_rbac.py - Module 18: Security, Multi-Tenant Isolation & Confidential Notes Protection
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Person, Tenant

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


def test_rbac_learning_access_controls():
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    # 1. Regular employee CANNOT create courses -> Expect HTTP 403
    c_resp = client.post("/api/v3/learning/courses", json={
        "course_code": "UNAUTH-CRS-01",
        "title": "Unauthorized Course",
    })
    assert c_resp.status_code == 403

    # 2. Regular employee CANNOT create training requirements -> Expect HTTP 403
    r_resp = client.post("/api/v3/learning/training-requirements", json={
        "name": "Unauthorized Requirement",
        "course_id": "dummy-id",
    })
    assert r_resp.status_code == 403

    # 3. Regular employee CANNOT view team manager dashboard -> Expect HTTP 403
    t_resp = client.get("/api/v3/learning/dashboard/team")
    assert t_resp.status_code == 403

    # 4. Regular employee CANNOT view enterprise analytics -> Expect HTTP 403
    a_resp = client.get("/api/v3/learning/analytics")
    assert a_resp.status_code == 403

    # 5. Regular employee CAN view own learning dashboard -> Expect HTTP 200
    d_resp = client.get("/api/v3/learning/dashboard")
    assert d_resp.status_code == 200
    dash = d_resp.json()
    assert "assigned_courses_count" in dash


def test_confidential_manager_notes_protection():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    person_id = get_demo_person_id()

    # 1. Admin/Manager creates Development Plan with Confidential Manager Notes
    dp_resp = client.post("/api/v3/learning/development-plans", json={
        "person_id": person_id,
        "current_role": "Software Engineer II",
        "target_role": "Senior Engineer",
        "career_direction": "Technical Leadership",
        "review_period": "FY27",
        "employee_notes": "Employee stated desire to lead upcoming migration project.",
        "manager_notes": "CONFIDENTIAL: Evaluated readiness for promotion in Q3. Needs to improve stakeholder communication.",
    })
    assert dp_resp.status_code == 201
    plan_id = dp_resp.json()["id"]

    # Admin CAN view confidential manager notes
    admin_view = client.get(f"/api/v3/learning/development-plans?person_id={person_id}")
    assert admin_view.status_code == 200
    plans = admin_view.json()
    target_plan = [p for p in plans if p["id"] == plan_id][0]
    assert target_plan["manager_notes"] is not None
    assert "CONFIDENTIAL" in target_plan["manager_notes"]

    # 2. Employee retrieves own Development Plan -> manager_notes MUST BE REDACTED (None)
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    emp_view = client.get(f"/api/v3/learning/development-plans?person_id={person_id}")
    assert emp_view.status_code == 200
    emp_plans = emp_view.json()
    emp_target_plan = [p for p in emp_plans if p["id"] == plan_id][0]
    assert emp_target_plan["manager_notes"] is None  # REDACTED FOR PRIVACY
    assert emp_target_plan["employee_notes"] is not None  # Employee notes preserved


def test_multi_tenant_isolation_and_idor():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)

    # 1. Create a foreign tenant and course in that foreign tenant
    db = SessionLocal()
    foreign_tenant_id = f"foreign-tenant-{int(datetime.utcnow().timestamp())}"
    try:
        t = Tenant(id=foreign_tenant_id, name="Foreign Corp", domain="foreign.example.com")
        db.add(t)
        db.commit()
    finally:
        db.close()

    # Create course in foreign tenant
    client.headers.update({"X-Tenant-ID": foreign_tenant_id})
    f_course_resp = client.post("/api/v3/learning/courses", json={
        "course_code": f"FOR-CRS-{int(datetime.utcnow().timestamp())}",
        "title": "Foreign Confidential Course",
        "category": "CONFIDENTIAL",
        "learning_type": "COURSE",
        "status": "PUBLISHED"
    })
    assert f_course_resp.status_code == 201
    foreign_course_id = f_course_resp.json()["id"]

    # 2. Switch back to primary default tenant
    client.headers.pop("X-Tenant-ID", None)

    # 3. Attempt to fetch foreign course with default tenant context -> Must return 404 (IDOR Prevention)
    cross_get = client.get(f"/api/v3/learning/courses/{foreign_course_id}")
    assert cross_get.status_code == 404
