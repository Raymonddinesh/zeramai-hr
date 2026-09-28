"""
Module 7 — Compensation & Benefits Management Tests.

Security, Workflow, IDOR, Cross-Tenant, Payroll Integration & Audit Logging Tests.
"""
import os
import uuid
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)



CREDENTIALS = {
    "SUPER_ADMIN":    ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN":       ("hr@zeramai.com",          "ChangeMe123!"),
    "HIRING_MANAGER": ("manager@zeramai.com",      "ChangeMe123!"),
    "FINANCE":        ("finance@zeramai.com",       "ChangeMe123!"),
    "EMPLOYEE":       ("employee@example.com",      "ChangeMe123!"),
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


_shared: dict = {}


# ---------------------------------------------------------------------------
# Setup helper: Ensure primary employee has an initial active salary structure
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def ensure_test_setup():
    from app.database import SessionLocal
    from app.models import User, Person
    from app.models_v6 import SalaryStructure

    db = SessionLocal()
    try:
        emp_user = db.query(User).filter(User.email == CREDENTIALS["EMPLOYEE"][0]).first()
        assert emp_user and emp_user.person_id
        _shared["emp_person_id"] = emp_user.person_id
        _shared["emp_user_id"] = emp_user.id

        # Retrieve hiring manager user
        mgr_user = db.query(User).filter(User.email == CREDENTIALS["HIRING_MANAGER"][0]).first()
        _shared["mgr_user_id"] = mgr_user.id



        # Ensure employee has clean baseline active salary structure for this test session
        if "setup_done" not in _shared:
            for ss in db.query(SalaryStructure).filter(SalaryStructure.person_id == emp_user.person_id).all():
                ss.is_active = False
            baseline_ss = SalaryStructure(
                person_id=emp_user.person_id,
                name="Baseline CTC 2026",
                effective_from=date(2026, 1, 1),
                ctc_annual=1200000.0,
                ctc_monthly=100000.0,
                currency="INR",
                components_json=[
                    {"code": "BASIC", "name": "Basic Salary", "amount": 50000.0, "type": "earning"},
                    {"code": "HRA", "name": "House Rent Allowance", "amount": 30000.0, "type": "earning"},
                    {"code": "SPECIAL", "name": "Special Allowance", "amount": 20000.0, "type": "earning"},
                ],
                is_active=True,
            )
            db.add(baseline_ss)
            db.commit()
            db.refresh(baseline_ss)
            _shared["initial_ss_id"] = baseline_ss.id
            _shared["setup_done"] = True
    finally:
        db.close()





# ---------------------------------------------------------------------------
# 1. Employee Ownership & IDOR Protections
# ---------------------------------------------------------------------------

def test_employee_cannot_access_other_employee_compensation(seed_data):
    """Employee A cannot access Employee B's salary structure."""
    from app.database import SessionLocal
    from app.models import User, Person, Engagement, EngagementType, EngagementStatus, UserRole
    from app.auth import hash_password

    db = SessionLocal()
    try:
        p2 = db.query(Person).filter(Person.email == "other.emp@test.com").first()
        if not p2:
            p2 = Person(full_name="Other Employee", email="other.emp@test.com")
            db.add(p2)
            db.flush()
            u2 = User(
                email="other.emp@test.com",
                hashed_password=hash_password("ChangeMe123!"),
                role=UserRole.EMPLOYEE,
                person_id=p2.id,
                is_active=True,
            )
            db.add(u2)
            db.commit()
        _shared["other_person_id"] = p2.id
    finally:
        db.close()

    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # Attempt to view other employee's structure
    resp = client.get(f"/api/v3/compensation/structures/{_shared['other_person_id']}")
    assert resp.status_code == 403, f"Expected 403 on IDOR attempt, got {resp.status_code}"

    # Attempt to view other employee's history
    resp_hist = client.get(f"/api/v3/compensation/{_shared['other_person_id']}/history")
    assert resp_hist.status_code == 403, f"Expected 403 on history IDOR, got {resp_hist.status_code}"


def test_employee_cannot_modify_own_compensation(seed_data):
    """Employee attempting to create or approve compensation revision is rejected (403)."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post("/api/v3/compensation/revisions", json={
        "person_id": _shared["emp_person_id"],
        "new_ctc_annual": 2500000.0,
        "effective_date": str(date.today()),
        "components_json": [{"code": "BASIC", "amount": 100000.0, "type": "earning"}],
        "reason": "annual_review",
    })
    assert resp.status_code == 403, f"Employee cannot create revision, got {resp.status_code}"


def test_unauthorized_role_cannot_view_org_compensation(seed_data):
    """Employee or non-HR role cannot list all company salary structures."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/compensation/structures")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 2. Manager Recommendation Scope & Prohibitions
# ---------------------------------------------------------------------------

def test_manager_cannot_directly_create_approved_compensation(seed_data):
    """Manager cannot directly create revisions via /revisions (needs compensation:manage)."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.post("/api/v3/compensation/revisions", json={
        "person_id": _shared["emp_person_id"],
        "new_ctc_annual": 1500000.0,
        "effective_date": str(date.today()),
        "components_json": [{"code": "BASIC", "amount": 75000.0, "type": "earning"}],
        "reason": "annual_review",
    })
    assert resp.status_code == 403


def test_manager_submits_recommendation_for_direct_report(seed_data):
    """Manager can recommend revision for their direct reporting team member."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.post("/api/v3/compensation/recommendations", json={
        "person_id": _shared["emp_person_id"],
        "proposed_ctc_annual": 1500000.0,
        "effective_date": str(date.today() + timedelta(days=15)),
        "reason": "promotion",
        "business_justification": "Outstanding performance leading Q3 product deliverables.",
    })
    assert resp.status_code == 201, f"Failed to submit recommendation: {resp.text}"
    data = resp.json()
    assert data["status"] == "submitted"
    assert data["recommended_by_id"] == _shared["mgr_user_id"]
    assert data["new_ctc_annual"] == 1500000.0
    _shared["mgr_revision_id"] = data["id"]


def test_manager_cannot_recommend_for_non_direct_report(seed_data):
    """Manager cannot recommend changes for an employee who does not report to them."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.post("/api/v3/compensation/recommendations", json={
        "person_id": _shared["other_person_id"],
        "proposed_ctc_annual": 1600000.0,
        "effective_date": str(date.today() + timedelta(days=15)),
        "reason": "annual_review",
        "business_justification": "Trying to change compensation for someone outside team.",
    })
    assert resp.status_code == 403


def test_manager_cannot_approve_own_recommendation(seed_data):
    """Manager who recommended a revision cannot approve it (Anti-Self-Approval check)."""
    token = login(*CREDENTIALS["HIRING_MANAGER"])
    set_auth(token)

    resp = client.post(f"/api/v3/compensation/revisions/{_shared['mgr_revision_id']}/approve")
    assert resp.status_code == 403, f"Expected 403 on self-approval attempt, got {resp.status_code}"


# ---------------------------------------------------------------------------
# 3. Revision Workflow, Approval & Effective-Dating
# ---------------------------------------------------------------------------

def test_unapproved_revision_is_not_effective_salary(seed_data):
    """Pending revision does not update the active salary structure."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # Check active structure for employee - must still be 1200000.0
    resp = client.get(f"/api/v3/compensation/structures/{_shared['emp_person_id']}")
    assert resp.status_code == 200
    assert resp.json()["ctc_annual"] == 1200000.0


def test_hr_admin_approves_revision_and_effective_dates_it(seed_data):
    """HR Admin approves the manager recommendation. New active structure is created and old deactivated."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.post(f"/api/v3/compensation/revisions/{_shared['mgr_revision_id']}/approve")
    assert resp.status_code == 200, f"Approval failed: {resp.text}"
    rev_data = resp.json()
    assert rev_data["status"] in ("approved", "effective")
    assert rev_data["approved_by_id"] is not None

    # Verify that employee now has the updated active structure
    resp_ss = client.get(f"/api/v3/compensation/structures/{_shared['emp_person_id']}")
    assert resp_ss.status_code == 200
    assert resp_ss.json()["ctc_annual"] == 1500000.0
    assert resp_ss.json()["id"] != _shared["initial_ss_id"]


def test_historical_compensation_cannot_be_silently_overwritten(seed_data):
    """Previous salary structure remains intact with effective_to date set."""
    from app.database import SessionLocal
    from app.models_v6 import SalaryStructure

    db = SessionLocal()
    try:
        old_ss = db.query(SalaryStructure).filter(SalaryStructure.id == _shared["initial_ss_id"]).first()
        assert old_ss is not None
        assert old_ss.is_active is False
        assert old_ss.effective_to is not None
        assert float(old_ss.ctc_annual) == 1200000.0
    finally:
        db.close()


def test_confidential_hr_notes_masked_from_employee(seed_data):
    """Confidential hr_notes are visible to HR Admin but masked (None) for regular employee."""
    # 1. HR creates revision with confidential notes
    token_hr = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token_hr)

    resp = client.post("/api/v3/compensation/revisions", json={
        "person_id": _shared["emp_person_id"],
        "new_ctc_annual": 1600000.0,
        "effective_date": str(date.today()),
        "components_json": [{"code": "BASIC", "amount": 80000.0, "type": "earning"}],
        "reason": "market_adjustment",
        "business_justification": "Market benchmark adjustment",
        "hr_notes": "CONFIDENTIAL: Internal retention flag raised by VP.",
    })
    assert resp.status_code == 201
    rev_id = resp.json()["id"]
    assert resp.json()["hr_notes"] == "CONFIDENTIAL: Internal retention flag raised by VP."

    # Approve so employee can view
    client.post(f"/api/v3/compensation/revisions/{rev_id}/approve")

    # 2. Employee inspects revision
    token_emp = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token_emp)

    emp_resp = client.get(f"/api/v3/compensation/revisions/{rev_id}")
    assert emp_resp.status_code == 200
    assert emp_resp.json()["hr_notes"] is None, "Confidential hr_notes leaked to employee!"


# ---------------------------------------------------------------------------
# 4. Bonuses & Payroll Integration Readiness
# ---------------------------------------------------------------------------

def test_hr_creates_and_approves_bonus(seed_data):
    """HR creates and approves a bonus for an employee."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    resp = client.post("/api/v3/compensation/bonuses", json={
        "person_id": _shared["emp_person_id"],
        "bonus_type": "performance",
        "amount": 50000.0,
        "currency": "INR",
        "pay_period": "2026-10",
        "effective_date": str(date.today()),
        "reason": "Q3 Target Exceeded",
    })
    assert resp.status_code == 201
    bonus = resp.json()
    assert bonus["status"] == "submitted"
    assert bonus["payroll_status"] == "pending"
    _shared["bonus_id"] = bonus["id"]

    # Approve bonus
    appr_resp = client.post(f"/api/v3/compensation/bonuses/{bonus['id']}/review", json={"action": "approve"})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"


def test_payroll_compute_integrates_approved_bonus(seed_data):
    """Executing payroll compute for 2026-10 incorporates the approved bonus into payslip earnings."""
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Create run
    run_resp = client.post("/api/payroll/runs", json={"month": "2026-10"})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # 2. Compute run
    comp_resp = client.post(f"/api/payroll/runs/{run_id}/compute")
    assert comp_resp.status_code == 200

    # 3. Check payslip for employee
    slips_resp = client.get(f"/api/payroll/runs/{run_id}/payslips")
    assert slips_resp.status_code == 200
    slips = slips_resp.json()
    emp_slip = next((s for s in slips if s["person_id"] == _shared["emp_person_id"]), None)
    assert emp_slip is not None

    # Bonus must be marked processed
    from app.database import SessionLocal
    from app.models_compensation import BonusIncentive
    db = SessionLocal()
    try:
        b = db.query(BonusIncentive).filter(BonusIncentive.id == _shared["bonus_id"]).first()
        assert b.payroll_status == "processed"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Benefits Foundation & Enrollments
# ---------------------------------------------------------------------------

def test_benefits_plan_creation_and_enrollment(seed_data):
    """HR creates a benefit plan and enrolls employee."""
    token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(token)

    # 1. Create plan
    plan_resp = client.post("/api/v3/benefits/plans", json={
        "name": "Comprehensive Medical Floater 5L",
        "benefit_type": "health_insurance",
        "provider": "Star Health",
        "description": "5 Lakhs family floater medical insurance",
        "employer_contribution": 1200.0,
        "employee_deduction": 300.0,
    })
    assert plan_resp.status_code == 201
    plan_id = plan_resp.json()["id"]
    _shared["plan_id"] = plan_id

    # 2. Enroll employee
    enroll_resp = client.post("/api/v3/benefits/enroll", json={
        "person_id": _shared["emp_person_id"],
        "benefit_plan_id": plan_id,
        "coverage_tier": "employee_and_spouse",
        "effective_date": str(date.today()),
        "notes": "Family addition verified",
    })
    assert enroll_resp.status_code == 201
    enr_data = enroll_resp.json()
    assert enr_data["status"] == "enrolled"
    assert enr_data["coverage_tier"] == "employee_and_spouse"
    assert enr_data["employer_contribution"] == 1200.0


def test_employee_views_own_compensation_and_benefits_self_service(seed_data):
    """Employee accesses their own compensation & benefits summary via /api/v3/compensation/me and /api/v3/me."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # 1. Via /api/v3/compensation/me
    comp_me = client.get("/api/v3/compensation/me")
    assert comp_me.status_code == 200
    comp_data = comp_me.json()
    assert comp_data["has_active_structure"] is True
    assert len(comp_data["enrolled_benefits"]) >= 1
    assert comp_data["enrolled_benefits"][0]["plan_name"] == "Comprehensive Medical Floater 5L"

    # 2. Via unified ESS /api/v3/me
    me_resp = client.get("/api/v3/me")
    assert me_resp.status_code == 200
    ess_data = me_resp.json()
    assert ess_data["compensation"] is not None
    assert ess_data["compensation"]["ctc_annual"] > 0
    assert len(ess_data["benefits"]) >= 1


# ---------------------------------------------------------------------------
# 6. Audit Logging Verification
# ---------------------------------------------------------------------------

def test_audit_logs_for_compensation_and_benefits(seed_data):
    """Verifies that all compensation and benefit actions are recorded in audit_logs."""
    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        actions = [a[0] for a in db.query(AuditLog.action).all()]
        assert "compensation_recommendation_submitted" in actions
        assert "compensation_revision_approved" in actions
        assert "benefit_plan_created" in actions
        assert "benefit_enrollment_created" in actions
    finally:
        db.close()
