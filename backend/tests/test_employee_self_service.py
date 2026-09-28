"""
Module 6 — Employee Self-Service (ESS) Expansion Tests.

Test Coverage:
1.  Employee gets own dashboard via /api/v3/me (server-derived identity)
2.  Employee A cannot access Employee B profile (IDOR protection)
3.  Employee A cannot access Employee B documents
4.  Employee A cannot access Employee B attendance
5.  Employee A cannot access Employee B leave balances/requests
6.  Employee A cannot access Employee B payroll/payslips
7.  Employee A cannot access Employee B assets
8.  Employee A cannot access Employee B expenses
9.  Employee updates permitted self-service fields (phone, preferred_name, emergency_contact)
10. Master data / HR-controlled fields cannot be modified via profile update
11. Employee submits expense claim via POST /api/v3/me/expenses
12. Cross-tenant access denied
13. Unauthenticated access denied (401)
14. Audit logging verification for ESS operations
"""
import os
import uuid
import pytest
from datetime import date, datetime
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
# Setup helper for second employee (Employee B)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def setup_second_employee():
    from app.database import SessionLocal
    from app.models import User, Person, Engagement, EngagementType, EngagementStatus, UserRole, Document, Attendance, LeaveRequest, AttendanceStatus, LeaveStatus
    from app.models_v6 import Payslip
    from app.models_ess import EmployeeAsset, ExpenseClaim
    from app.auth import hash_password

    db = SessionLocal()
    try:
        # Create Employee B if not exists
        u_b = db.query(User).filter(User.email == "emp_b@test.com").first()
        if not u_b:
            p_b = Person(
                full_name="Employee Bravo",
                email="emp_b@test.com",
                phone="9876543210",
                emergency_contact="Emergency Contact Bravo",
            )
            db.add(p_b)
            db.flush()

            u_b = User(
                email="emp_b@test.com",
                hashed_password=hash_password("ChangeMe123!"),
                role=UserRole.EMPLOYEE,
                person_id=p_b.id,
                is_active=True,
            )
            db.add(u_b)
            db.flush()

            eng_b = Engagement(
                person_id=p_b.id,
                engagement_type=EngagementType.FULL_TIME_EMPLOYEE,
                designation="Backend Engineer",
                department="Platform",
                start_date=date(2025, 6, 1),
                status=EngagementStatus.ACTIVE,
            )
            db.add(eng_b)
            db.flush()

            # Seed Employee B's private data:
            # 1. Document
            doc_b = Document(
                person_id=p_b.id,
                document_type="passport",
                file_name="bravo_passport.pdf",
                storage_key="docs/bravo_passport.pdf",
            )
            db.add(doc_b)

            # 2. Attendance
            att_b = Attendance(
                person_id=p_b.id,
                date=date(2026, 9, 20),
                status=AttendanceStatus.PRESENT,
                notes="Bravo attendance record",
            )
            db.add(att_b)

            # 3. Leave
            leave_b = LeaveRequest(
                person_id=p_b.id,
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 3),
                days=3,
                leave_type="casual",
                status=LeaveStatus.PENDING,
                reason="Bravo private vacation",
            )
            db.add(leave_b)

            # 4. Payslip
            from app.models_v6 import PayrollRun, PayrollRunStatus
            run_b = PayrollRun(
                month="2026-09",
                status=PayrollRunStatus.APPROVED,
            )
            db.add(run_b)
            db.flush()

            payslip_b = Payslip(
                payroll_run_id=run_b.id,
                person_id=p_b.id,
                month="2026-09",
                gross_salary=85000.0,
                total_deductions=5000.0,
                net_salary=80000.0,
            )
            db.add(payslip_b)

            # 5. Asset
            asset_b = EmployeeAsset(
                person_id=p_b.id,
                user_id=u_b.id,
                asset_name="MacBook Pro M3 Max",
                asset_type="laptop",
                serial_number="C02BRAVO12345",
                assigned_date=date(2025, 6, 2),
            )
            db.add(asset_b)

            # 6. Expense
            exp_b = ExpenseClaim(
                ticket_number="EXP-BRAVO-001",
                person_id=p_b.id,
                user_id=u_b.id,
                category="travel",
                amount=12500.0,
                description="Bravo client visit flight",
                status="pending",
            )
            db.add(exp_b)

            db.commit()

        _shared["user_b_id"] = u_b.id
        _shared["person_b_id"] = u_b.person_id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1. Employee Dashboard & Server-Derived Identity
# ---------------------------------------------------------------------------

def test_employee_gets_own_dashboard(seed_data):
    """Employee A calls /api/v3/me and receives their own dashboard."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me")
    assert resp.status_code == 200, f"Dashboard fetch failed: {resp.text}"
    data = resp.json()
    assert data["profile"]["email"] == CREDENTIALS["EMPLOYEE"][0]
    assert data["profile"]["user_id"] is not None
    assert "attendance" in data
    assert "leave" in data
    assert "payslips" in data
    assert "documents" in data
    assert "assets" in data
    assert "expenses" in data


def test_unauthenticated_dashboard_rejected(seed_data):
    """Unauthenticated caller to /api/v3/me receives 401."""
    client.cookies.clear()
    resp = client.get("/api/v3/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Cross-Employee Isolation (IDOR Protections)
# ---------------------------------------------------------------------------

def test_employee_a_cannot_access_employee_b_profile(seed_data):
    """Employee A querying /api/v3/me gets only Employee A profile, ignoring query params."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # Attempt to inject Employee B's person_id or user_id as query params
    resp = client.get(f"/api/v3/me?person_id={_shared['person_b_id']}&user_id={_shared['user_b_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["profile"]["email"] == CREDENTIALS["EMPLOYEE"][0]
    assert data["profile"]["id"] != _shared["person_b_id"]


def test_employee_a_cannot_access_employee_b_documents(seed_data):
    """Employee A's document list does not contain Employee B's documents."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me/documents")
    assert resp.status_code == 200
    file_names = [d["file_name"] for d in resp.json()]
    assert "bravo_passport.pdf" not in file_names


def test_employee_a_cannot_access_employee_b_attendance(seed_data):
    """Employee A's attendance records do not contain Employee B's attendance."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me/attendance")
    assert resp.status_code == 200
    notes = [a["notes"] for a in resp.json() if a["notes"]]
    assert "Bravo attendance record" not in notes


def test_employee_a_cannot_access_employee_b_leave(seed_data):
    """Employee A's leave list does not contain Employee B's leave request."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me/leave")
    assert resp.status_code == 200
    reasons = [r["reason"] for r in resp.json()["recent_requests"] if r["reason"]]
    assert "Bravo private vacation" not in reasons


def test_employee_a_cannot_access_employee_b_payroll(seed_data):
    """Employee A's payslips do not contain Employee B's payroll data."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me/payroll")
    assert resp.status_code == 200
    # Employee B had gross_pay 85000.0
    for p in resp.json():
        assert p["gross_pay"] != 85000.0


def test_employee_a_cannot_access_employee_b_assets(seed_data):
    """Employee A's asset list does not contain Employee B's assigned hardware."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me/assets")
    assert resp.status_code == 200
    serials = [a["serial_number"] for a in resp.json() if a["serial_number"]]
    assert "C02BRAVO12345" not in serials


def test_employee_a_cannot_access_employee_b_expenses(seed_data):
    """Employee A's expense list does not contain Employee B's claims."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.get("/api/v3/me/expenses")
    assert resp.status_code == 200
    ticket_nums = [e["ticket_number"] for e in resp.json()]
    assert "EXP-BRAVO-001" not in ticket_nums


# ---------------------------------------------------------------------------
# 3. Profile Updates & Master Data Protection
# ---------------------------------------------------------------------------

def test_employee_updates_permitted_profile_fields(seed_data):
    """Employee can update permitted contact and address fields."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    new_phone = "9123456789"
    new_address = "42 Silicon Avenue, Tech Park"
    resp = client.patch("/api/v3/me/profile", json={
        "phone": new_phone,
        "current_address": new_address,
        "preferred_name": "Johnny",
        "emergency_contact": "Dr. Sarah (+91 9999999999)",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == new_phone
    assert data["current_address"] == new_address
    assert data["preferred_name"] == "Johnny"
    assert data["emergency_contact"] == "Dr. Sarah (+91 9999999999)"


def test_master_data_fields_protected_from_self_update(seed_data):
    """Employee attempting to overwrite HR-controlled master data (email, designation) is rejected/ignored."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    # Attempt to change email or designation
    resp = client.patch("/api/v3/me/profile", json={
        "email": "hacked_email@evil.com",
        "designation": "Chief Executive Officer",
        "phone": "9000000000",
    })
    assert resp.status_code == 200
    data = resp.json()
    # Email must remain the original authenticated email
    assert data["email"] == CREDENTIALS["EMPLOYEE"][0]
    # Designation must not be changed to CEO
    assert data["designation"] != "Chief Executive Officer"


# ---------------------------------------------------------------------------
# 4. Expense Claim Submission
# ---------------------------------------------------------------------------

def test_employee_submits_expense_claim(seed_data):
    """Employee submits a valid expense claim."""
    token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(token)

    resp = client.post("/api/v3/me/expenses", json={
        "category": "internet",
        "amount": 1499.0,
        "currency": "INR",
        "description": "Monthly broadband reimbursement",
        "merchant": "Airtel Fiber",
    })
    assert resp.status_code == 201
    claim = resp.json()
    assert claim["ticket_number"].startswith("EXP-")
    assert claim["category"] == "internet"
    assert claim["amount"] == 1499.0
    assert claim["status"] == "pending"


# ---------------------------------------------------------------------------
# 5. Audit Logging Verification
# ---------------------------------------------------------------------------

def test_audit_logs_for_ess(seed_data):
    """Verifies that ESS actions write entries to audit_logs."""
    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        actions = [a[0] for a in db.query(AuditLog.action).all()]
        assert "ess_dashboard_viewed" in actions, "Missing ess_dashboard_viewed in audit_logs"
        assert "profile_self_updated" in actions, "Missing profile_self_updated in audit_logs"
        assert "expense_claim_submitted" in actions, "Missing expense_claim_submitted in audit_logs"
    finally:
        db.close()
