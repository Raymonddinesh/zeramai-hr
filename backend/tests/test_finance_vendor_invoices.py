"""
test_finance_vendor_invoices.py - Module 16: Vendor Management, Contracts, Invoices & Expense Linkage Tests
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


def test_vendor_and_contract_management():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # 1. Register a Vendor
    v_resp = client.post("/api/v3/finance/vendors", json={
        "vendor_code": "V-TATA-01",
        "name": "Tata AIG Health Insurance",
        "category": "BENEFITS",
        "tax_identifier": "27AABCT1234F1Z1",
        "contact_reference": "Pooja Sharma <corporate@tataaig.com>",
        "currency": "INR",
        "active": True,
    })
    assert v_resp.status_code in [200, 201]
    vendor_data = v_resp.json()
    assert vendor_data["name"] == "Tata AIG Health Insurance"
    vendor_id = vendor_data["id"]

    # 2. Add Vendor Contract
    c_resp = client.post(f"/api/v3/finance/vendors/{vendor_id}/contracts", json={
        "contract_reference": "TATA-GMC-2026",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "recurring_amount": 3500000.0,
        "payment_frequency": "ANNUAL",
        "status": "ACTIVE",
    })
    assert c_resp.status_code in [200, 201]
    contract_data = c_resp.json()
    assert contract_data["contract_reference"] == "TATA-GMC-2026"

    # 3. List Vendors
    list_v = client.get("/api/v3/finance/vendors")
    assert list_v.status_code == 200
    assert any(v["id"] == vendor_id for v in list_v.json())


def test_vendor_invoice_lifecycle_and_approval():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # Get a vendor
    v_resp = client.get("/api/v3/finance/vendors")
    assert v_resp.status_code == 200
    vendors = v_resp.json()
    assert len(vendors) >= 1
    vendor_id = vendors[0]["id"]

    # 1. Submit Vendor Invoice
    inv_resp = client.post("/api/v3/finance/invoices", json={
        "vendor_id": vendor_id,
        "invoice_number": "INV-2026-0091",
        "invoice_date": "2026-03-15",
        "due_date": "2026-04-15",
        "amount": 100000.0,
        "tax_amount": 18000.0,
        "total_amount": 118000.0,
        "currency": "INR",
        "status": "SUBMITTED",
    })
    assert inv_resp.status_code in [200, 201]
    inv_data = inv_resp.json()
    assert inv_data["invoice_number"] == "INV-2026-0091"
    invoice_id = inv_data["id"]

    # 2. Approve Invoice
    appr_resp = client.post(f"/api/v3/finance/invoices/{invoice_id}/approve", json={})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVED"

    # 3. Pay Invoice
    pay_resp = client.post(f"/api/v3/finance/invoices/{invoice_id}/pay", json={
        "payment_reference": "UTR-HDFC-991283",
        "paid_amount": 118000.0,
    })
    assert pay_resp.status_code == 200
    paid_data = pay_resp.json()
    assert paid_data["status"] == "PAID"
    assert paid_data["payment_reference"] == "UTR-HDFC-991283"


def test_expense_accounting_linkage():
    token = login(*CREDENTIALS["FINANCE"])
    set_auth(token)

    # Link an expense reimbursement to a GL account and cost center
    from app.database import SessionLocal
    from app.models import Person
    from app.models_v3 import CostCenter
    from app.models_finance import GLAccount

    db = SessionLocal()
    person = db.query(Person).first()
    person_id = person.id if person else "demo-person"
    cc = db.query(CostCenter).first()
    cc_id = cc.id if cc else "demo-cc"
    gl = db.query(GLAccount).filter(GLAccount.code == "50100").first()
    gl_id = gl.id if gl else None
    db.close()

    resp = client.post("/api/v3/finance/expense-entries", json={
        "source_type": "REIMBURSEMENT",
        "source_reference_id": "REIMB-CLAIM-882",
        "person_id": person_id,
        "cost_center_id": cc_id,
        "gl_account_id": gl_id,
        "amount": 4500.0,
        "currency": "INR",
        "transaction_date": "2026-03-20",
        "status": "POSTED",
        "description": "Client travel & transport reimbursement",
    })
    assert resp.status_code in [200, 201]
    assert resp.json()["source_reference_id"] == "REIMB-CLAIM-882"
