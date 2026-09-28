from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v11 import CompanyLegalProfile, StatutoryRegistration
from app.schemas.company_legal_profile import (
    CompanyLegalProfileCreate,
    CompanyLegalProfileUpdate,
    CompanyLegalProfileOut,
    StatutoryRegistrationCreate,
    StatutoryRegistrationUpdate,
    StatutoryRegistrationOut,
)

router = APIRouter(prefix="/api/v3/company-legal-profile", tags=["company_legal_profile"])

# Helper to enforce tenant isolation
def get_tenant_id(current_user: User, request: Request = None, db: Session = None) -> str:
    if request:
        header = request.headers.get("X-Tenant-ID")
        if header:
            return header
    tid = getattr(current_user, "tenant_id", None)
    if tid:
        return tid
    if db:
        from app.models_v3 import Tenant
        t = db.query(Tenant).first()
        if t:
            return t.id
    return "default_tenant"

# CRUD for CompanyLegalProfile
@router.post("/", response_model=CompanyLegalProfileOut, status_code=status.HTTP_201_CREATED)
def create_company_legal_profile(
    payload: CompanyLegalProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("company_legal_profile:create")),
):
    # tenant_id derived from auth context, ignore payload.tenant_id if provided
    tenant_id = get_tenant_id(current_user)
    profile = CompanyLegalProfile(
        tenant_id=tenant_id,
        legal_entity_id=payload.legal_entity_id,
        company_name=payload.company_name,
        trade_name=payload.trade_name,
        company_type=payload.company_type,
        cin=payload.cin,
        pan_number=payload.pan_number,
        tan_number=payload.tan_number,
        gstin=payload.gstin,
        incorporation_date=payload.incorporation_date,
        financial_year_start=payload.financial_year_start,
        financial_year_end=payload.financial_year_end,
        registered_office=payload.registered_office,
        corporate_office=payload.corporate_office,
        state=payload.state,
        country=payload.country,
        hr_contact=payload.hr_contact,
        finance_contact=payload.finance_contact,
        compliance_contact=payload.compliance_contact,
        status=payload.status or "active",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    log_audit(
        db,
        user=current_user,
        action="company_legal_profile_created",
        entity="company_legal_profile",
        entity_id=profile.id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return profile

@router.get("/", response_model=List[CompanyLegalProfileOut])
def list_company_legal_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("company_legal_profile:view")),
):
    tenant_id = get_tenant_id(current_user)
    return db.query(CompanyLegalProfile).filter(CompanyLegalProfile.tenant_id == tenant_id).all()

@router.get("/{profile_id}", response_model=CompanyLegalProfileOut)
def get_company_legal_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("company_legal_profile:view")),
):
    tenant_id = get_tenant_id(current_user)
    profile = (
        db.query(CompanyLegalProfile)
        .filter(CompanyLegalProfile.id == profile_id, CompanyLegalProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CompanyLegalProfile not found")
    return profile

@router.put("/{profile_id}", response_model=CompanyLegalProfileOut)
def update_company_legal_profile(
    profile_id: str,
    payload: CompanyLegalProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("company_legal_profile:update")),
):
    tenant_id = get_tenant_id(current_user)
    profile = (
        db.query(CompanyLegalProfile)
        .filter(CompanyLegalProfile.id == profile_id, CompanyLegalProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CompanyLegalProfile not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    log_audit(
        db,
        user=current_user,
        action="company_legal_profile_updated",
        entity="company_legal_profile",
        entity_id=profile.id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return profile

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_legal_profile(
    profile_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("company_legal_profile:delete")),
):
    tenant_id = get_tenant_id(current_user)
    profile = (
        db.query(CompanyLegalProfile)
        .filter(CompanyLegalProfile.id == profile_id, CompanyLegalProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CompanyLegalProfile not found")
    db.delete(profile)
    db.commit()
    log_audit(
        db,
        user=current_user,
        action="company_legal_profile_deleted",
        entity="company_legal_profile",
        entity_id=profile_id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return None

# Nested CRUD for StatutoryRegistration
@router.get("/{profile_id}/registrations", response_model=List[StatutoryRegistrationOut])
def list_registrations(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_registration:view")),
):
    tenant_id = get_tenant_id(current_user)
    profile = (
        db.query(CompanyLegalProfile)
        .filter(CompanyLegalProfile.id == profile_id, CompanyLegalProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CompanyLegalProfile not found")
    return profile.registrations

@router.post("/{profile_id}/registrations", response_model=StatutoryRegistrationOut, status_code=status.HTTP_201_CREATED)
def create_registration(
    profile_id: str,
    payload: StatutoryRegistrationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_registration:create")),
):
    tenant_id = get_tenant_id(current_user)
    profile = (
        db.query(CompanyLegalProfile)
        .filter(CompanyLegalProfile.id == profile_id, CompanyLegalProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CompanyLegalProfile not found")
    reg = StatutoryRegistration(
        company_profile_id=profile.id,
        registration_type=payload.registration_type,
        registration_number=payload.registration_number,
        state=payload.state,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        status=payload.status or "active",
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
    )
    return reg

@router.put("/{profile_id}/registrations/{reg_id}", response_model=StatutoryRegistrationOut)
def update_registration(
    profile_id: str,
    reg_id: str,
    payload: StatutoryRegistrationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_registration:update")),
):
    tenant_id = get_tenant_id(current_user)
    reg = (
        db.query(StatutoryRegistration)
        .join(CompanyLegalProfile)
        .filter(
            StatutoryRegistration.id == reg_id,
            CompanyLegalProfile.id == profile_id,
            CompanyLegalProfile.tenant_id == tenant_id,
        )
        .first()
    )
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StatutoryRegistration not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reg, field, value)
    db.commit()
    db.refresh(reg)
    log_audit(
        db,
        user=current_user,
        action="statutory_registration_updated",
        entity="statutory_registration",
        entity_id=reg.id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return reg

@router.delete("/{profile_id}/registrations/{reg_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registration(
    profile_id: str,
    reg_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("statutory_registration:delete")),
):
    tenant_id = get_tenant_id(current_user)
    reg = (
        db.query(StatutoryRegistration)
        .join(CompanyLegalProfile)
        .filter(
            StatutoryRegistration.id == reg_id,
            CompanyLegalProfile.id == profile_id,
            CompanyLegalProfile.tenant_id == tenant_id,
        )
        .first()
    )
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StatutoryRegistration not found")
    db.delete(reg)
    db.commit()
    log_audit(
        db,
        user=current_user,
        action="statutory_registration_deleted",
        entity="statutory_registration",
        entity_id=reg_id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return None
