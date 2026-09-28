from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import CandidateStatus, EngagementStatus, EngagementType, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    role: UserRole
    is_active: bool


class CandidateCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    applied_position: str | None = None
    department: str | None = None
    recruiter: str | None = None
    highest_qualification: str | None = None
    college_university: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    person_id: str
    applied_position: str | None
    department: str | None
    status: CandidateStatus
    application_date: date | None


class ConvertToTraineeRequest(BaseModel):
    designation: str = "Engineering Trainee"
    department: str
    start_date: date
    duration_months: int = 6
    monthly_stipend: float = 5000.00
    reporting_manager_id: str | None = None
    work_location: str | None = None


class EngagementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    person_id: str
    engagement_type: EngagementType
    designation: str
    department: str
    start_date: date
    end_date: date | None
    stipend_amount: float | None
    stipend_currency: str
    status: EngagementStatus
