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
from app.models_compensation import BonusIncentive


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
        earnings = [dict(c) for c in (ss.components_json or []) if c.get("type") != "deduction"]
        deductions = [dict(c) for c in (ss.components_json or []) if c.get("type") == "deduction"]
        gross = sum(c.get("amount", 0) for c in earnings) or float(ss.ctc_monthly)
        ded = sum(c.get("amount", 0) for c in deductions)

        # Integrate approved bonuses for this pay period
        approved_bonuses = db.query(BonusIncentive).filter(
            BonusIncentive.person_id == ss.person_id,
            BonusIncentive.status == "approved",
            BonusIncentive.pay_period == run.month,
            BonusIncentive.payroll_status == "pending",
        ).all()
        for b in approved_bonuses:
            b_amount = float(b.amount)
            earnings.append({"code": "BONUS", "name": f"Bonus ({b.bonus_type})", "amount": b_amount, "type": "earning"})
            gross += b_amount
            b.payroll_status = "processed"

        # Module 12: India Statutory Deductions & Calculation Snapshots
        try:
            from app.models_statutory import (
                StatutoryPeriod,
                StatutoryCalculation,
                StatutoryContribution,
                StatutoryRule,
                StatutoryScheme,
            )
            from app.models_v3 import Tenant, LegalEntity
            from app.adapters.india_statutory_adapter import (
                EPFAdapter,
                ESIAdapter,
                ProfessionalTaxAdapter,
                TDSAdapter,
            )

            tenant = db.query(Tenant).first()
            tenant_id = tenant.id if tenant else "default_tenant"
            le = db.query(LegalEntity).filter(LegalEntity.tenant_id == tenant_id).first()
            if not le:
                le = LegalEntity(tenant_id=tenant_id, name="Primary Legal Entity", country_code="IN", default_currency="INR")
                db.add(le)
                db.flush()

            y, m = [int(x) for x in run.month.split("-")]
            import calendar
            _, last_day = calendar.monthrange(y, m)
            run_date = date(y, m, last_day)

            stat_rules = db.query(StatutoryRule).filter(
                StatutoryRule.tenant_id == tenant_id,
                StatutoryRule.is_active == True,
                StatutoryRule.effective_from <= run_date,
                (StatutoryRule.effective_to == None) | (StatutoryRule.effective_to >= run_date),
            ).all()

            if stat_rules:
                stat_period = db.query(StatutoryPeriod).filter(StatutoryPeriod.payroll_run_id == run_id).first()
                if not stat_period:
                    stat_period = StatutoryPeriod(
                        tenant_id=tenant_id,
                        legal_entity_id=le.id,
                        start_date=date(y, m, 1),
                        end_date=run_date,
                        payroll_run_id=run_id,
                    )
                    db.add(stat_period)
                    db.flush()

                basic_wage = 0.0
                for c in earnings:
                    if str(c.get("code", "")).upper() in ("BASIC", "BASE"):
                        basic_wage = float(c.get("amount", 0.0))
                        break
                if basic_wage == 0.0:
                    basic_wage = float(gross) * 0.4 if gross > 0 else 15000.0

                schemes_calculated = set()
                for r in stat_rules:
                    if r.scheme in schemes_calculated:
                        continue
                    schemes_calculated.add(r.scheme)

                    res = None
                    if r.scheme == StatutoryScheme.EPF:
                        res = EPFAdapter(db).calculate(ss.person_id, run_date, basic_wage, gross, tenant_id=tenant_id)
                    elif r.scheme == StatutoryScheme.ESI:
                        res = ESIAdapter(db).calculate(ss.person_id, run_date, gross, tenant_id=tenant_id)
                    elif r.scheme == StatutoryScheme.PROFESSIONAL_TAX:
                        res = ProfessionalTaxAdapter(db).calculate(ss.person_id, run_date, gross, state=r.state or "Karnataka", tenant_id=tenant_id)
                    elif r.scheme == StatutoryScheme.TDS:
                        res = TDSAdapter(db).calculate(ss.person_id, run_date, gross, annual_ctc=float(ss.ctc_annual), tenant_id=tenant_id)

                    if res and res.get("employee_deduction", 0) > 0:
                        ded_amt = float(res["employee_deduction"])
                        deductions.append({
                            "code": r.scheme.value.upper(),
                            "name": f"Statutory {r.scheme.value.upper()}",
                            "amount": ded_amt,
                            "type": "deduction",
                            "statutory": True,
                        })
                        ded += ded_amt

                        calc = StatutoryCalculation(
                            period_id=stat_period.id,
                            rule_id=r.id,
                            person_id=ss.person_id,
                            amount=ded_amt,
                            result_snapshot=res,
                            rule_version=res.get("rule_version", str(r.id)),
                        )
                        db.add(calc)
                        db.flush()

                        if res.get("employer_contribution", 0) > 0:
                            contrib = StatutoryContribution(
                                calculation_id=calc.id,
                                contribution_type="employer",
                                amount=float(res["employer_contribution"]),
                            )
                            db.add(contrib)
        except Exception:
            pass

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
