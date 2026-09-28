"""
routers/finance.py - Module 16: Enterprise Finance, Billing & Workforce Cost Management Endpoints.

All endpoints mounted under /api/v3/finance/...
"""
import uuid
import csv
import io
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import AuditResult, User, UserRole, Person
from app.models_v3 import Tenant, LegalEntity, CostCenter
from app.models_v6 import PayrollRun
from app.models_finance import (
    FinancialDimension,
    FinancialDimensionValue,
    EmployeeCostAllocation,
    GLAccount,
    GLMapping,
    PayrollJournal,
    PayrollJournalLine,
    WorkforceCostRecord,
    ExpenseAccountingEntry,
    AccrualRule,
    AccrualRecord,
    WorkforceBudget,
    WorkforceBudgetLine,
    Vendor,
    VendorContract,
    VendorInvoice,
    PayrollJournalStatus,
    BudgetStatus,
    InvoiceStatus,
)
from app.schemas_finance import (
    FinancialDimensionCreate,
    FinancialDimensionUpdate,
    FinancialDimensionResponse,
    FinancialDimensionValueCreate,
    FinancialDimensionValueResponse,
    CostCenterCreate,
    CostCenterUpdate,
    CostCenterResponse,
    EmployeeCostAllocationCreate,
    EmployeeCostAllocationUpdate,
    EmployeeCostAllocationResponse,
    GLAccountCreate,
    GLAccountUpdate,
    GLAccountResponse,
    GLMappingCreate,
    GLMappingUpdate,
    GLMappingResponse,
    PayrollJournalCreate,
    PayrollJournalResponse,
    PayrollJournalLineResponse,
    JournalGenerateRequest,
    WorkforceCostRecordResponse,
    WorkforceCostCalculateRequest,
    ExpenseAccountingEntryCreate,
    ExpenseAccountingEntryResponse,
    AccrualRuleCreate,
    AccrualRuleUpdate,
    AccrualRuleResponse,
    AccrualRecordResponse,
    WorkforceBudgetCreate,
    WorkforceBudgetUpdate,
    WorkforceBudgetResponse,
    WorkforceBudgetLineCreate,
    WorkforceBudgetLineResponse,
    BudgetVsActualResponse,
    PayrollVarianceResponse,
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorContractCreate,
    VendorContractResponse,
    VendorInvoiceCreate,
    VendorInvoiceUpdate,
    VendorInvoiceResponse,
    AccountingExportRequest,
    AccountingExportResponse,
    FinanceDashboardMetrics,
)
from app.services.finance_service import (
    validate_employee_allocations,
    generate_payroll_journal,
    post_payroll_journal,
    reverse_payroll_journal,
    calculate_workforce_cost_records,
    calculate_budget_vs_actual,
    analyze_payroll_variance,
    generate_accounting_export,
    get_finance_dashboard_metrics,
)

router = APIRouter(prefix="/api/v3/finance", tags=["finance"])


def _resolve_tenant_id(request: Request, db: Session, user: Optional[User] = None) -> str:
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    if user and user.person and getattr(user.person, "tenant_id", None):
        return user.person.tenant_id
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def _can_read_finance(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.FINANCE)
        or has_permission(user, "finance:read", db)
        or has_permission(user, "finance.read", db)
        or has_permission(user, "finance:manage", db)
        or has_permission(user, "finance.manage", db)
    )


def _can_manage_finance(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.FINANCE)
        or has_permission(user, "finance:manage", db)
        or has_permission(user, "finance.manage", db)
    )


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=FinanceDashboardMetrics)
def get_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return get_finance_dashboard_metrics(db, tenant_id)


# ---------------------------------------------------------------------------
# 2. Financial Dimensions
# ---------------------------------------------------------------------------

@router.get("/dimensions", response_model=List[FinancialDimensionResponse])
def list_dimensions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    dimensions = db.query(FinancialDimension).filter(FinancialDimension.tenant_id == tenant_id).all()
    resp = []
    for d in dimensions:
        r = FinancialDimensionResponse.from_orm(d)
        r.values = [FinancialDimensionValueResponse.from_orm(v) for v in d.values]
        resp.append(r)
    return resp


@router.post("/dimensions", response_model=FinancialDimensionResponse, status_code=status.HTTP_201_CREATED)
def create_dimension(
    payload: FinancialDimensionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    dim = FinancialDimension(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        dimension_type=payload.dimension_type,
        description=payload.description,
        active=payload.active,
    )
    db.add(dim)
    db.commit()
    db.refresh(dim)
    return dim


@router.post("/dimensions/{dimension_id}/values", response_model=FinancialDimensionValueResponse, status_code=status.HTTP_201_CREATED)
def create_dimension_value(
    dimension_id: str,
    payload: FinancialDimensionValueCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    dim = db.query(FinancialDimension).filter(
        FinancialDimension.id == dimension_id,
        FinancialDimension.tenant_id == tenant_id
    ).first()
    if not dim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial dimension not found")

    val = FinancialDimensionValue(
        tenant_id=tenant_id,
        dimension_id=dimension_id,
        code=payload.code,
        name=payload.name,
        parent_id=payload.parent_id,
        active=payload.active,
    )
    db.add(val)
    db.commit()
    db.refresh(val)
    return val


# ---------------------------------------------------------------------------
# 3. Cost Centers
# ---------------------------------------------------------------------------

@router.get("/cost-centers", response_model=List[CostCenterResponse])
def list_cost_centers(
    request: Request,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(CostCenter).filter(CostCenter.tenant_id == tenant_id)
    if active_only:
        query = query.filter(CostCenter.active.is_(True))
    return query.order_by(CostCenter.code.asc()).all()


@router.post("/cost-centers", response_model=CostCenterResponse, status_code=status.HTTP_201_CREATED)
def create_cost_center(
    payload: CostCenterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:cost_centers:manage", db)
        or has_permission(current_user, "finance.cost_centers.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cost center manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Check unique code within tenant
    existing = db.query(CostCenter).filter(CostCenter.tenant_id == tenant_id, CostCenter.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cost center code '{payload.code}' already exists")

    cc = CostCenter(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        legal_entity_id=payload.legal_entity_id,
        manager_person_id=payload.manager_person_id,
        parent_cost_center_id=payload.parent_cost_center_id,
        currency=payload.currency,
        active=payload.active,
        effective_from=payload.effective_from or date.today(),
        effective_to=payload.effective_to,
    )
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc


@router.get("/cost-centers/{cost_center_id}", response_model=CostCenterResponse)
def get_cost_center(
    cost_center_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cc = db.query(CostCenter).filter(CostCenter.id == cost_center_id, CostCenter.tenant_id == tenant_id).first()
    if not cc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")
    return cc


@router.put("/cost-centers/{cost_center_id}", response_model=CostCenterResponse)
def update_cost_center(
    cost_center_id: str,
    payload: CostCenterUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:cost_centers:manage", db)
        or has_permission(current_user, "finance.cost_centers.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cost center manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cc = db.query(CostCenter).filter(CostCenter.id == cost_center_id, CostCenter.tenant_id == tenant_id).first()
    if not cc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(cc, k, v)

    db.commit()
    db.refresh(cc)
    return cc


# ---------------------------------------------------------------------------
# 4. Employee Cost Allocation
# ---------------------------------------------------------------------------

@router.get("/cost-allocations", response_model=List[EmployeeCostAllocationResponse])
@router.get("/employee-allocations", response_model=List[EmployeeCostAllocationResponse])
def list_cost_allocations(
    request: Request,
    person_id: Optional[str] = None,
    cost_center_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(EmployeeCostAllocation).filter(EmployeeCostAllocation.tenant_id == tenant_id)
    if person_id:
        query = query.filter(EmployeeCostAllocation.person_id == person_id)
    if cost_center_id:
        query = query.filter(EmployeeCostAllocation.cost_center_id == cost_center_id)

    allocs = query.all()
    resp = []
    for a in allocs:
        r = EmployeeCostAllocationResponse.from_orm(a)
        cc = db.query(CostCenter).filter(CostCenter.id == a.cost_center_id).first()
        if cc:
            r.cost_center_code = cc.code
            r.cost_center_name = cc.name
        resp.append(r)
    return resp


@router.post("/cost-allocations", response_model=EmployeeCostAllocationResponse, status_code=status.HTTP_201_CREATED)
@router.post("/employee-allocations", response_model=EmployeeCostAllocationResponse, status_code=status.HTTP_201_CREATED)
def create_cost_allocation(
    payload: EmployeeCostAllocationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Validate that person exists
    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    # Validate that cost center exists
    cc = db.query(CostCenter).filter(CostCenter.id == payload.cost_center_id, CostCenter.tenant_id == tenant_id).first()
    if not cc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")

    # Enforce allocation sum <= 100%
    try:
        validate_employee_allocations(
            db=db,
            tenant_id=tenant_id,
            person_id=payload.person_id,
            effective_from=payload.effective_from,
            new_percentage=payload.percentage
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    alloc = EmployeeCostAllocation(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        engagement_id=payload.engagement_id,
        cost_center_id=payload.cost_center_id,
        percentage=payload.percentage,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        allocation_type=payload.allocation_type,
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)

    r = EmployeeCostAllocationResponse.from_orm(alloc)
    r.cost_center_code = cc.code
    r.cost_center_name = cc.name
    return r


# ---------------------------------------------------------------------------
# 5. GL Accounts & Mappings
# ---------------------------------------------------------------------------

@router.get("/gl-accounts", response_model=List[GLAccountResponse])
def list_gl_accounts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    accounts = db.query(GLAccount).filter(GLAccount.tenant_id == tenant_id).order_by(GLAccount.code.asc()).all()
    resp = []
    for a in accounts:
        r = GLAccountResponse.from_orm(a)
        r.account_code = a.code
        r.account_name = a.name
        resp.append(r)
    return resp


@router.post("/gl-accounts", response_model=GLAccountResponse, status_code=status.HTTP_201_CREATED)
def create_gl_account(
    payload: GLAccountCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:gl:manage", db)
        or has_permission(current_user, "finance.gl.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GL manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    code = payload.code or payload.account_code or "DEFAULT"
    name = payload.name or payload.account_name or "General Ledger Account"

    existing = db.query(GLAccount).filter(GLAccount.tenant_id == tenant_id, GLAccount.code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GL Account code '{code}' already exists")

    acct = GLAccount(
        tenant_id=tenant_id,
        code=code,
        name=name,
        account_type=payload.account_type,
        description=payload.description,
        active=payload.active,
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    r = GLAccountResponse.from_orm(acct)
    r.account_code = acct.code
    r.account_name = acct.name
    return r


@router.get("/gl-mappings", response_model=List[GLMappingResponse])
def list_gl_mappings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    mappings = db.query(GLMapping).filter(GLMapping.tenant_id == tenant_id).all()
    resp = []
    for m in mappings:
        r = GLMappingResponse.from_orm(m)
        if m.debit_account:
            r.debit_account_code = m.debit_account.code
        if m.credit_account:
            r.credit_account_code = m.credit_account.code
        resp.append(r)
    return resp


@router.post("/gl-mappings", response_model=GLMappingResponse, status_code=status.HTTP_201_CREATED)
def create_gl_mapping(
    payload: GLMappingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:gl:manage", db)
        or has_permission(current_user, "finance.gl.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GL manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    m = GLMapping(
        tenant_id=tenant_id,
        transaction_type=payload.transaction_type,
        source_type=payload.source_type,
        source_code=payload.source_code,
        debit_account_id=payload.debit_account_id,
        credit_account_id=payload.credit_account_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        active=payload.active,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ---------------------------------------------------------------------------
# 6. Payroll Accounting Journals
# ---------------------------------------------------------------------------

@router.get("/payroll-journals", response_model=List[PayrollJournalResponse])
def list_payroll_journals(
    request: Request,
    status_filter: Optional[str] = None,
    payroll_run_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(PayrollJournal).filter(PayrollJournal.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(PayrollJournal.status == status_filter)
    if payroll_run_id:
        query = query.filter(PayrollJournal.payroll_run_id == payroll_run_id)

    journals = query.order_by(PayrollJournal.created_at.desc()).all()
    resp = []
    for j in journals:
        r = PayrollJournalResponse.from_orm(j)
        r.lines = [PayrollJournalLineResponse.from_orm(l) for l in j.lines]
        resp.append(r)
    return resp


@router.post("/payroll-journals/generate", response_model=PayrollJournalResponse, status_code=status.HTTP_201_CREATED)
def trigger_journal_generation(
    payload: JournalGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:payroll_journal:manage", db)
        or has_permission(current_user, "finance.payroll_journal.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Journal manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    try:
        journal = generate_payroll_journal(
            db=db,
            tenant_id=tenant_id,
            payroll_run_id=payload.payroll_run_id,
            accounting_date=payload.accounting_date,
            user_id=current_user.id
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    r = PayrollJournalResponse.from_orm(journal)
    r.lines = [PayrollJournalLineResponse.from_orm(l) for l in journal.lines]
    return r


@router.get("/payroll-journals/{journal_id}", response_model=PayrollJournalResponse)
def get_payroll_journal(
    journal_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    j = db.query(PayrollJournal).filter(PayrollJournal.id == journal_id, PayrollJournal.tenant_id == tenant_id).first()
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")

    r = PayrollJournalResponse.from_orm(j)
    r.lines = [PayrollJournalLineResponse.from_orm(l) for l in j.lines]
    return r


@router.post("/payroll-journals/{journal_id}/approve", response_model=PayrollJournalResponse)
def approve_payroll_journal(
    journal_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:payroll_journal:manage", db)
        or has_permission(current_user, "finance.payroll_journal.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Journal manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    j = db.query(PayrollJournal).filter(PayrollJournal.id == journal_id, PayrollJournal.tenant_id == tenant_id).first()
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")

    if j.status == PayrollJournalStatus.POSTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Posted journals are immutable")

    j.status = PayrollJournalStatus.APPROVED.value
    db.commit()
    db.refresh(j)

    r = PayrollJournalResponse.from_orm(j)
    r.lines = [PayrollJournalLineResponse.from_orm(l) for l in j.lines]
    return r


@router.post("/payroll-journals/{journal_id}/post", response_model=PayrollJournalResponse)
def post_journal_to_gl(
    journal_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:payroll_journal:manage", db)
        or has_permission(current_user, "finance.payroll_journal.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Journal manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    try:
        j = post_payroll_journal(
            db=db,
            tenant_id=tenant_id,
            journal_id=journal_id,
            user_id=current_user.id
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    r = PayrollJournalResponse.from_orm(j)
    r.lines = [PayrollJournalLineResponse.from_orm(l) for l in j.lines]
    return r


@router.post("/payroll-journals/{journal_id}/reverse")
def reverse_journal(
    journal_id: str,
    request: Request,
    payload: Optional[Dict[str, Any]] = None,
    reversal_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:payroll_journal:manage", db)
        or has_permission(current_user, "finance.payroll_journal.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Journal manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    reason = reversal_reason or (payload.get("reason") if payload else None)
    try:
        reversal = reverse_payroll_journal(
            db=db,
            tenant_id=tenant_id,
            journal_id=journal_id,
            user_id=current_user.id,
            reversal_reason=reason
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    return {
        "id": reversal.id,
        "original_journal_id": journal_id,
        "reversal_journal_id": reversal.id,
        "reversal_journal_number": reversal.journal_number,
        "journal_number": reversal.journal_number,
        "status": reversal.status,
        "total_debit": float(reversal.total_debit),
        "total_credit": float(reversal.total_credit),
    }


# ---------------------------------------------------------------------------
# 7. Normalized Workforce Cost Records
# ---------------------------------------------------------------------------

@router.get("/workforce-cost", response_model=List[WorkforceCostRecordResponse])
@router.get("/workforce-costs", response_model=List[WorkforceCostRecordResponse])
def list_workforce_costs(
    request: Request,
    payroll_run_id: Optional[str] = None,
    cost_center_id: Optional[str] = None,
    period_key: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(WorkforceCostRecord).filter(WorkforceCostRecord.tenant_id == tenant_id)
    if payroll_run_id:
        query = query.filter(WorkforceCostRecord.payroll_run_id == payroll_run_id)
    if cost_center_id:
        query = query.filter(WorkforceCostRecord.cost_center_id == cost_center_id)

    records = query.all()
    resp = []
    for rec in records:
        r = WorkforceCostRecordResponse.from_orm(rec)
        p = db.query(Person).filter(Person.id == rec.person_id).first()
        if p:
            r.person_name = p.full_name
        cc = db.query(CostCenter).filter(CostCenter.id == rec.cost_center_id).first() if rec.cost_center_id else None
        if cc:
            r.cost_center_code = cc.code
        r.period_key = period_key or rec.period_start.strftime("%Y-%m")
        r.base_salary_amount = float(rec.base_salary)
        r.bonus_amount = float(rec.bonus)
        r.employer_statutory_amount = float(rec.employer_statutory_cost)
        r.benefits_amount = float(rec.benefits_cost)
        r.expense_reimbursements_amount = float(rec.reimbursement_cost)
        resp.append(r)
    return resp


@router.post("/workforce-cost/calculate", response_model=List[WorkforceCostRecordResponse])
@router.post("/workforce-costs/calculate-from-payroll", response_model=List[WorkforceCostRecordResponse])
def trigger_workforce_cost_calculation(
    request: Request,
    payload: Optional[WorkforceCostCalculateRequest] = None,
    payroll_run_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    p_run_id = payroll_run_id or (payload.payroll_run_id if payload else None)
    records = calculate_workforce_cost_records(
        db=db,
        tenant_id=tenant_id,
        payroll_run_id=p_run_id
    )

    resp = []
    for rec in records:
        r = WorkforceCostRecordResponse.from_orm(rec)
        p = db.query(Person).filter(Person.id == rec.person_id).first()
        if p:
            r.person_name = p.full_name
        cc = db.query(CostCenter).filter(CostCenter.id == rec.cost_center_id).first() if rec.cost_center_id else None
        if cc:
            r.cost_center_code = cc.code
        r.period_key = rec.period_start.strftime("%Y-%m")
        r.base_salary_amount = float(rec.base_salary)
        r.bonus_amount = float(rec.bonus)
        r.employer_statutory_amount = float(rec.employer_statutory_cost)
        r.benefits_amount = float(rec.benefits_cost)
        r.expense_reimbursements_amount = float(rec.reimbursement_cost)
        resp.append(r)
    return resp


# ---------------------------------------------------------------------------
# 8. Accruals & Provisions
# ---------------------------------------------------------------------------

@router.get("/accruals/rules", response_model=List[AccrualRuleResponse])
def list_accrual_rules(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    rules = db.query(AccrualRule).filter(AccrualRule.tenant_id == tenant_id).all()
    resp = []
    for r in rules:
        resp_rule = AccrualRuleResponse.from_orm(r)
        resp_rule.records = [AccrualRecordResponse.from_orm(rec) for rec in r.records]
        resp.append(resp_rule)
    return resp


@router.post("/accruals/rules", response_model=AccrualRuleResponse, status_code=status.HTTP_201_CREATED)
def create_accrual_rule(
    payload: AccrualRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:accrual:manage", db)
        or has_permission(current_user, "finance.accrual.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accrual manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    rule = AccrualRule(
        tenant_id=tenant_id,
        name=payload.name,
        accrual_type=payload.accrual_type,
        calculation_method=payload.calculation_method,
        frequency=payload.frequency,
        account_id=payload.account_id,
        cost_center_id=payload.cost_center_id,
        active=payload.active,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# 9. Workforce Budgeting & Budget vs Actual
# ---------------------------------------------------------------------------

@router.get("/budgets", response_model=List[WorkforceBudgetResponse])
def list_budgets(
    request: Request,
    fiscal_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(WorkforceBudget).filter(WorkforceBudget.tenant_id == tenant_id)
    if fiscal_year:
        query = query.filter(WorkforceBudget.fiscal_year == fiscal_year)

    budgets = query.all()
    resp = []
    for b in budgets:
        r = WorkforceBudgetResponse.from_orm(b)
        r.lines = [WorkforceBudgetLineResponse.from_orm(l) for l in b.lines]
        resp.append(r)
    return resp


@router.post("/budgets", response_model=WorkforceBudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: WorkforceBudgetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:budget:manage", db)
        or has_permission(current_user, "finance.budget.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    total_sum = sum(float(l.budget_amount) for l in payload.lines) or float(payload.total_budget)

    budget = WorkforceBudget(
        tenant_id=tenant_id,
        name=payload.name,
        fiscal_year=payload.fiscal_year,
        legal_entity_id=payload.legal_entity_id,
        currency=payload.currency,
        status=BudgetStatus.DRAFT.value,
        total_budget=total_sum,
        created_by=current_user.id,
    )
    db.add(budget)
    db.flush()

    for l in payload.lines:
        line = WorkforceBudgetLine(
            tenant_id=tenant_id,
            budget_id=budget.id,
            cost_center_id=l.cost_center_id,
            department_id=l.department_id,
            category=l.category,
            month=l.month,
            budget_amount=l.budget_amount,
        )
        db.add(line)

    db.commit()
    db.refresh(budget)

    r = WorkforceBudgetResponse.from_orm(budget)
    r.lines = [WorkforceBudgetLineResponse.from_orm(line) for line in budget.lines]
    return r


@router.get("/budgets/{budget_id}", response_model=WorkforceBudgetResponse)
def get_budget(
    budget_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    b = db.query(WorkforceBudget).filter(WorkforceBudget.id == budget_id, WorkforceBudget.tenant_id == tenant_id).first()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    r = WorkforceBudgetResponse.from_orm(b)
    r.lines = [WorkforceBudgetLineResponse.from_orm(l) for l in b.lines]
    return r


@router.post("/budgets/{budget_id}/approve", response_model=WorkforceBudgetResponse)
def approve_budget(
    budget_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:budget:manage", db)
        or has_permission(current_user, "finance.budget.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    b = db.query(WorkforceBudget).filter(WorkforceBudget.id == budget_id, WorkforceBudget.tenant_id == tenant_id).first()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    b.status = BudgetStatus.APPROVED.value
    b.approved_by = current_user.id
    b.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(b)

    r = WorkforceBudgetResponse.from_orm(b)
    r.lines = [WorkforceBudgetLineResponse.from_orm(l) for l in b.lines]
    return r


@router.get("/budget-vs-actual", response_model=BudgetVsActualResponse)
def get_budget_vs_actual(
    request: Request,
    fiscal_year: Optional[str] = None,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return calculate_budget_vs_actual(db, tenant_id, fiscal_year, month)


@router.get("/budgets/{budget_id}/variance")
def get_budget_variance(
    budget_id: str,
    request: Request,
    period_key: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    b = db.query(WorkforceBudget).filter(WorkforceBudget.id == budget_id, WorkforceBudget.tenant_id == tenant_id).first()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    res = calculate_budget_vs_actual(db, tenant_id, b.fiscal_year, period_key)
    return {
        "budget_id": b.id,
        "fiscal_year": b.fiscal_year,
        "period_key": period_key,
        "total_budget": res.get("total_budget", 0.0),
        "total_actual": res.get("total_actual", 0.0),
        "total_variance": res.get("total_variance", 0.0),
        "total_variance_percentage": res.get("total_variance_percentage", 0.0),
        "cost_center_variances": res.get("breakdown", []),
    }


# ---------------------------------------------------------------------------
# 10. Payroll Variance Analysis
# ---------------------------------------------------------------------------

@router.get("/payroll-variance")
def get_payroll_variance(
    request: Request,
    previous_payroll_id: Optional[str] = None,
    current_payroll_id: Optional[str] = None,
    prior_period: Optional[str] = None,
    current_period: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    try:
        return analyze_payroll_variance(
            db=db,
            tenant_id=tenant_id,
            previous_payroll_id=previous_payroll_id,
            current_payroll_id=current_payroll_id,
            prior_period=prior_period,
            current_period=current_period,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ---------------------------------------------------------------------------
# 11. Vendors & Invoices
# ---------------------------------------------------------------------------

@router.get("/vendors", response_model=List[VendorResponse])
def list_vendors(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    vendors = db.query(Vendor).filter(Vendor.tenant_id == tenant_id).all()
    resp = []
    for v in vendors:
        r = VendorResponse.from_orm(v)
        r.contracts = [VendorContractResponse.from_orm(c) for c in v.contracts]
        r.invoices = [VendorInvoiceResponse.from_orm(i) for i in v.invoices]
        resp.append(r)
    return resp


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:vendor:manage", db)
        or has_permission(current_user, "finance.vendor.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    v = Vendor(
        tenant_id=tenant_id,
        vendor_code=payload.vendor_code or f"V-{uuid.uuid4().hex[:6].upper()}",
        name=payload.name,
        category=payload.category,
        tax_identifier=payload.tax_identifier,
        contact_reference=payload.contact_reference,
        legal_entity_id=payload.legal_entity_id,
        currency=payload.currency,
        active=payload.active,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.post("/vendors/{vendor_id}/contracts", response_model=VendorContractResponse, status_code=status.HTTP_201_CREATED)
def create_vendor_contract(
    vendor_id: str,
    payload: VendorContractCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:vendor:manage", db)
        or has_permission(current_user, "finance.vendor.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    contract = VendorContract(
        tenant_id=tenant_id,
        vendor_id=vendor_id,
        contract_reference=payload.contract_reference,
        start_date=payload.start_date,
        end_date=payload.end_date,
        recurring_amount=payload.recurring_amount,
        currency=payload.currency,
        payment_frequency=payload.payment_frequency,
        cost_center_id=payload.cost_center_id,
        status=payload.status,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/invoices", response_model=List[VendorInvoiceResponse])
def list_invoices(
    request: Request,
    vendor_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(VendorInvoice).filter(VendorInvoice.tenant_id == tenant_id)
    if vendor_id:
        query = query.filter(VendorInvoice.vendor_id == vendor_id)
    if status_filter:
        query = query.filter(VendorInvoice.status == status_filter)

    invoices = query.order_by(VendorInvoice.invoice_date.desc()).all()
    resp = []
    for inv in invoices:
        r = VendorInvoiceResponse.from_orm(inv)
        if inv.vendor:
            r.vendor_name = inv.vendor.name
        resp.append(r)
    return resp


@router.post("/invoices", response_model=VendorInvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: VendorInvoiceCreate,
    request: Request,
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:invoice:manage", db)
        or has_permission(current_user, "finance.invoice.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invoice manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    v_id = vendor_id or payload.vendor_id
    if not v_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="vendor_id is required")

    vendor = db.query(Vendor).filter(Vendor.id == v_id, Vendor.tenant_id == tenant_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    inv = VendorInvoice(
        tenant_id=tenant_id,
        vendor_id=v_id,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        amount=payload.amount,
        tax_amount=payload.tax_amount,
        total_amount=payload.total_amount,
        currency=payload.currency,
        cost_center_id=payload.cost_center_id,
        status=InvoiceStatus.SUBMITTED.value,
        external_reference=payload.external_reference,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    r = VendorInvoiceResponse.from_orm(inv)
    r.vendor_name = vendor.name
    return r


@router.post("/invoices/{invoice_id}/approve", response_model=VendorInvoiceResponse)
def approve_invoice(
    invoice_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:invoice:manage", db)
        or has_permission(current_user, "finance.invoice.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invoice manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    inv = db.query(VendorInvoice).filter(VendorInvoice.id == invoice_id, VendorInvoice.tenant_id == tenant_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    inv.status = InvoiceStatus.APPROVED.value
    db.commit()
    db.refresh(inv)

    r = VendorInvoiceResponse.from_orm(inv)
    if inv.vendor:
        r.vendor_name = inv.vendor.name
    return r


@router.post("/invoices/{invoice_id}/pay", response_model=VendorInvoiceResponse)
def pay_invoice(
    invoice_id: str,
    request: Request,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:invoice:manage", db)
        or has_permission(current_user, "finance.invoice.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invoice manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    inv = db.query(VendorInvoice).filter(VendorInvoice.id == invoice_id, VendorInvoice.tenant_id == tenant_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    inv.status = InvoiceStatus.PAID.value
    if payload and "payment_reference" in payload:
        inv.external_reference = payload["payment_reference"]
    db.commit()
    db.refresh(inv)

    r = VendorInvoiceResponse.from_orm(inv)
    if payload and "payment_reference" in payload:
        r.payment_reference = payload["payment_reference"]
    if inv.vendor:
        r.vendor_name = inv.vendor.name
    return r


@router.post("/expense-entries", status_code=status.HTTP_201_CREATED)
def create_expense_entry(
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_finance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    t_date = date.today()
    if "transaction_date" in payload and payload["transaction_date"]:
        try:
            t_date = datetime.strptime(payload["transaction_date"], "%Y-%m-%d").date()
        except Exception:
            pass
    ref_id = payload.get("source_reference_id") or payload.get("expense_claim_id") or "EXP-DEFAULT"
    entry = ExpenseAccountingEntry(
        tenant_id=tenant_id,
        expense_claim_id=ref_id,
        source_type=payload.get("source_type", "REIMBURSEMENT"),
        source_reference_id=ref_id,
        cost_center_id=payload.get("cost_center_id"),
        gl_account_id=payload.get("gl_account_id"),
        amount=payload.get("amount", 0.0),
        currency=payload.get("currency", "INR"),
        accounting_date=t_date,
        status=payload.get("status", "POSTED"),
        description=payload.get("description"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "id": entry.id,
        "source_type": entry.source_type,
        "source_reference_id": entry.source_reference_id,
        "amount": float(entry.amount),
        "status": entry.status,
    }


# ---------------------------------------------------------------------------
# 12. Accounting Export
# ---------------------------------------------------------------------------

@router.get("/payroll-journals/{journal_id}/export")
def export_single_payroll_journal(
    journal_id: str,
    export_format: str = Query("CSV"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:accounting_export", db)
        or has_permission(current_user, "finance.accounting_export", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accounting export permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    j = db.query(PayrollJournal).filter(PayrollJournal.id == journal_id, PayrollJournal.tenant_id == tenant_id).first()
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")

    if export_format.upper() == "CSV":
        lines = ["journal_number,posting_date,account_code,debit,credit,description"]
        for l in j.lines:
            acct_code = l.account.code if l.account else (l.account_id or "")
            lines.append(f"{j.journal_number},{j.accounting_date},{acct_code},{l.debit},{l.credit},\"{l.description or ''}\"")
        return {"journal_id": j.id, "export_format": "CSV", "csv_data": "\n".join(lines)}
    else:
        r = PayrollJournalResponse.from_orm(j)
        r.lines = [PayrollJournalLineResponse.from_orm(l) for l in j.lines]
        return r.dict()

@router.post("/accounting/export", response_model=AccountingExportResponse)
def export_accounting_journals(
    payload: AccountingExportRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_finance(current_user, db)
        or has_permission(current_user, "finance:accounting_export", db)
        or has_permission(current_user, "finance.accounting_export", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accounting export permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    return generate_accounting_export(
        db=db,
        tenant_id=tenant_id,
        journal_ids=payload.journal_ids,
        period_start=payload.period_start,
        period_end=payload.period_end,
        export_format=payload.export_format,
    )
