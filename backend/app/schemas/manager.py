from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

class TeamMemberOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    full_name: str
    designation: Optional[str]
    department: Optional[str]
    joining_date: Optional[date]
    status: Optional[str]

class LeavePendingOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    leave_type: str
    start_date: date
    end_date: date
    days: float
    reason: Optional[str]
    status: str

class AttendanceExceptionOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    date: date
    status: str
    notes: Optional[str]

class OnboardingTaskPendingOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    title: str
    category: str
    assignee_role: str
    status: str
    due_date: Optional[date]

class EvaluationPendingOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    review_cycle_id: str
    reviewer_id: str
    status: str

class CandidateOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    hiring_manager_id: Optional[str]
    applied_position: Optional[str]
    department: Optional[str]
    status: Optional[str]

class ManagerDashboardOut(BaseModel):
    team_headcount: int
    active_employees: int
    pending_leaves: List[LeavePendingOut]
    attendance_exceptions: List[AttendanceExceptionOut]
    onboarding_tasks: List[OnboardingTaskPendingOut]
    pending_evaluations: List[EvaluationPendingOut]
    candidates: List[CandidateOut]
