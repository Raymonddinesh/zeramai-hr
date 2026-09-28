"""
schemas_compensation.py - Module 7: Compensation & Benefits Management Schemas.
"""
from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

from app.models_compensation import (
    RevisionStatus, RevisionReason, BonusType, BonusStatus, BenefitType, EnrollmentStatus
)


# ===========================================================================
# Compensation Structure & Revisions
# ===========================================================================

class ComponentItem(BaseModel):
    code: str
    name: str
    amount: float
    type: str = "earning"  # "earning", "deduction", "employer_contribution"


class CompensationRevisionCreate(BaseModel):
    person_id: str
    new_ctc_annual: float
    new_ctc_monthly: Optional[float] = None
    currency: str = "INR"
    components_json: List[Dict[str, Any]]
    effective_date: date
    reason: RevisionReason = RevisionReason.ANNUAL_REVIEW
    business_justification: Optional[str] = None
    hr_notes: Optional[str] = None


class CompensationRevisionRecommend(BaseModel):
    person_id: str
    proposed_ctc_annual: float
    effective_date: date
    reason: RevisionReason = RevisionReason.ANNUAL_REVIEW
    business_justification: str
    components_json: Optional[List[Dict[str, Any]]] = None


class CompensationRevisionReview(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    rejection_reason: Optional[str] = None
    hr_notes: Optional[str] = None


class CompensationRevisionOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    person_name: Optional[str] = None
    previous_salary_structure_id: Optional[str] = None
    previous_ctc_annual: Optional[float] = None
    new_ctc_annual: float
    new_ctc_monthly: float
    currency: str
    components_json: List[Dict[str, Any]]
    effective_date: date
    reason: str
    business_justification: Optional[str] = None
    hr_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    status: RevisionStatus
    created_by_id: str
    recommended_by_id: Optional[str] = None
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    resulting_salary_structure_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CompensationStructureOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    person_name: Optional[str] = None
    name: str
    effective_from: date
    effective_to: Optional[date] = None
    ctc_annual: float
    ctc_monthly: float
    components_json: List[Dict[str, Any]]
    currency: str
    is_active: bool


class CompensationHistoryItemOut(BaseModel):
    id: str
    type: str  # "salary_structure" or "revision"
    effective_date: date
    ctc_annual: float
    ctc_monthly: float
    currency: str
    reason: Optional[str] = None
    status: str
    approved_at: Optional[datetime] = None


# ===========================================================================
# Bonuses & Incentives
# ===========================================================================

class BonusIncentiveCreate(BaseModel):
    person_id: str
    bonus_type: BonusType
    amount: float
    currency: str = "INR"
    pay_period: str  # e.g. "2026-09"
    effective_date: date
    reason: Optional[str] = None


class BonusIncentiveReview(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    rejection_reason: Optional[str] = None


class BonusIncentiveOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    person_name: Optional[str] = None
    bonus_type: str
    amount: float
    currency: str
    pay_period: str
    effective_date: date
    reason: Optional[str] = None
    status: BonusStatus
    payroll_status: str
    created_by_id: str
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Benefits Plans & Enrollments
# ===========================================================================

class BenefitPlanCreate(BaseModel):
    name: str
    benefit_type: BenefitType
    provider: Optional[str] = None
    description: Optional[str] = None
    employer_contribution: float = 0.0
    employee_deduction: float = 0.0
    coverage_details: Optional[Dict[str, Any]] = None
    eligibility_criteria: Optional[Dict[str, Any]] = None


class BenefitPlanOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    name: str
    benefit_type: str
    provider: Optional[str] = None
    description: Optional[str] = None
    employer_contribution: float
    employee_deduction: float
    coverage_details: Optional[Dict[str, Any]] = None
    eligibility_criteria: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime


class BenefitEnrollmentCreate(BaseModel):
    person_id: str
    benefit_plan_id: str
    coverage_tier: str = "employee_only"
    employee_contribution: Optional[float] = None
    employer_contribution: Optional[float] = None
    effective_date: date
    notes: Optional[str] = None


class BenefitEnrollmentOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    person_name: Optional[str] = None
    benefit_plan_id: str
    plan_name: Optional[str] = None
    benefit_type: Optional[str] = None
    provider: Optional[str] = None
    coverage_tier: str
    status: EnrollmentStatus
    employee_contribution: float
    employer_contribution: float
    effective_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime


# ===========================================================================
# Overview & Employee Self-Service Summaries
# ===========================================================================

class CompensationOverviewOut(BaseModel):
    active_structures_count: int
    pending_revisions_count: int
    approved_revisions_count: int
    pending_bonuses_count: int
    total_annual_payroll_commitment: float
    total_benefits_enrolled: int


class EmployeeCompensationSummaryOut(BaseModel):
    has_active_structure: bool
    ctc_annual: Optional[float] = None
    ctc_monthly: Optional[float] = None
    currency: Optional[str] = None
    effective_from: Optional[date] = None
    components: List[Dict[str, Any]] = []
    recent_revisions: List[CompensationRevisionOut] = []
    enrolled_benefits: List[BenefitEnrollmentOut] = []
