"""Phase 6 – Payroll engine: components, salary structures, payroll runs, payslips."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v6 import (
    PayrollComponent, SalaryStructure, PayrollRun, Payslip,
    ComponentType, PayrollRunStatus,
)

router = APIRouter(prefix="/api/payroll", tags=["payroll"])


# ── Schemas ──────────────────────────────────────────────────────────────

class ComponentCreate(BaseModel):
    name: str
    code: str
    component_type: ComponentType
    is_taxable: bool = True
    is_statutory: bool = False
    calculation_type: str = "fixed"
    percentage_of: Optional[str] = None
    default_value: float = 0

class ComponentOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    name: str
    code: str
    component_type: ComponentType
    is_taxable: bool
    is_statutory: bool
    is_active: bool

class SalaryCreate(BaseModel):
    person_id: str
    name: str
    effective_from: date
    ctc_annual: float
    ctc_monthly: float
    components_json: list[dict]  # [{"code":"BASIC","amount":50000}]
    currency: str = "INR"

class SalaryOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    name: str
    ctc_annual: float
    ctc_monthly: float
    components_json: list[dict]
    is_active: bool

class PayrollRunCreate(BaseModel):
    month: str  # "2026-09"

class PayrollRunOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    month: str
    status: PayrollRunStatus
    total_gross: Optional[float]
    total_deductions: Optional[float]
    total_net: Optional[float]
    employee_count: int

class PayslipOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    month: str
    gross_salary: float
    total_deductions: float
    net_salary: float


# ── Payroll Components ──────────────────────────────────────────────────

@router.post("/components", response_model=ComponentOut, status_code=201)
def create_component(
    payload: ComponentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    comp = PayrollComponent(**payload.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    log_audit(db, user=current_user, action="payroll_component_created", entity="payroll_component",
              entity_id=comp.id, result=AuditResult.SUCCESS, request=request)
    return comp


@router.get("/components", response_model=list[ComponentOut])
def list_components(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:view")),
):
    return db.query(PayrollComponent).filter(PayrollComponent.is_active == True).all()


# ── Salary Structures ──────────────────────────────────────────────────

@router.post("/salary-structures", response_model=SalaryOut, status_code=201)
def create_salary_structure(
    payload: SalaryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    ss = SalaryStructure(**payload.model_dump())
    db.add(ss)
    db.commit()
    db.refresh(ss)
    return ss


@router.get("/salary-structures/{person_id}", response_model=list[SalaryOut])
def get_salary_structures(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:view")),
):
    return db.query(SalaryStructure).filter(
        SalaryStructure.person_id == person_id,
        SalaryStructure.is_active == True,
    ).all()


# ── Payroll Runs ────────────────────────────────────────────────────────

@router.post("/runs", response_model=PayrollRunOut, status_code=201)
def create_payroll_run(
    payload: PayrollRunCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    run = PayrollRun(month=payload.month, processed_by_id=current_user.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.post("/runs/{run_id}/compute")
def compute_payroll(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    """Auto-compute payslips from active salary structures."""
    run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")

    structures = db.query(SalaryStructure).filter(SalaryStructure.is_active == True).all()
    total_gross = 0
    total_deductions = 0
    count = 0

    for ss in structures:
        earnings = [c for c in (ss.components_json or []) if c.get("type") != "deduction"]
        deductions = [c for c in (ss.components_json or []) if c.get("type") == "deduction"]
        gross = sum(c.get("amount", 0) for c in earnings) or float(ss.ctc_monthly)
        ded = sum(c.get("amount", 0) for c in deductions)
        net = gross - ded

        slip = Payslip(
            payroll_run_id=run_id,
            person_id=ss.person_id,
            month=run.month,
            gross_salary=gross,
            total_deductions=ded,
            net_salary=net,
            earnings_json=earnings,
            deductions_json=deductions,
        )
        db.add(slip)
        total_gross += gross
        total_deductions += ded
        count += 1

    run.total_gross = total_gross
    run.total_deductions = total_deductions
    run.total_net = total_gross - total_deductions
    run.employee_count = count
    run.status = PayrollRunStatus.COMPUTED
    db.commit()
    log_audit(db, user=current_user, action="payroll_computed", entity="payroll_run",
              entity_id=run_id, result=AuditResult.SUCCESS, request=request,
              metadata={"employees": count})
    return {
        "id": run_id, "status": "computed",
        "employees": count, "total_net": float(run.total_net)
    }


@router.get("/runs/{run_id}/payslips", response_model=list[PayslipOut])
def get_payslips(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:view")),
):
    return db.query(Payslip).filter(Payslip.payroll_run_id == run_id).all()


@router.patch("/runs/{run_id}/approve")
def approve_payroll_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")
    if run.status != PayrollRunStatus.COMPUTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Run must be computed before approval")
    run.status = PayrollRunStatus.APPROVED
    run.approved_by_id = current_user.id
    db.commit()
    return {"id": run_id, "status": "approved"}
