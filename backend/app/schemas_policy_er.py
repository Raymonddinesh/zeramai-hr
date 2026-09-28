"""
schemas_policy_er.py - Module 8: HR Policy & Employee Relations Pydantic Schemas.
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models_policy_er import (
    HRPolicyStatus, HRPolicyCategory, ERCaseCategory, ERCaseStatus, ERCaseSeverity,
    DisciplinaryActionType, DisciplinaryStatus
)


# ===========================================================================
# HR Policy Schemas
# ===========================================================================

class HRPolicyCreate(BaseModel):
    title: str
    policy_code: str
    category: HRPolicyCategory = HRPolicyCategory.GENERAL
    description: Optional[str] = None
    content: str
    effective_date: date
    review_date: Optional[date] = None
    legal_entity_id: Optional[str] = None
    department_id: Optional[str] = None
    employment_type: Optional[str] = None
    is_mandatory: bool = True


class HRPolicyVersionCreate(BaseModel):
    version: str
    effective_date: date
    review_date: Optional[date] = None
    content: str
    description: Optional[str] = None


class HRPolicyOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    title: str
    policy_code: str
    category: HRPolicyCategory
    description: Optional[str] = None
    content: str
    version: str
    status: HRPolicyStatus
    effective_date: date
    review_date: Optional[date] = None
    legal_entity_id: Optional[str] = None
    department_id: Optional[str] = None
    employment_type: Optional[str] = None
    is_mandatory: bool
    previous_version_id: Optional[str] = None
    created_by_id: str
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    published_by_id: Optional[str] = None
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    has_acknowledged: Optional[bool] = None


class PolicyAcknowledgementOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    policy_id: str
    policy_title: Optional[str] = None
    policy_version: str
    person_id: str
    person_name: Optional[str] = None
    acknowledged_at: datetime
    ip_address: Optional[str] = None
    status: str


class PolicyComplianceStatusOut(BaseModel):
    policy_id: str
    policy_title: str
    policy_code: str
    version: str
    total_eligible_employees: int
    acknowledged_count: int
    compliance_rate_pct: float


# ===========================================================================
# Employee Relations Schemas
# ===========================================================================

class ERCaseNoteCreate(BaseModel):
    note_type: str = "internal_hr"  # "internal_hr", "investigation", "evidence", "employee_communication"
    content: str
    is_confidential: bool = True


class ERCaseNoteOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    case_id: str
    author_id: str
    author_name: Optional[str] = None
    note_type: str
    content: str
    is_confidential: bool
    created_at: datetime


class ERCaseCreate(BaseModel):
    title: str
    category: ERCaseCategory
    severity: ERCaseSeverity = ERCaseSeverity.MEDIUM
    subject_person_id: str
    reporting_manager_id: Optional[str] = None
    description: str
    investigation_summary: Optional[str] = None


class ERCaseAssign(BaseModel):
    hr_owner_id: str


class ERCaseStatusUpdate(BaseModel):
    status: ERCaseStatus
    investigation_summary: Optional[str] = None
    resolution_summary: Optional[str] = None


class ERCaseOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    case_number: str
    title: str
    category: ERCaseCategory
    severity: ERCaseSeverity
    subject_person_id: str
    subject_person_name: Optional[str] = None
    reporting_manager_id: Optional[str] = None
    hr_owner_id: str
    hr_owner_name: Optional[str] = None
    created_by_id: str
    status: ERCaseStatus
    description: str
    investigation_summary: Optional[str] = None
    resolution_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    notes: List[ERCaseNoteOut] = []
    disciplinary_actions_count: int = 0


# ===========================================================================
# Disciplinary Action Schemas
# ===========================================================================

class DisciplinaryActionCreate(BaseModel):
    case_id: Optional[str] = None
    person_id: Optional[str] = None
    action_type: DisciplinaryActionType
    reason: Optional[str] = None
    description: Optional[str] = None
    action_plan: Optional[str] = None
    issued_date: Optional[date] = None
    effective_date: date
    expiry_date: Optional[date] = None


class DisciplinaryActionOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    case_id: Optional[str] = None
    person_id: str
    person_name: Optional[str] = None
    action_type: str
    reason: str
    action_plan: Optional[str] = None
    issued_by_id: str
    issued_date: date
    effective_date: date
    expiry_date: Optional[date] = None
    status: str
    employee_acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
