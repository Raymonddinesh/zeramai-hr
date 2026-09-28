"""
test_learning_assessments_certifications.py - Module 18: Assessments, Answer-Key Protection & Certifications
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


def test_assessment_creation_and_answer_key_protection():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)

    # 1. Create Course for Assessment
    c_resp = client.post("/api/v3/learning/courses", json={
        "course_code": f"CRS-SEC-{datetime.utcnow().timestamp()}",
        "title": "Secure Coding & OWASP Standards",
        "category": "TECHNICAL",
        "learning_type": "COURSE",
        "difficulty": "ADVANCED",
        "duration_minutes": 90,
        "delivery_mode": "ONLINE",
        "language": "en",
        "status": "PUBLISHED"
    })
    assert c_resp.status_code == 201
    course_id = c_resp.json()["id"]

    # 2. Create Assessment with Questions containing Secret Correct Answers
    a_resp = client.post("/api/v3/learning/assessments", json={
        "course_id": course_id,
        "title": "OWASP Top 10 Certification Exam",
        "passing_score": 75.0,
        "attempts_allowed": 2,
        "duration_minutes": 30,
        "questions": [
            {
                "question_type": "MULTIPLE_CHOICE",
                "question_text": "Which vulnerability occurs when untrusted user input is directly concatenated into a SQL statement?",
                "options_json": '["SQL Injection", "XSS", "CSRF", "SSRF"]',
                "correct_answer": "SQL Injection",
                "sequence": 1,
                "points": 50.0,
            },
            {
                "question_type": "TRUE_FALSE",
                "question_text": "Prepared statements prevent SQL injection attacks.",
                "options_json": '["True", "False"]',
                "correct_answer": "True",
                "sequence": 2,
                "points": 50.0,
            }
        ]
    })
    assert a_resp.status_code == 201
    assessment = a_resp.json()
    assessment_id = assessment["id"]
    assert assessment["passing_score"] == 75.0

    # 3. Security Test: GET /assessments and GET /assessments/{id} MUST NOT leak correct_answer
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    get_resp = client.get(f"/api/v3/learning/assessments/{assessment_id}")
    assert get_resp.status_code == 200
    exam_payload = get_resp.json()
    assert len(exam_payload["questions"]) == 2
    for q in exam_payload["questions"]:
        assert "correct_answer" not in q or q.get("correct_answer") is None
        assert "SQL Injection" not in str(q.get("correct_answer"))

    # 4. Submit Passing Attempt (100% score)
    q1_id = exam_payload["questions"][0]["id"]
    q2_id = exam_payload["questions"][1]["id"]

    attempt_resp = client.post(f"/api/v3/learning/assessments/{assessment_id}/attempt", json={
        "assessment_id": assessment_id,
        "answers": {
            q1_id: "SQL Injection",
            q2_id: "True",
        }
    })
    assert attempt_resp.status_code == 201
    attempt = attempt_resp.json()
    assert attempt["score"] == 100.0
    assert attempt["passed"] is True
    assert attempt["attempt_number"] == 1

    # 5. Submit Second Attempt (Failed: 50% score)
    attempt2_resp = client.post(f"/api/v3/learning/assessments/{assessment_id}/attempt", json={
        "assessment_id": assessment_id,
        "answers": {
            q1_id: "SQL Injection",
            q2_id: "False",  # incorrect
        }
    })
    assert attempt2_resp.status_code == 201
    assert attempt2_resp.json()["score"] == 50.0
    assert attempt2_resp.json()["passed"] is False
    assert attempt2_resp.json()["attempt_number"] == 2

    # 6. Exceed Maximum Allowed Attempts (allowed = 2) -> Expect HTTP 400
    attempt3_resp = client.post(f"/api/v3/learning/assessments/{assessment_id}/attempt", json={
        "assessment_id": assessment_id,
        "answers": {q1_id: "SQL Injection"}
    })
    assert attempt3_resp.status_code == 400
    assert "attempts" in attempt3_resp.json()["detail"].lower()


def test_certifications_and_expiry_tracking():
    admin_token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(admin_token)
    person_id = get_demo_person_id()

    # 1. Create Industry Certification
    cert_resp = client.post("/api/v3/learning/certifications", json={
        "name": "Certified Kubernetes Administrator (CKA)",
        "issuing_body": "Linux Foundation & CNCF",
        "description": "Enterprise container orchestration credential.",
        "validity_months": 36,
        "status": "ACTIVE",
    })
    assert cert_resp.status_code == 201
    cert = cert_resp.json()
    cert_id = cert["id"]

    # 2. Employee Submits Earned Credential
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    today = date.today()
    in_two_years = today + timedelta(days=730)
    sub_resp = client.post("/api/v3/learning/employee-certifications", json={
        "person_id": person_id,
        "certification_id": cert_id,
        "credential_number": "CKA-2026-987654",
        "issued_date": str(today),
        "expiry_date": str(in_two_years),
        "document_reference": "https://certificates.example.com/cka/987654.pdf",
    })
    assert sub_resp.status_code == 201
    emp_cert = sub_resp.json()
    emp_cert_id = emp_cert["id"]
    assert emp_cert["verification_status"] == "PENDING"
    assert emp_cert["is_expired"] is False

    # 3. HR Admin Verifies Credential
    set_auth(admin_token)
    verify_resp = client.post(f"/api/v3/learning/employee-certifications/{emp_cert_id}/verify", json={
        "verification_status": "VERIFIED"
    })
    assert verify_resp.status_code == 200
    verified = verify_resp.json()
    assert verified["verification_status"] == "VERIFIED"
    assert verified["verified_by"] is not None
