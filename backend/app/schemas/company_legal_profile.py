from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models import UserRole

class CompanyLegalProfileBase(BaseModel):
    company_name: str
    trade_name: Optional[str] = None
    company_type: Optional[str] = None
    cin: Optional[str] = None
    pan_number: Optional[str] = None
    tan_number: Optional[str] = None
    gstin: Optional[str] = None
    incorporation_date: Optional[date] = None
    financial_year_start: Optional[date] = None
    financial_year_end: Optional[date] = None
    registered_office: Optional[str] = None
    corporate_office: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    hr_contact: Optional[str] = None
    finance_contact: Optional[str] = None
    compliance_contact: Optional[str] = None
    status: Optional[str] = "active"

class CompanyLegalProfileCreate(CompanyLegalProfileBase):
    tenant_id: str
    legal_entity_id: str

class CompanyLegalProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    trade_name: Optional[str] = None
    company_type: Optional[str] = None
    cin: Optional[str] = None
    pan_number: Optional[str] = None
    tan_number: Optional[str] = None
    gstin: Optional[str] = None
    incorporation_date: Optional[date] = None
    financial_year_start: Optional[date] = None
    financial_year_end: Optional[date] = None
    registered_office: Optional[str] = None
    corporate_office: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    hr_contact: Optional[str] = None
    finance_contact: Optional[str] = None
    compliance_contact: Optional[str] = None
    status: Optional[str] = None

class CompanyLegalProfileOut(CompanyLegalProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    legal_entity_id: str
    created_at: datetime
    updated_at: datetime

class StatutoryRegistrationBase(BaseModel):
    registration_type: str
    registration_number: str
    state: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    status: Optional[str] = "active"

class StatutoryRegistrationCreate(StatutoryRegistrationBase):
    company_profile_id: str

class StatutoryRegistrationUpdate(BaseModel):
    registration_type: Optional[str] = None
    registration_number: Optional[str] = None
    state: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    status: Optional[str] = None

class StatutoryRegistrationOut(StatutoryRegistrationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_profile_id: str
    created_at: datetime
    updated_at: datetime
