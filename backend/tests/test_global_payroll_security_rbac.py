"""
test_global_payroll_security_rbac.py - Module 21: Security, RBAC & IDOR Tests
Zeramai Enterprise HRMS
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, User, Person, UserRole
from app.auth import hash_password

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "MANAGER": ("manager@zeramai.com", "ChangeMe123!"),
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


def test_global_payroll_rbac_permissions():
    # Employee cannot configure country or pay group -> 403 Forbidden
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    resp_cfg = client.post("/api/v3/global-payroll/countries", json={
        "country_code": "DEU",
        "country_name": "Germany",
        "default_currency": "EUR",
    })
    assert resp_cfg.status_code == 403


def test_cross_tenant_idor_isolation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Fetch a country or calendar in primary tenant
    countries = client.get("/api/v3/global-payroll/countries").json()
    country_id = countries[0]["id"]

    # Create secondary tenant user
    db = SessionLocal()
    try:
        t2 = db.query(Tenant).filter(Tenant.domain == "payroll-tenant2.com").first()
        if not t2:
            t2 = Tenant(name="Payroll Tenant 2", domain="payroll-tenant2.com", is_active=True)
            db.add(t2)
            db.commit()
            db.refresh(t2)
        t2_id = t2.id

        u2 = db.query(User).filter(User.email == "pay_admin@tenant2.com").first()
        if not u2:
            p2 = Person(full_name="Payroll Admin 2", email="pay_admin@tenant2.com")
            db.add(p2)
            db.flush()
            u2 = User(
                email="pay_admin@tenant2.com",
                hashed_password=hash_password("Password123!"),
                role=UserRole.HR_ADMIN,
                person_id=p2.id,
                is_active=True,
            )
            db.add(u2)
            db.commit()
    finally:
        db.close()

    # Login as secondary tenant admin
    sec_token = login("pay_admin@tenant2.com", "Password123!")
    set_auth(sec_token)

    # Attempt to access primary tenant's country details using secondary tenant header -> 404
    resp_idor = client.get(f"/api/v3/global-payroll/countries/{country_id}", headers={"X-Tenant-ID": t2_id})
    assert resp_idor.status_code == 404


def test_manager_salary_payslip_restriction():
    # Manager role must NOT be able to view another employee's individual payroll result or salary
    mgr_token = login(*CREDENTIALS["MANAGER"])
    set_auth(mgr_token)

    # Get demo employee id
    db = SessionLocal()
    try:
        emp = db.query(Person).filter(Person.email == "employee@example.com").first()
        emp_id = emp.id
    finally:
        db.close()

    # Attempt to query employee's specific results as manager -> 403 or filtered to own
    resp = client.get(f"/api/v3/global-payroll/results?person_id={emp_id}")
    # Since manager is not HR admin or the employee himself, access is forbidden or empty
    assert resp.status_code in [403, 200]
    if resp.status_code == 200:
        data = resp.json()
        assert all(r["person_id"] != emp_id for r in data)


def test_employee_payslip_ownership_authorization():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)
    slips = client.get("/api/v3/global-payroll/payslips").json()
    if not slips:
        cals = client.get("/api/v3/global-payroll/calendars").json()
        cal = next((c for c in cals if (c.get("pay_group") and c.get("pay_group", {}).get("currency") == "INR") or "IND" in c.get("name", "")), cals[0])
        cal_id = cal["id"]
        client.post(f"/api/v3/global-payroll/runs/{cal_id}/calculate", json={"recalculate_existing": True})
        client.post(f"/api/v3/global-payroll/runs/{cal_id}/approve")
        client.post(f"/api/v3/global-payroll/runs/{cal_id}/finalize")
        slips = client.get("/api/v3/global-payroll/payslips").json()

    slip_id = slips[0]["id"]

    # Login as employee who does NOT own this payslip (create a temporary second employee)
    db = SessionLocal()
    try:
        p_other = db.query(Person).filter(Person.email == "other_emp@zeramai.com").first()
        if not p_other:
            p_other = Person(full_name="Other Employee", email="other_emp@zeramai.com")
            db.add(p_other)
            db.flush()
            u_other = User(
                email="other_emp@zeramai.com",
                hashed_password=hash_password("Password123!"),
                role=UserRole.EMPLOYEE,
                person_id=p_other.id,
                is_active=True,
            )
            db.add(u_other)
            db.commit()
    finally:
        db.close()

    other_token = login("other_emp@zeramai.com", "Password123!")
    set_auth(other_token)

    # Attempt to get primary employee's payslip -> 403 Forbidden
    resp = client.get(f"/api/v3/global-payroll/payslips/{slip_id}")
    assert resp.status_code == 403
    assert "access forbidden" in resp.json()["detail"].lower()
