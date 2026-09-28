from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class EmployeeProfileOut(BaseModel):
    class Config:
        from_attributes = True

    id: str  # person_id
    user_id: str
    full_name: str
    preferred_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    emergency_contact: Optional[str] = None

    # Employment details
    designation: Optional[str] = None
    department: Optional[str] = None
    engagement_type: Optional[str] = None
    start_date: Optional[date] = None
    reporting_manager_id: Optional[str] = None
    reporting_manager_name: Optional[str] = None
    work_location: Optional[str] = None
    status: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    phone: Optional[str] = None
    preferred_name: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    emergency_contact: Optional[str] = None


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

class AssetItemOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    asset_name: str
    asset_type: str
    serial_number: Optional[str] = None
    assigned_date: date
    return_status: str


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class ExpenseClaimCreate(BaseModel):
    category: str
    amount: float
    currency: str = "INR"
    description: str
    merchant: Optional[str] = None
    receipt_url: Optional[str] = None


class ExpenseClaimOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    ticket_number: str
    category: str
    amount: float
    currency: str
    description: str
    merchant: Optional[str] = None
    receipt_url: Optional[str] = None
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Summaries for Aggregated Dashboard
# ---------------------------------------------------------------------------

class AttendanceRecordOut(BaseModel):
    id: str
    date: date
    status: str
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    notes: Optional[str] = None


class LeaveBalanceItemOut(BaseModel):
    policy_name: str
    leave_type: str
    balance: float


class LeaveRequestItemOut(BaseModel):
    id: str
    start_date: date
    end_date: date
    leave_type: str
    status: str
    reason: Optional[str] = None


class LeaveSummaryOut(BaseModel):
    balances: List[LeaveBalanceItemOut] = []
    recent_requests: List[LeaveRequestItemOut] = []


class PayslipSummaryOut(BaseModel):
    id: str
    month: str
    gross_pay: float
    total_deductions: float
    net_pay: float


class DocumentItemOut(BaseModel):
    id: str
    document_type: str
    file_name: str
    status: str
    upload_date: Optional[datetime] = None


class OKRObjectiveSummaryOut(BaseModel):
    id: str
    title: str
    progress_percentage: float
    status: str


class PerformanceSummaryOut(BaseModel):
    objectives: List[OKRObjectiveSummaryOut] = []
    latest_review_rating: Optional[str] = None


class LearningSummaryOut(BaseModel):
    enrolled_courses_count: int = 0
    completed_courses_count: int = 0
    certificates_count: int = 0


class HRRequestSummaryOut(BaseModel):
    id: str
    ticket_number: str
    category: str
    priority: str
    subject: str
    status: str
    created_at: datetime


class OffboardingSummaryOut(BaseModel):
    id: str
    ticket_number: str
    status: str
    resignation_date: date
    proposed_last_working_day: date
    approved_last_working_day: Optional[date] = None


class EmployeeDashboardOut(BaseModel):
    profile: EmployeeProfileOut
    attendance: List[AttendanceRecordOut] = []
    leave: LeaveSummaryOut
    payslips: List[PayslipSummaryOut] = []
    documents: List[DocumentItemOut] = []
    performance: PerformanceSummaryOut
    learning: LearningSummaryOut
    assets: List[AssetItemOut] = []
    expenses: List[ExpenseClaimOut] = []
    hr_requests: List[HRRequestSummaryOut] = []
    offboarding: Optional[OffboardingSummaryOut] = None
    compensation: Optional[dict] = None
    benefits: List[dict] = []

