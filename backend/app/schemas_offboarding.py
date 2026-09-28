from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Input Schemas
# ---------------------------------------------------------------------------

class ResignationCreate(BaseModel):
    resignation_date: date
    proposed_last_working_day: date
    reason_category: Optional[str] = "better_opportunity"
    employee_comments: Optional[str] = None


class ExitReviewAction(BaseModel):
    action: str  # "approve", "reject", "under_review"
    comments: Optional[str] = None
    approved_last_working_day: Optional[date] = None


class ClearanceTaskUpdate(BaseModel):
    task_id: str
    is_cleared: bool
    remarks: Optional[str] = None


class HandoverCreate(BaseModel):
    title: str
    description: Optional[str] = None
    recipient_user_id: Optional[str] = None
    recipient_name: Optional[str] = None
    documentation_url: Optional[str] = None


class HandoverStatusUpdate(BaseModel):
    handover_id: str
    status: str  # "pending", "completed"


class ExitInterviewUpdate(BaseModel):
    primary_reason: Optional[str] = None
    feedback_company: Optional[str] = None
    feedback_management: Optional[str] = None
    feedback_role: Optional[str] = None
    is_completed: bool = False


class SettlementReadinessUpdate(BaseModel):
    payroll_reviewed: Optional[bool] = None
    leave_balance_reviewed: Optional[bool] = None
    leave_encashment_days: Optional[float] = None
    asset_clearance_completed: Optional[bool] = None
    finance_clearance_completed: Optional[bool] = None
    settlement_status: Optional[str] = None
    settlement_amount: Optional[float] = None
    remarks: Optional[str] = None


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------

class ExitClearanceTaskOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    department: str
    task_name: str
    is_cleared: bool
    cleared_by_user_id: Optional[str] = None
    cleared_at: Optional[datetime] = None
    remarks: Optional[str] = None


class ExitHandoverOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    title: str
    description: Optional[str] = None
    recipient_user_id: Optional[str] = None
    recipient_name: Optional[str] = None
    documentation_url: Optional[str] = None
    status: str
    completed_at: Optional[datetime] = None


class ExitInterviewOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    interview_date: Optional[date] = None
    interviewer_user_id: Optional[str] = None
    primary_reason: Optional[str] = None
    feedback_company: Optional[str] = None
    feedback_management: Optional[str] = None
    feedback_role: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None


class ExitSettlementOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    payroll_reviewed: bool
    leave_balance_reviewed: bool
    leave_encashment_days: float
    asset_clearance_completed: bool
    finance_clearance_completed: bool
    settlement_status: str
    settlement_amount: Optional[float] = None
    remarks: Optional[str] = None
    settled_at: Optional[datetime] = None


class ExitRequestOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    ticket_number: str
    tenant_id: Optional[str] = None
    person_id: str
    user_id: str
    resignation_date: date
    proposed_last_working_day: date
    approved_last_working_day: Optional[date] = None
    notice_period_days: int
    reason_category: Optional[str] = None
    employee_comments: Optional[str] = None
    status: str
    manager_comments: Optional[str] = None
    hr_comments: Optional[str] = None
    manager_reviewed_by_id: Optional[str] = None
    manager_approved_at: Optional[datetime] = None
    hr_reviewed_by_id: Optional[str] = None
    hr_approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    clearance_tasks: List[ExitClearanceTaskOut] = []
    handovers: List[ExitHandoverOut] = []
    interview: Optional[ExitInterviewOut] = None
    settlement: Optional[ExitSettlementOut] = None
