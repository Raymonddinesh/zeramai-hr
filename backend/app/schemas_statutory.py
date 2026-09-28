from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models_statutory import (
    StatutoryAuthority,
    StatutoryScheme,
    FilingStatus,
    PaymentStatus,
    TaxRegime,
    TaxDeclarationStatus,
)


class StatutoryRuleCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    authority: StatutoryAuthority
    scheme: StatutoryScheme
    legal_entity_id: Optional[str] = None
    state: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class StatutoryRuleUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    effective_to: Optional[date] = None
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StatutoryRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    authority: StatutoryAuthority
    scheme: StatutoryScheme
    state: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    config: Dict[str, Any]
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StatutoryRegistrationCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    legal_entity_id: Optional[str] = None
    authority: StatutoryAuthority
    registration_number: str
    state: Optional[str] = None
    effective_date: date
    expiry_date: Optional[date] = None
    status: str = "active"
    verification_metadata: Optional[Dict[str, Any]] = None


class StatutoryRegistrationUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    registration_number: Optional[str] = None
    state: Optional[str] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    verification_metadata: Optional[Dict[str, Any]] = None


class StatutoryRegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    authority: StatutoryAuthority
    registration_number: str
    state: Optional[str] = None
    effective_date: date
    expiry_date: Optional[date] = None
    status: str
    verification_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class StatutoryCalculateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    person_id: str
    as_of: Optional[date] = None
    basic_wage: Optional[float] = None
    gross_wage: Optional[float] = None
    scheme: Optional[str] = None  # None for all schemes or "epf", "esi", "professional_tax", "tds"
    state: Optional[str] = "Karnataka"
    financial_year: Optional[str] = "2026-2027"


class StatutoryCalculateResponse(BaseModel):
    person_id: str
    as_of: date
    total_statutory_deductions: float
    total_employer_contributions: float
    schemes: Dict[str, Any]


class StatutoryCalculationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    period_id: str
    rule_id: str
    person_id: str
    amount: float
    result_snapshot: Dict[str, Any]
    rule_version: str
    created_at: datetime


class StatutoryFilingCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    legal_entity_id: Optional[str] = None
    authority: StatutoryAuthority
    scheme: StatutoryScheme
    period_start: date
    period_end: date
    due_date: date
    filed_date: Optional[date] = None
    status: FilingStatus = FilingStatus.DRAFT
    reference_number: Optional[str] = None
    filing_document_id: Optional[str] = None


class StatutoryFilingUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Optional[FilingStatus] = None
    filed_date: Optional[date] = None
    reference_number: Optional[str] = None
    filing_document_id: Optional[str] = None


class StatutoryFilingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    authority: StatutoryAuthority
    scheme: StatutoryScheme
    period_start: date
    period_end: date
    due_date: date
    filed_date: Optional[date] = None
    status: FilingStatus
    reference_number: Optional[str] = None
    filing_document_id: Optional[str] = None
    responsible_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StatutoryPaymentCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filing_id: str
    amount: float
    payment_date: date
    due_date: Optional[date] = None
    reference_number: Optional[str] = None
    status: PaymentStatus = PaymentStatus.DRAFT
    payment_document_id: Optional[str] = None


class StatutoryPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    amount: Optional[float] = None
    payment_date: Optional[date] = None
    status: Optional[PaymentStatus] = None
    reference_number: Optional[str] = None
    payment_document_id: Optional[str] = None


class StatutoryPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filing_id: str
    amount: float
    payment_date: date
    due_date: Optional[date] = None
    reference_number: Optional[str] = None
    status: PaymentStatus
    payment_document_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaxDeclarationCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    financial_year: str = "2026-2027"
    regime: TaxRegime = TaxRegime.NEW
    projected_income: float = 0.0
    deductions_json: Optional[List[Dict[str, Any]]] = None
    documents_json: Optional[List[Dict[str, Any]]] = None


class TaxDeclarationReview(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: str  # "approve" / "verify" / "reject"
    rejection_reason: Optional[str] = None


class TaxDeclarationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    person_id: str
    financial_year: str
    regime: TaxRegime
    projected_income: float
    deductions_json: Optional[List[Dict[str, Any]]] = None
    documents_json: Optional[List[Dict[str, Any]]] = None
    status: TaxDeclarationStatus
    verified_by_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
