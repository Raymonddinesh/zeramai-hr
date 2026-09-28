"""
test_finance_journals.py - Module 16: Double-Entry Payroll Journals & Immutability Tests
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "FINANCE": ("finance@zeramai.com", "ChangeMe123!"),
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


def test_gl_accounts_and_mappings():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Create a custom GL account
    gl_resp = client.post("/api/v3/finance/gl-accounts", json={
        "code": "50990",
        "name": "Overtime & Shift Allowance Expense",
        "account_type": "EXPENSE",
        "active": True,
    })
    assert gl_resp.status_code in [200, 201]
    gl_data = gl_resp.json()
    assert gl_data["code"] == "50990"

    # 2. List GL accounts
    list_resp = client.get("/api/v3/finance/gl-accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    codes = [a["code"] for a in accounts]
    assert "50100" in codes  # From seed
    assert "50990" in codes

    # 3. List GL Mappings
    map_resp = client.get("/api/v3/finance/gl-mappings")
    assert map_resp.status_code == 200
    mappings = map_resp.json()
    assert len(mappings) >= 1


def test_payroll_journal_generation_and_balance_invariant():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # First, let's ensure a PayrollRun exists or create one
    from app.database import SessionLocal
    from app.models import PayrollRun, PayrollRunStatus, Tenant
    from datetime import date
    import uuid

    db = SessionLocal()
    tenant = db.query(Tenant).first()
    t_id = tenant.id if tenant else str(uuid.uuid4())

    payroll_run = db.query(PayrollRun).filter(PayrollRun.status == PayrollRunStatus.APPROVED).first()
    if not payroll_run:
        payroll_run = PayrollRun(
            month="2026-03",
            status=PayrollRunStatus.APPROVED,
            total_gross=500000.0,
            total_deductions=80000.0,
            total_net=420000.0,
        )
        db.add(payroll_run)
        db.commit()
        db.refresh(payroll_run)

    p_run_id = payroll_run.id
    db.close()

    # Generate payroll journal
    gen_resp = client.post("/api/v3/finance/payroll-journals/generate", json={
        "payroll_run_id": p_run_id,
        "period_key": "2026-03",
    })
    assert gen_resp.status_code in [200, 201]
    journal = gen_resp.json()

    # Verify double-entry balance invariant: total_debit == total_credit
    total_debit = float(journal["total_debit"])
    total_credit = float(journal["total_credit"])
    assert abs(total_debit - total_credit) < 0.001
    assert total_debit > 0
    assert journal["status"] == "DRAFT"
    journal_id = journal["id"]

    # Retrieve journal by ID with lines
    get_resp = client.get(f"/api/v3/finance/payroll-journals/{journal_id}")
    assert get_resp.status_code == 200
    j_detail = get_resp.json()
    assert len(j_detail["lines"]) >= 2
    sum_dr = sum(float(l.get("debit", l.get("debit_amount", 0))) for l in j_detail["lines"])
    sum_cr = sum(float(l.get("credit", l.get("credit_amount", 0))) for l in j_detail["lines"])
    assert abs(sum_dr - sum_cr) < 0.001


def test_payroll_journal_approval_and_posting_immutability():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Fetch a draft journal
    list_resp = client.get("/api/v3/finance/payroll-journals")
    assert list_resp.status_code == 200
    journals = list_resp.json()
    draft_journals = [j for j in journals if j["status"] == "DRAFT"]
    assert len(draft_journals) >= 1
    j_id = draft_journals[0]["id"]

    # 2. Cannot post before approval
    post_unapproved = client.post(f"/api/v3/finance/payroll-journals/{j_id}/post", json={})
    assert post_unapproved.status_code == 400

    # 3. Approve journal
    appr_resp = client.post(f"/api/v3/finance/payroll-journals/{j_id}/approve", json={})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVED"

    # 4. Post journal to GL
    post_resp = client.post(f"/api/v3/finance/payroll-journals/{j_id}/post", json={})
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "POSTED"

    # 5. IMMUTABILITY CHECK: Attempting to post again must be REJECTED (HTTP 400)
    post_again = client.post(f"/api/v3/finance/payroll-journals/{j_id}/post", json={})
    assert post_again.status_code == 400
    assert "Only APPROVED journals can be posted" in post_again.json().get("detail", "")


def test_payroll_journal_reversal_workflow():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # Fetch posted journal
    list_resp = client.get("/api/v3/finance/payroll-journals")
    assert list_resp.status_code == 200
    posted_journals = [j for j in list_resp.json() if j["status"] == "POSTED"]
    assert len(posted_journals) >= 1
    orig_j_id = posted_journals[0]["id"]

    # Reverse journal
    rev_resp = client.post(f"/api/v3/finance/payroll-journals/{orig_j_id}/reverse", json={
        "reason": "Test reversal for payroll correction",
    })
    assert rev_resp.status_code in [200, 201]
    rev_data = rev_resp.json()

    assert rev_data["original_journal_id"] == orig_j_id
    assert "REV-" in rev_data["reversal_journal_number"]

    # Verify original journal is now REVERSED
    orig_resp = client.get(f"/api/v3/finance/payroll-journals/{orig_j_id}")
    assert orig_resp.status_code == 200
    assert orig_resp.json()["status"] == "REVERSED"

    # Verify reversal journal exists, is balanced, and lines swap debits/credits
    rev_j_id = rev_data["reversal_journal_id"]
    rev_j_resp = client.get(f"/api/v3/finance/payroll-journals/{rev_j_id}")
    assert rev_j_resp.status_code == 200
    rev_j_detail = rev_j_resp.json()
    assert abs(float(rev_j_detail["total_debit"]) - float(rev_j_detail["total_credit"])) < 0.001
