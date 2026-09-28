"""
global_payroll.py - Module 21: Global Payroll & Multi-Country Workforce Platform Router
Prefix: /api/v3/global-payroll
Zeramai Enterprise HRMS
"""
from typing import List, Optional, Any, Dict
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.database import get_db
from app.deps import get_current_user, require_permission
from app.models import User, Person, Engagement, Tenant, LegalEntity
from app.models_global_payroll import (
    PayrollCountry,
    GlobalPayrollConfiguration,
    PayrollPayGroup,
    PayrollCalendar,
    GlobalPayComponent,
    PayrollInput,
    CountryPayrollRule,
    GlobalPayrollResult,
    PayrollResultComponent,
    PayrollExchangeRate,
    EmployeePayrollAssignment,
    PayrollAdjustment,
    PayrollReconciliation,
    GlobalPayslipRecord,
    CountryPayrollStatus,
    PayrollCalendarStatus,
    GlobalPayComponentType,
    GlobalPayrollResultStatus,
    AssignmentPayrollStatus,
    PayrollAdjustmentStatus,
    PayrollReconciliationStatus,
    GlobalPayslipStatus,
)
from app.schemas_global_payroll import (
    PayrollCountryCreate,
    PayrollCountryUpdate,
    PayrollCountryResponse,
    GlobalPayrollConfigurationCreate,
    GlobalPayrollConfigurationUpdate,
    GlobalPayrollConfigurationResponse,
    PayrollPayGroupCreate,
    PayrollPayGroupUpdate,
    PayrollPayGroupResponse,
    PayrollCalendarCreate,
    PayrollCalendarUpdate,
    PayrollCalendarResponse,
    GlobalPayComponentCreate,
    GlobalPayComponentUpdate,
    GlobalPayComponentResponse,
    PayrollInputCreate,
    PayrollInputUpdate,
    PayrollInputResponse,
    CountryPayrollRuleCreate,
    CountryPayrollRuleUpdate,
    CountryPayrollRuleResponse,
    EmployeePayrollAssignmentCreate,
    EmployeePayrollAssignmentUpdate,
    EmployeePayrollAssignmentResponse,
    PayrollExchangeRateCreate,
    PayrollExchangeRateResponse,
    PayrollResultComponentResponse,
    GlobalPayrollResultResponse,
    CalculatePayrollRequest,
    PayrollRunSummaryResponse,
    PayrollAdjustmentCreate,
    PayrollAdjustmentResponse,
    PayrollReconciliationResponse,
    GlobalPayslipRecordResponse,
    ProviderPayrollSubmissionRequest,
    ProviderPayrollSubmissionResponse,
    GlobalPayrollDashboardResponse,
    PayrollCostByCountryItem,
    PayrollExceptionItem,
)
from app.services import global_payroll_service

router = APIRouter(prefix="/api/v3/global-payroll", tags=["Module 21 - Global Payroll & Multi-Country Workforce"])


def _resolve_tenant_id(request: Request, db: Session, current_user: Optional[User] = None) -> str:
    header_tenant = request.headers.get("X-Tenant-ID")
    if header_tenant:
        return header_tenant
    if current_user and getattr(current_user, "tenant_id", None):
        return current_user.tenant_id
    if current_user and getattr(current_user, "person", None) and getattr(current_user.person, "tenant_id", None):
        return current_user.person.tenant_id
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


# ===========================================================================
# 1. Countries
# ===========================================================================

@router.get("/countries", response_model=List[PayrollCountryResponse])
def list_countries(
    request: Request,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(PayrollCountry).filter(PayrollCountry.tenant_id == tenant_id)
    if active_only:
        q = q.filter(PayrollCountry.active == True)
    return q.order_by(PayrollCountry.country_name.asc()).all()


@router.post("/countries", response_model=PayrollCountryResponse, status_code=status.HTTP_201_CREATED)
def create_country(
    request: Request,
    payload: PayrollCountryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.configure")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    existing = db.query(PayrollCountry).filter(
        PayrollCountry.tenant_id == tenant_id,
        PayrollCountry.country_code == payload.country_code.upper(),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Country {payload.country_code} already registered")

    c = PayrollCountry(
        tenant_id=tenant_id,
        country_code=payload.country_code.upper(),
        country_name=payload.country_name,
        default_currency=payload.default_currency.upper(),
        timezone=payload.timezone,
        active=payload.active,
        payroll_enabled=payload.payroll_enabled,
        adapter_status=payload.adapter_status.value if hasattr(payload.adapter_status, 'value') else payload.adapter_status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/countries/{id}", response_model=PayrollCountryResponse)
def get_country(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = db.query(PayrollCountry).filter(PayrollCountry.id == id, PayrollCountry.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")
    return c


# ===========================================================================
# 2. Configurations
# ===========================================================================

@router.get("/configurations", response_model=List[GlobalPayrollConfigurationResponse])
def list_configurations(
    request: Request,
    country_id: Optional[str] = None,
    legal_entity_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.read")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(GlobalPayrollConfiguration).filter(GlobalPayrollConfiguration.tenant_id == tenant_id)
    if country_id:
        q = q.filter(GlobalPayrollConfiguration.country_id == country_id)
    if legal_entity_id:
        q = q.filter(GlobalPayrollConfiguration.legal_entity_id == legal_entity_id)
    return q.all()


@router.post("/configurations", response_model=GlobalPayrollConfigurationResponse, status_code=status.HTTP_201_CREATED)
def create_configuration(
    request: Request,
    payload: GlobalPayrollConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.configure")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cfg = GlobalPayrollConfiguration(
        tenant_id=tenant_id,
        legal_entity_id=payload.legal_entity_id,
        country_id=payload.country_id,
        default_currency=payload.default_currency.upper(),
        timezone=payload.timezone,
        payroll_frequency=payload.payroll_frequency.value,
        payroll_day=payload.payroll_day,
        cutoff_day=payload.cutoff_day,
        adapter_code=payload.adapter_code,
        active=payload.active,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


# ===========================================================================
# 3. Pay Groups
# ===========================================================================

@router.get("/pay-groups", response_model=List[PayrollPayGroupResponse])
def list_pay_groups(
    request: Request,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(PayrollPayGroup).filter(PayrollPayGroup.tenant_id == tenant_id)
    if active_only:
        q = q.filter(PayrollPayGroup.active == True)
    return q.all()


@router.post("/pay-groups", response_model=PayrollPayGroupResponse, status_code=status.HTTP_201_CREATED)
def create_pay_group(
    request: Request,
    payload: PayrollPayGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.configure")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    existing = db.query(PayrollPayGroup).filter(
        PayrollPayGroup.tenant_id == tenant_id,
        PayrollPayGroup.code == payload.code.upper(),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Pay group {payload.code} already exists")

    pg = PayrollPayGroup(
        tenant_id=tenant_id,
        payroll_configuration_id=payload.payroll_configuration_id,
        name=payload.name,
        code=payload.code.upper(),
        description=payload.description,
        currency=payload.currency.upper(),
        frequency=payload.frequency.value,
        active=payload.active,
    )
    db.add(pg)
    db.commit()
    db.refresh(pg)
    return pg


# ===========================================================================
# 4. Calendars (Periods)
# ===========================================================================

@router.get("/calendars", response_model=List[PayrollCalendarResponse])
def list_calendars(
    request: Request,
    pay_group_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(PayrollCalendar).filter(PayrollCalendar.tenant_id == tenant_id)
    if pay_group_id:
        q = q.filter(PayrollCalendar.pay_group_id == pay_group_id)
    if status_filter:
        q = q.filter(PayrollCalendar.status == status_filter.upper())
    return q.order_by(PayrollCalendar.period_start.desc()).all()


@router.post("/calendars", response_model=PayrollCalendarResponse, status_code=status.HTTP_201_CREATED)
def create_calendar(
    request: Request,
    payload: PayrollCalendarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.manage")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    # Check overlap prevention invariant
    global_payroll_service.validate_calendar_overlap(
        db=db,
        pay_group_id=payload.pay_group_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )

    cal = PayrollCalendar(
        tenant_id=tenant_id,
        pay_group_id=payload.pay_group_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        cutoff_date=payload.cutoff_date,
        pay_date=payload.pay_date,
        status=payload.status.value,
    )
    db.add(cal)
    db.commit()
    db.refresh(cal)
    return cal


# ===========================================================================
# 5. Pay Components
# ===========================================================================

@router.get("/components", response_model=List[GlobalPayComponentResponse])
def list_components(
    request: Request,
    country_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(GlobalPayComponent).filter(GlobalPayComponent.tenant_id == tenant_id)
    if country_code:
        q = q.filter(or_(GlobalPayComponent.country_code == country_code.upper(), GlobalPayComponent.country_code == None))
    return q.order_by(GlobalPayComponent.name.asc()).all()


@router.post("/components", response_model=GlobalPayComponentResponse, status_code=status.HTTP_201_CREATED)
def create_component(
    request: Request,
    payload: GlobalPayComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.configure")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = GlobalPayComponent(
        tenant_id=tenant_id,
        code=payload.code.upper(),
        name=payload.name,
        component_type=payload.component_type.value,
        taxable=payload.taxable,
        pensionable=payload.pensionable,
        recurring=payload.recurring,
        country_code=payload.country_code.upper() if payload.country_code else None,
        description=payload.description,
        active=payload.active,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ===========================================================================
# 6. Country Payroll Rules
# ===========================================================================

@router.get("/rules", response_model=List[CountryPayrollRuleResponse])
def list_rules(
    request: Request,
    country_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(CountryPayrollRule).filter(CountryPayrollRule.tenant_id == tenant_id)
    if country_code:
        q = q.filter(CountryPayrollRule.country_code == country_code.upper())
    return q.order_by(CountryPayrollRule.effective_from.desc()).all()


@router.post("/rules", response_model=CountryPayrollRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    request: Request,
    payload: CountryPayrollRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.configure")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    r = CountryPayrollRule(
        tenant_id=tenant_id,
        country_code=payload.country_code.upper(),
        rule_code=payload.rule_code.upper(),
        rule_name=payload.rule_name,
        rule_type=payload.rule_type.value,
        configuration_reference=payload.configuration_reference,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        active=payload.active,
        version=payload.version,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ===========================================================================
# 7. Employee Assignments
# ===========================================================================

@router.get("/assignments", response_model=List[EmployeePayrollAssignmentResponse])
def list_assignments(
    request: Request,
    person_id: Optional[str] = None,
    pay_group_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(EmployeePayrollAssignment).filter(EmployeePayrollAssignment.tenant_id == tenant_id)
    if person_id:
        q = q.filter(EmployeePayrollAssignment.person_id == person_id)
    if pay_group_id:
        q = q.filter(EmployeePayrollAssignment.pay_group_id == pay_group_id)
    return q.all()


@router.post("/assignments", response_model=EmployeePayrollAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    request: Request,
    payload: EmployeePayrollAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.manage")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    # Check overlap prevention
    global_payroll_service.validate_assignment_overlap(
        db=db,
        person_id=payload.person_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )

    a = EmployeePayrollAssignment(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        legal_entity_id=payload.legal_entity_id,
        country_code=payload.country_code.upper(),
        pay_group_id=payload.pay_group_id,
        currency=payload.currency.upper(),
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        payroll_status=payload.payroll_status.value,
        split_ratio=payload.split_ratio,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ===========================================================================
# 8. Payroll Inputs
# ===========================================================================

@router.get("/inputs", response_model=List[PayrollInputResponse])
def list_inputs(
    request: Request,
    calendar_id: Optional[str] = None,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(PayrollInput).filter(PayrollInput.tenant_id == tenant_id)
    if calendar_id:
        q = q.filter(PayrollInput.payroll_calendar_id == calendar_id)
    if person_id:
        q = q.filter(PayrollInput.person_id == person_id)
    return q.all()


@router.post("/inputs", response_model=PayrollInputResponse, status_code=status.HTTP_201_CREATED)
def create_input(
    request: Request,
    payload: PayrollInputCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.manage")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cal = db.query(PayrollCalendar).filter(
        PayrollCalendar.id == payload.payroll_calendar_id,
        PayrollCalendar.tenant_id == tenant_id,
    ).first()
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    inp = PayrollInput(
        tenant_id=tenant_id,
        payroll_calendar_id=payload.payroll_calendar_id,
        person_id=payload.person_id,
        pay_component_id=payload.pay_component_id,
        amount=payload.amount,
        currency=payload.currency.upper(),
        source=payload.source.value,
        reference=payload.reference,
        effective_date=payload.effective_date or cal.period_end,
    )
    db.add(inp)
    db.commit()
    db.refresh(inp)
    return inp


# ===========================================================================
# 9. Runs & Gross-to-Net Calculations
# ===========================================================================

@router.get("/runs/{id}", response_model=PayrollRunSummaryResponse)
def get_payroll_run(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.read")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cal = db.query(PayrollCalendar).filter(
        PayrollCalendar.id == id,
        PayrollCalendar.tenant_id == tenant_id,
    ).first()
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar run not found")

    return global_payroll_service.summarize_payroll_calendar(db, cal)


@router.post("/runs/{id}/calculate", response_model=PayrollRunSummaryResponse)
def calculate_run(
    id: str,
    request: Request,
    payload: CalculatePayrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.process")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return global_payroll_service.calculate_payroll_run(
        db=db,
        calendar_id=id,
        tenant_id=tenant_id,
        caller_user=current_user,
        person_ids=payload.person_ids,
        recalculate_existing=payload.recalculate_existing,
    )


@router.post("/runs/{id}/approve", response_model=PayrollCalendarResponse)
def approve_run(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.approve")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return global_payroll_service.approve_payroll_calendar(
        db=db,
        calendar_id=id,
        tenant_id=tenant_id,
        caller_user=current_user,
    )


@router.post("/runs/{id}/finalize", response_model=PayrollCalendarResponse)
def finalize_run(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.finalize")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return global_payroll_service.finalize_payroll_calendar(
        db=db,
        calendar_id=id,
        tenant_id=tenant_id,
        caller_user=current_user,
    )


# ===========================================================================
# 10. Results & Components
# ===========================================================================

@router.get("/results", response_model=List[GlobalPayrollResultResponse])
def list_results(
    request: Request,
    calendar_id: Optional[str] = None,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.read")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    user_role = getattr(current_user, "role", "").lower()

    # Manager restriction: cannot see other employees' individual salary records
    if user_role not in ["super_admin", "hr_admin", "finance"]:
        caller_person_id = getattr(current_user, "person_id", None)
        if not caller_person_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        person_id = caller_person_id  # Restrict to own

    q = db.query(GlobalPayrollResult).filter(GlobalPayrollResult.tenant_id == tenant_id)
    if calendar_id:
        q = q.filter(GlobalPayrollResult.payroll_calendar_id == calendar_id)
    if person_id:
        q = q.filter(GlobalPayrollResult.person_id == person_id)

    return q.all()


@router.get("/results/{id}", response_model=GlobalPayrollResultResponse)
def get_result(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    res = db.query(GlobalPayrollResult).filter(
        GlobalPayrollResult.id == id,
        GlobalPayrollResult.tenant_id == tenant_id,
    ).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll result not found")

    user_role = getattr(current_user, "role", "").lower()
    if user_role not in ["super_admin", "hr_admin", "finance"]:
        if res.person_id != getattr(current_user, "person_id", None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view this payroll result")

    return res


# ===========================================================================
# 11. Adjustments
# ===========================================================================

@router.get("/adjustments", response_model=List[PayrollAdjustmentResponse])
def list_adjustments(
    request: Request,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.adjust")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(PayrollAdjustment).filter(PayrollAdjustment.tenant_id == tenant_id)
    if person_id:
        q = q.filter(PayrollAdjustment.person_id == person_id)
    return q.order_by(PayrollAdjustment.created_at.desc()).all()


@router.post("/adjustments", response_model=PayrollAdjustmentResponse, status_code=status.HTTP_201_CREATED)
def create_adjustment(
    request: Request,
    payload: PayrollAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.adjust")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    adj = PayrollAdjustment(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        original_payroll_result_id=payload.original_payroll_result_id,
        adjustment_type=payload.adjustment_type.value,
        amount=payload.amount,
        currency=payload.currency.upper(),
        reason=payload.reason,
        effective_period=payload.effective_period,
        status=PayrollAdjustmentStatus.PENDING.value,
        created_by=current_user.id,
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return adj


# ===========================================================================
# 12. Reconciliation
# ===========================================================================

@router.get("/reconciliation", response_model=PayrollReconciliationResponse)
def get_reconciliation(
    calendar_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.reconcile")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cal = db.query(PayrollCalendar).filter(
        PayrollCalendar.id == calendar_id,
        PayrollCalendar.tenant_id == tenant_id,
    ).first()
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    rec = global_payroll_service.reconcile_calendar(db, cal)
    db.commit()
    db.refresh(rec)
    return rec


# ===========================================================================
# 13. Multi-Currency FX Rates
# ===========================================================================

@router.get("/exchange-rates", response_model=List[PayrollExchangeRateResponse])
def list_exchange_rates(
    request: Request,
    base_currency: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(PayrollExchangeRate).filter(PayrollExchangeRate.tenant_id == tenant_id)
    if base_currency:
        q = q.filter(PayrollExchangeRate.base_currency == base_currency.upper())
    return q.order_by(PayrollExchangeRate.effective_date.desc()).all()


@router.post("/exchange-rates", response_model=PayrollExchangeRateResponse, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    request: Request,
    payload: PayrollExchangeRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.configure")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    rate = PayrollExchangeRate(
        tenant_id=tenant_id,
        base_currency=payload.base_currency.upper(),
        quote_currency=payload.quote_currency.upper(),
        rate=payload.rate,
        effective_date=payload.effective_date or date.today(),
        source=payload.source.value,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


# ===========================================================================
# 14. Payslips (ESS View & Ownership Authorization)
# ===========================================================================

@router.get("/payslips", response_model=List[GlobalPayslipRecordResponse])
def list_payslips(
    request: Request,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    user_role = getattr(current_user, "role", "").lower()

    if user_role not in ["super_admin", "hr_admin", "finance"]:
        caller_person = getattr(current_user, "person_id", None)
        if not caller_person:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee identity missing")
        person_id = caller_person

    q = db.query(GlobalPayslipRecord).filter(GlobalPayslipRecord.tenant_id == tenant_id)
    if person_id:
        q = q.filter(GlobalPayslipRecord.person_id == person_id)

    slips = q.order_by(GlobalPayslipRecord.generated_at.desc()).all()
    res = []
    for s in slips:
        item = {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "payroll_result_id": s.payroll_result_id,
            "person_id": s.person_id,
            "document_reference": s.document_reference,
            "generated_at": s.generated_at,
            "currency": s.currency,
            "status": s.status,
            "gross": s.payroll_result.gross if s.payroll_result else None,
            "net_pay": s.payroll_result.net_pay if s.payroll_result else None,
            "period_start": s.payroll_result.calendar.period_start if s.payroll_result and s.payroll_result.calendar else None,
            "period_end": s.payroll_result.calendar.period_end if s.payroll_result and s.payroll_result.calendar else None,
            "pay_group_name": s.payroll_result.calendar.pay_group.name if s.payroll_result and s.payroll_result.calendar and s.payroll_result.calendar.pay_group else None,
        }
        res.append(item)
    return res


@router.get("/payslips/{id}", response_model=GlobalPayslipRecordResponse)
def get_payslip(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    slip = db.query(GlobalPayslipRecord).filter(
        GlobalPayslipRecord.id == id,
        GlobalPayslipRecord.tenant_id == tenant_id,
    ).first()
    if not slip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip not found")

    if not global_payroll_service.can_access_payslip(current_user, slip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you cannot access another employee's payslip",
        )

    return {
        "id": slip.id,
        "tenant_id": slip.tenant_id,
        "payroll_result_id": slip.payroll_result_id,
        "person_id": slip.person_id,
        "document_reference": slip.document_reference,
        "generated_at": slip.generated_at,
        "currency": slip.currency,
        "status": slip.status,
        "gross": slip.payroll_result.gross if slip.payroll_result else None,
        "net_pay": slip.payroll_result.net_pay if slip.payroll_result else None,
        "period_start": slip.payroll_result.calendar.period_start if slip.payroll_result and slip.payroll_result.calendar else None,
        "period_end": slip.payroll_result.calendar.period_end if slip.payroll_result and slip.payroll_result.calendar else None,
        "pay_group_name": slip.payroll_result.calendar.pay_group.name if slip.payroll_result and slip.payroll_result.calendar and slip.payroll_result.calendar.pay_group else None,
    }


# ===========================================================================
# 15. International Providers Integration
# ===========================================================================

@router.post("/providers/submit", response_model=ProviderPayrollSubmissionResponse)
def submit_provider_payroll(
    request: Request,
    payload: ProviderPayrollSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.provider.manage")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cal = db.query(PayrollCalendar).filter(
        PayrollCalendar.id == payload.calendar_id,
        PayrollCalendar.tenant_id == tenant_id,
    ).first()
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    results = db.query(GlobalPayrollResult).filter(
        GlobalPayrollResult.payroll_calendar_id == cal.id
    ).all()

    provider_adapter = global_payroll_service.GenericPayrollProviderAdapter()
    return provider_adapter.submit_payroll(cal, results)


# ===========================================================================
# 16. Executive Dashboard & Analytics
# ===========================================================================

@router.get("/dashboard", response_model=GlobalPayrollDashboardResponse)
def get_global_payroll_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("global_payroll.analytics.read")),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    total_countries = db.query(func.count(PayrollCountry.id)).filter(PayrollCountry.tenant_id == tenant_id).scalar() or 0
    active_countries = db.query(func.count(PayrollCountry.id)).filter(
        PayrollCountry.tenant_id == tenant_id,
        PayrollCountry.active == True,
    ).scalar() or 0
    total_pgs = db.query(func.count(PayrollPayGroup.id)).filter(PayrollPayGroup.tenant_id == tenant_id).scalar() or 0
    open_cals = db.query(func.count(PayrollCalendar.id)).filter(
        PayrollCalendar.tenant_id == tenant_id,
        PayrollCalendar.status.in_([PayrollCalendarStatus.OPEN.value, PayrollCalendarStatus.PROCESSING.value]),
    ).scalar() or 0
    pending_appr = db.query(func.count(PayrollCalendar.id)).filter(
        PayrollCalendar.tenant_id == tenant_id,
        PayrollCalendar.status == PayrollCalendarStatus.PENDING_APPROVAL.value,
    ).scalar() or 0
    total_assign = db.query(func.count(EmployeePayrollAssignment.id)).filter(
        EmployeePayrollAssignment.tenant_id == tenant_id,
        EmployeePayrollAssignment.payroll_status == AssignmentPayrollStatus.ACTIVE.value,
    ).scalar() or 0

    # Aggregate cost by country
    countries = db.query(PayrollCountry).filter(PayrollCountry.tenant_id == tenant_id).all()
    cost_by_country: List[PayrollCostByCountryItem] = []
    total_cost_usd = Decimal("0.00")

    for c in countries:
        # Sum all results for pay groups in this country
        results = db.query(GlobalPayrollResult).join(
            PayrollCalendar, GlobalPayrollResult.payroll_calendar_id == PayrollCalendar.id
        ).join(
            PayrollPayGroup, PayrollCalendar.pay_group_id == PayrollPayGroup.id
        ).join(
            GlobalPayrollConfiguration, PayrollPayGroup.payroll_configuration_id == GlobalPayrollConfiguration.id
        ).filter(
            GlobalPayrollConfiguration.country_id == c.id,
            GlobalPayrollResult.tenant_id == tenant_id,
        ).all()

        emp_count = len(set(r.person_id for r in results))
        tot_gross = sum((r.gross for r in results), Decimal("0.00"))
        tot_net = sum((r.net_pay for r in results), Decimal("0.00"))
        tot_employer = sum((r.employer_contributions for r in results), Decimal("0.00"))

        cost_by_country.append(PayrollCostByCountryItem(
            country_code=c.country_code,
            country_name=c.country_name,
            currency=c.default_currency,
            employee_count=emp_count,
            total_gross=tot_gross,
            total_net=tot_net,
            total_employer_cost=tot_employer,
        ))

        # Convert to USD approx or sum base
        total_cost_usd += tot_gross

    # Detect exceptions (e.g. unassigned employees, variance in reconciliation)
    exceptions: List[PayrollExceptionItem] = []
    variance_recs = db.query(PayrollReconciliation).filter(
        PayrollReconciliation.tenant_id == tenant_id,
        PayrollReconciliation.status == PayrollReconciliationStatus.VARIANCE.value,
    ).all()

    for vr in variance_recs:
        exceptions.append(PayrollExceptionItem(
            calendar_id=vr.payroll_calendar_id,
            pay_group_name=vr.calendar.pay_group.name if vr.calendar and vr.calendar.pay_group else "Unknown",
            country_code=vr.calendar.pay_group.configuration.country.country_code if vr.calendar and vr.calendar.pay_group and vr.calendar.pay_group.configuration.country else "N/A",
            issue_type="RECONCILIATION_VARIANCE",
            description=f"Calculated variance of {vr.variance} {vr.currency} detected in cycle.",
            severity="HIGH",
        ))

    return GlobalPayrollDashboardResponse(
        total_countries=total_countries,
        active_countries=active_countries,
        total_pay_groups=total_pgs,
        open_calendars=open_cals,
        pending_approvals=pending_appr,
        total_active_assignments=total_assign,
        total_global_workforce_cost_usd=total_cost_usd,
        cost_by_country=cost_by_country,
        exceptions=exceptions,
    )
