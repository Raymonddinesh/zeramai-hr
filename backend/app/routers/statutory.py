from datetime import date, datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit, has_permission
from app.models import AuditResult, User, UserRole, Person
from app.models_v3 import Tenant, LegalEntity
from app.models_statutory import (
    StatutoryAuthority,
    StatutoryScheme,
    StatutoryRule,
    StatutoryRegistration,
    StatutoryApplicability,
    StatutoryPeriod,
    StatutoryCalculation,
    StatutoryContribution,
    StatutoryFiling,
    StatutoryPayment,
    FilingStatus,
    PaymentStatus,
)
from app.schemas_statutory import (
    StatutoryRuleCreate,
    StatutoryRuleUpdate,
    StatutoryRuleOut,
    StatutoryRegistrationCreate,
    StatutoryRegistrationUpdate,
    StatutoryRegistrationOut,
    StatutoryCalculateRequest,
    StatutoryCalculateResponse,
    StatutoryCalculationOut,
    StatutoryFilingCreate,
    StatutoryFilingUpdate,
    StatutoryFilingOut,
    StatutoryPaymentCreate,
    StatutoryPaymentUpdate,
    StatutoryPaymentOut,
)
from app.adapters.india_statutory_adapter import (
    EPFAdapter,
    ESIAdapter,
    ProfessionalTaxAdapter,
    TDSAdapter,
)

router = APIRouter(prefix="/api/v3/statutory", tags=["statutory"])


def _resolve_tenant_id(request: Request, db: Session) -> str:
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def _resolve_legal_entity_id(tenant_id: str, db: Session, provided: Optional[str] = None) -> str:
    if provided:
        le = db.query(LegalEntity).filter(LegalEntity.id == provided).first()
        if le:
            return le.id
    le = db.query(LegalEntity).filter(LegalEntity.tenant_id == tenant_id).first()
    if not le:
        le = LegalEntity(
            tenant_id=tenant_id,
            name="Primary Legal Entity",
            country_code="IN",
            default_currency="INR",
        )
        db.add(le)
        db.commit()
    return le.id


# ---------------------------------------------------------------------------
# 1. Statutory Schemes & Rules
# ---------------------------------------------------------------------------

@router.get("/schemes", response_model=List[str])
def list_schemes(
    current_user: User = Depends(require_permission("statutory:view")),
):
    return [s.value for s in StatutoryScheme]


@router.post("/rules", response_model=StatutoryRuleOut, status_code=status.HTTP_201_CREATED)
def create_statutory_rule(
    payload: StatutoryRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    legal_entity_id = _resolve_legal_entity_id(tenant_id, db, payload.legal_entity_id)

    rule = StatutoryRule(
        tenant_id=tenant_id,
        legal_entity_id=legal_entity_id,
        authority=payload.authority,
        scheme=payload.scheme,
        state=payload.state,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        config=payload.config,
        description=payload.description,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_audit(
        db,
        user=current_user,
        action="statutory_rule_created",
        entity="statutory_rule",
        entity_id=rule.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"scheme": rule.scheme.value, "authority": rule.authority.value},
    )
    return rule


@router.get("/rules", response_model=List[StatutoryRuleOut])
def list_statutory_rules(
    scheme: Optional[StatutoryScheme] = None,
    state: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(StatutoryRule).filter(StatutoryRule.tenant_id == tenant_id)
    if scheme:
        query = query.filter(StatutoryRule.scheme == scheme)
    if state:
        query = query.filter(StatutoryRule.state == state)
    return query.order_by(StatutoryRule.effective_from.desc()).all()


@router.get("/rules/{rule_id}", response_model=StatutoryRuleOut)
def get_statutory_rule(
    rule_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    rule = db.query(StatutoryRule).filter(StatutoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statutory rule not found")
    if rule.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")
    return rule


@router.patch("/rules/{rule_id}", response_model=StatutoryRuleOut)
def update_statutory_rule(
    rule_id: str,
    payload: StatutoryRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    rule = db.query(StatutoryRule).filter(StatutoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statutory rule not found")
    if rule.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")

    if payload.effective_to is not None:
        rule.effective_to = payload.effective_to
    if payload.config is not None:
        rule.config = payload.config
    if payload.description is not None:
        rule.description = payload.description
    if payload.is_active is not None:
        rule.is_active = payload.is_active

    db.commit()
    db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# 2. Statutory Registrations
# ---------------------------------------------------------------------------

@router.get("/registrations", response_model=List[StatutoryRegistrationOut])
def list_registrations(
    request: Request,
    authority: Optional[StatutoryAuthority] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(StatutoryRegistration).filter(StatutoryRegistration.tenant_id == tenant_id)
    if authority:
        query = query.filter(StatutoryRegistration.authority == authority)
    return query.all()


@router.post("/registrations", response_model=StatutoryRegistrationOut, status_code=status.HTTP_201_CREATED)
def create_registration(
    payload: StatutoryRegistrationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    legal_entity_id = _resolve_legal_entity_id(tenant_id, db, payload.legal_entity_id)

    from app.models_v11 import CompanyLegalProfile
    profile = db.query(CompanyLegalProfile).filter(CompanyLegalProfile.legal_entity_id == legal_entity_id).first()
    if not profile:
        profile = CompanyLegalProfile(
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            company_name="Zeramai Technologies Pvt Ltd",
            status="active",
        )
        db.add(profile)
        db.flush()

    auth_str = payload.authority.value if hasattr(payload.authority, "value") else str(payload.authority)
    reg = StatutoryRegistration(
        tenant_id=tenant_id,
        legal_entity_id=legal_entity_id,
        company_profile_id=profile.id,
        authority=auth_str,
        registration_type=auth_str,
        registration_number=payload.registration_number,
        state=payload.state,
        effective_date=payload.effective_date,
        effective_from=payload.effective_date,
        expiry_date=payload.expiry_date,
        effective_to=payload.expiry_date,
        status=payload.status,
        verification_metadata=payload.verification_metadata,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)

    log_audit(
        db,
        user=current_user,
        action="statutory_registration_created",
        entity="statutory_registration",
        entity_id=reg.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"authority": str(reg.authority), "reg_num": reg.registration_number},
    )
    return reg


@router.get("/registrations/{reg_id}", response_model=StatutoryRegistrationOut)
def get_registration(
    reg_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    reg = db.query(StatutoryRegistration).filter(StatutoryRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statutory registration not found")
    if reg.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")
    return reg


@router.patch("/registrations/{reg_id}", response_model=StatutoryRegistrationOut)
def update_registration(
    reg_id: str,
    payload: StatutoryRegistrationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    reg = db.query(StatutoryRegistration).filter(StatutoryRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statutory registration not found")
    if reg.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")

    if payload.registration_number:
        reg.registration_number = payload.registration_number
    if payload.state is not None:
        reg.state = payload.state
    if payload.expiry_date is not None:
        reg.expiry_date = payload.expiry_date
    if payload.status:
        reg.status = payload.status
    if payload.verification_metadata is not None:
        reg.verification_metadata = payload.verification_metadata

    db.commit()
    db.refresh(reg)
    return reg


# ---------------------------------------------------------------------------
# 3. Calculation Engine (India Statutory Adapters)
# ---------------------------------------------------------------------------

@router.post("/calculate", response_model=StatutoryCalculateResponse)
def calculate_statutory(
    payload: StatutoryCalculateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:calculate")),
):
    tenant_id = _resolve_tenant_id(request, db)
    calc_date = payload.as_of or date.today()

    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person not found")

    # Determine wages from salary structure if not explicitly provided
    from app.models_v6 import SalaryStructure
    active_ss = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == payload.person_id,
        SalaryStructure.is_active == True,
    ).first()

    basic = payload.basic_wage
    gross = payload.gross_wage

    if active_ss:
        if gross is None:
            gross = float(active_ss.ctc_monthly)
        if basic is None and active_ss.components_json:
            for c in active_ss.components_json:
                if c.get("code") == "BASIC":
                    basic = float(c.get("amount", 0.0))
                    break

    basic = basic if basic is not None else 25000.0
    gross = gross if gross is not None else 50000.0

    schemes_result: Dict[str, Any] = {}
    total_deductions = 0.0
    total_employer = 0.0

    target_scheme = payload.scheme.lower() if payload.scheme else None

    # 1. EPF
    if not target_scheme or target_scheme == "epf":
        epf_res = EPFAdapter(db).calculate(
            person_id=payload.person_id,
            as_of=calc_date,
            basic_wage=basic,
            gross_wage=gross,
            tenant_id=tenant_id,
        )
        schemes_result["epf"] = epf_res
        total_deductions += epf_res["employee_deduction"]
        total_employer += epf_res["employer_contribution"]

    # 2. ESI
    if not target_scheme or target_scheme == "esi":
        esi_res = ESIAdapter(db).calculate(
            person_id=payload.person_id,
            as_of=calc_date,
            gross_wage=gross,
            tenant_id=tenant_id,
        )
        schemes_result["esi"] = esi_res
        total_deductions += esi_res["employee_deduction"]
        total_employer += esi_res["employer_contribution"]

    # 3. Professional Tax (PT)
    if not target_scheme or target_scheme in ("professional_tax", "pt"):
        pt_res = ProfessionalTaxAdapter(db).calculate(
            person_id=payload.person_id,
            as_of=calc_date,
            gross_wage=gross,
            state=payload.state or "Karnataka",
            tenant_id=tenant_id,
        )
        schemes_result["professional_tax"] = pt_res
        total_deductions += pt_res["employee_deduction"]
        total_employer += pt_res["employer_contribution"]

    # 4. TDS
    if not target_scheme or target_scheme == "tds":
        tds_res = TDSAdapter(db).calculate(
            person_id=payload.person_id,
            as_of=calc_date,
            monthly_gross=gross,
            financial_year=payload.financial_year or "2026-2027",
            tenant_id=tenant_id,
        )
        schemes_result["tds"] = tds_res
        total_deductions += tds_res["employee_deduction"]
        total_employer += tds_res["employer_contribution"]

    return StatutoryCalculateResponse(
        person_id=payload.person_id,
        as_of=calc_date,
        total_statutory_deductions=round(total_deductions, 2),
        total_employer_contributions=round(total_employer, 2),
        schemes=schemes_result,
    )


@router.get("/calculations", response_model=List[StatutoryCalculationOut])
def list_calculations(
    person_id: Optional[str] = None,
    period_id: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory:view")),
):
    query = db.query(StatutoryCalculation)
    if person_id:
        query = query.filter(StatutoryCalculation.person_id == person_id)
    if period_id:
        query = query.filter(StatutoryCalculation.period_id == period_id)
    return query.order_by(StatutoryCalculation.created_at.desc()).all()


# ---------------------------------------------------------------------------
# 4. Statutory Filings & Payments
# ---------------------------------------------------------------------------

@router.get("/filings", response_model=List[StatutoryFilingOut])
def list_filings(
    authority: Optional[StatutoryAuthority] = None,
    scheme: Optional[StatutoryScheme] = None,
    status_filter: Optional[FilingStatus] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_filing:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(StatutoryFiling).filter(StatutoryFiling.tenant_id == tenant_id)
    if authority:
        query = query.filter(StatutoryFiling.authority == authority)
    if scheme:
        query = query.filter(StatutoryFiling.scheme == scheme)
    if status_filter:
        query = query.filter(StatutoryFiling.status == status_filter)
    return query.order_by(StatutoryFiling.due_date.asc()).all()


@router.post("/filings", response_model=StatutoryFilingOut, status_code=status.HTTP_201_CREATED)
def create_filing(
    payload: StatutoryFilingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_filing:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    legal_entity_id = _resolve_legal_entity_id(tenant_id, db, payload.legal_entity_id)

    filing = StatutoryFiling(
        tenant_id=tenant_id,
        legal_entity_id=legal_entity_id,
        authority=payload.authority,
        scheme=payload.scheme,
        period_start=payload.period_start,
        period_end=payload.period_end,
        due_date=payload.due_date,
        filed_date=payload.filed_date,
        status=payload.status,
        reference_number=payload.reference_number,
        filing_document_id=payload.filing_document_id,
        responsible_user_id=current_user.id,
    )
    db.add(filing)
    db.commit()
    db.refresh(filing)

    log_audit(
        db,
        user=current_user,
        action="statutory_filing_created",
        entity="statutory_filing",
        entity_id=filing.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"authority": filing.authority.value, "scheme": filing.scheme.value},
    )
    return filing


@router.get("/filings/{filing_id}", response_model=StatutoryFilingOut)
def get_filing(
    filing_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_filing:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    filing = db.query(StatutoryFiling).filter(StatutoryFiling.id == filing_id).first()
    if not filing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filing not found")
    if filing.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")
    return filing


@router.patch("/filings/{filing_id}", response_model=StatutoryFilingOut)
def update_filing(
    filing_id: str,
    payload: StatutoryFilingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_filing:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    filing = db.query(StatutoryFiling).filter(StatutoryFiling.id == filing_id).first()
    if not filing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filing not found")
    if filing.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")

    if payload.status:
        filing.status = payload.status
    if payload.filed_date:
        filing.filed_date = payload.filed_date
    if payload.reference_number:
        filing.reference_number = payload.reference_number
    if payload.filing_document_id:
        filing.filing_document_id = payload.filing_document_id

    db.commit()
    db.refresh(filing)
    return filing


@router.get("/payments", response_model=List[StatutoryPaymentOut])
def list_payments(
    filing_id: Optional[str] = None,
    status_filter: Optional[PaymentStatus] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_payment:view")),
):
    query = db.query(StatutoryPayment)
    if filing_id:
        query = query.filter(StatutoryPayment.filing_id == filing_id)
    if status_filter:
        query = query.filter(StatutoryPayment.status == status_filter)
    return query.order_by(StatutoryPayment.payment_date.desc()).all()


@router.post("/payments", response_model=StatutoryPaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: StatutoryPaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_payment:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    filing = db.query(StatutoryFiling).filter(StatutoryFiling.id == payload.filing_id).first()
    if not filing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Associated filing not found")
    if filing.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant payment forbidden")

    payment = StatutoryPayment(
        filing_id=payload.filing_id,
        amount=payload.amount,
        payment_date=payload.payment_date,
        due_date=payload.due_date,
        reference_number=payload.reference_number,
        status=payload.status,
        payment_document_id=payload.payment_document_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    log_audit(
        db,
        user=current_user,
        action="statutory_payment_recorded",
        entity="statutory_payment",
        entity_id=payment.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"amount": float(payment.amount), "filing_id": payment.filing_id},
    )
    return payment


@router.get("/payments/{payment_id}", response_model=StatutoryPaymentOut)
def get_payment(
    payment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_payment:view")),
):
    payment = db.query(StatutoryPayment).filter(StatutoryPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return payment


@router.patch("/payments/{payment_id}", response_model=StatutoryPaymentOut)
def update_payment(
    payment_id: str,
    payload: StatutoryPaymentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_payment:manage")),
):
    payment = db.query(StatutoryPayment).filter(StatutoryPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    if payload.amount is not None:
        payment.amount = payload.amount
    if payload.payment_date is not None:
        payment.payment_date = payload.payment_date
    if payload.status is not None:
        payment.status = payload.status
    if payload.reference_number is not None:
        payment.reference_number = payload.reference_number
    if payload.payment_document_id is not None:
        payment.payment_document_id = payload.payment_document_id

    db.commit()
    db.refresh(payment)
    return payment
