"""
schemas_analytics.py - Pydantic schemas for Module 13: Enterprise HR Analytics,
Workforce Intelligence & Compliance Reporting.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Metric Breakdown Models
# ---------------------------------------------------------------------------

class BreakdownItem(BaseModel):
    name: str
    count: Optional[int] = 0
    value: Optional[float] = 0.0
    percentage: Optional[float] = 0.0


class TrendPoint(BaseModel):
    period: str
    count: Optional[int] = 0
    value: Optional[float] = 0.0


# ---------------------------------------------------------------------------
# Core Analytics Metric Response Schemas
# ---------------------------------------------------------------------------

class HeadcountMetricOut(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    new_hires: int
    exits: int
    by_department: List[BreakdownItem] = []
    by_legal_entity: List[BreakdownItem] = []
    by_location: List[BreakdownItem] = []
    by_employment_type: List[BreakdownItem] = []
    by_manager: List[BreakdownItem] = []
    trend: List[TrendPoint] = []


class AttritionMetricOut(BaseModel):
    exits: int
    voluntary_exits: int
    involuntary_exits: int
    resignation_rate: float
    turnover_rate: float
    average_tenure_months: float
    by_department: List[BreakdownItem] = []
    by_location: List[BreakdownItem] = []
    by_tenure_band: List[BreakdownItem] = []


class AttendanceMetricOut(BaseModel):
    total_records: int
    present_days: int
    absent_days: int
    attendance_rate: float
    absence_rate: float
    late_arrivals: int
    overtime_hours: float
    working_hours: float
    by_department: List[BreakdownItem] = []
    trends: List[TrendPoint] = []


class LeaveMetricOut(BaseModel):
    total_requests: int
    approved_requests: int
    pending_requests: int
    total_days_taken: float
    leave_utilization_rate: float
    by_type: List[BreakdownItem] = []
    by_department: List[BreakdownItem] = []
    trends: List[TrendPoint] = []


class FunnelStage(BaseModel):
    stage: str
    count: int
    conversion_rate: float


class RecruitmentMetricOut(BaseModel):
    open_positions: int
    total_candidates: int
    total_applications: int
    screening_rate: float
    interview_rate: float
    offer_rate: float
    offer_acceptance_rate: float
    average_time_to_hire_days: float
    average_time_to_fill_days: float
    funnel: List[FunnelStage] = []
    by_department: List[BreakdownItem] = []
    by_legal_entity: List[BreakdownItem] = []


class CompensationMetricOut(BaseModel):
    is_redacted: bool = False
    redaction_reason: Optional[str] = None
    sample_size: int = 0
    total_payroll_cost: Optional[float] = None
    fixed_compensation: Optional[float] = None
    variable_compensation: Optional[float] = None
    benefits_cost: Optional[float] = None
    employer_statutory_cost: Optional[float] = None
    by_department: List[BreakdownItem] = []
    by_legal_entity: List[BreakdownItem] = []
    salary_distribution: List[BreakdownItem] = []
    revisions_count: int = 0
    average_bonus: Optional[float] = None


class PayrollMetricOut(BaseModel):
    total_gross_pay: float
    total_net_pay: float
    total_deductions: float
    total_employer_contributions: float
    payroll_runs_count: int
    by_department: List[BreakdownItem] = []
    by_legal_entity: List[BreakdownItem] = []
    by_period: List[TrendPoint] = []


class PerformanceMetricOut(BaseModel):
    total_reviews: int
    completed_reviews: int
    pending_reviews: int
    review_completion_rate: float
    goal_completion_rate: float
    rating_distribution: List[BreakdownItem] = []
    by_department: List[BreakdownItem] = []


class LearningMetricOut(BaseModel):
    total_courses: int
    total_enrollments: int
    completed_enrollments: int
    completion_rate: float
    training_hours: float
    mandatory_training_compliance_rate: float
    certifications_awarded: int


class ComplianceMetricOut(BaseModel):
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    compliance_score_percent: float
    statutory_filings_by_status: List[BreakdownItem] = []
    statutory_payments_by_status: List[BreakdownItem] = []
    tax_declarations_completion_percent: float


class WorkforceCostMetricOut(BaseModel):
    employee_compensation: float
    employer_statutory_cost: float
    benefits_cost: float
    training_cost: float
    recruitment_cost: float
    total_workforce_cost: float
    by_department: List[BreakdownItem] = []
    by_legal_entity: List[BreakdownItem] = []
    by_month: List[TrendPoint] = []


class ExecutiveDashboardOut(BaseModel):
    headcount: HeadcountMetricOut
    attrition: AttritionMetricOut
    attendance: AttendanceMetricOut
    leave: LeaveMetricOut
    recruitment: RecruitmentMetricOut
    workforce_cost: WorkforceCostMetricOut
    compliance: ComplianceMetricOut
    pending_hr_tasks_count: int


# ---------------------------------------------------------------------------
# Report Definition Schemas
# ---------------------------------------------------------------------------

class ReportDefinitionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    report_type: str = "WORKFORCE"
    metrics: Optional[List[str]] = None
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    grouping: Optional[List[str]] = None
    sorting: Optional[List[Dict[str, str]]] = None
    visibility: str = "PRIVATE"
    allowed_roles: Optional[List[str]] = None
    min_aggregation_threshold: int = 3


class ReportDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metrics: Optional[List[str]] = None
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    grouping: Optional[List[str]] = None
    sorting: Optional[List[Dict[str, str]]] = None
    visibility: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    min_aggregation_threshold: Optional[int] = None


class ReportDefinitionOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    report_type: str
    metrics: Optional[List[str]] = None
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    grouping: Optional[List[str]] = None
    sorting: Optional[List[Dict[str, str]]] = None
    visibility: str
    owner_id: str
    allowed_roles: Optional[List[str]] = None
    min_aggregation_threshold: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Dashboard & Widget Schemas
# ---------------------------------------------------------------------------

class WidgetCreate(BaseModel):
    title: str
    widget_type: str = "KPI_CARD"
    metric: str
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    report_definition_id: Optional[str] = None
    position: int = 0


class WidgetUpdate(BaseModel):
    title: Optional[str] = None
    widget_type: Optional[str] = None
    metric: Optional[str] = None
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    position: Optional[int] = None


class WidgetOut(BaseModel):
    id: str
    tenant_id: str
    dashboard_id: str
    title: str
    widget_type: str
    metric: str
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    report_definition_id: Optional[str] = None
    position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dashboard_type: str = "HR"
    layout: Optional[Dict[str, Any]] = None
    is_default: bool = False
    visibility: str = "PRIVATE"
    allowed_roles: Optional[List[str]] = None
    widgets: Optional[List[WidgetCreate]] = None


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dashboard_type: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    visibility: Optional[str] = None
    allowed_roles: Optional[List[str]] = None


class DashboardOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    dashboard_type: str
    layout: Optional[Dict[str, Any]] = None
    is_default: bool
    visibility: str
    owner_id: str
    allowed_roles: Optional[List[str]] = None
    widgets: List[WidgetOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Scheduled Report Schemas
# ---------------------------------------------------------------------------

class ScheduledReportCreate(BaseModel):
    report_definition_id: str
    frequency: str = "MONTHLY"
    recipients: List[str]
    format: str = "CSV"
    status: str = "ACTIVE"
    next_run_at: Optional[datetime] = None


class ScheduledReportUpdate(BaseModel):
    frequency: Optional[str] = None
    recipients: Optional[List[str]] = None
    format: Optional[str] = None
    status: Optional[str] = None
    next_run_at: Optional[datetime] = None


class ScheduledReportOut(BaseModel):
    id: str
    tenant_id: str
    report_definition_id: str
    frequency: str
    recipients: List[str]
    format: str
    status: str
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Report Execution & Export Schemas
# ---------------------------------------------------------------------------

class ReportExecutionCreate(BaseModel):
    report_definition_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    format: str = "CSV"


class ReportExecutionOut(BaseModel):
    id: str
    tenant_id: str
    report_definition_id: str
    scheduled_report_id: Optional[str] = None
    executed_by: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    format: str
    row_count: int
    execution_time_ms: int
    parameters: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportExportOut(BaseModel):
    id: str
    tenant_id: str
    execution_id: str
    export_format: str
    file_name: str
    file_size: int
    status: str
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
