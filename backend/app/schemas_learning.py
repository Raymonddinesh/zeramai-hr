"""
schemas_learning.py - Module 18: Enterprise Learning, Skills & Career Development Schemas
Zeramai Enterprise HRMS
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Training Provider Schemas
# ---------------------------------------------------------------------------

class TrainingProviderBase(BaseModel):
    name: str = Field(..., max_length=255)
    provider_type: str = Field("INTERNAL", max_length=50)
    website: Optional[str] = None
    contact_reference: Optional[str] = None
    active: bool = True


class TrainingProviderCreate(TrainingProviderBase):
    pass


class TrainingProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    website: Optional[str] = None
    contact_reference: Optional[str] = None
    active: Optional[bool] = None


class TrainingProviderResponse(TrainingProviderBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Learning Course & Module Schemas
# ---------------------------------------------------------------------------

class CourseContentBase(BaseModel):
    content_type: str = Field("DOCUMENT", max_length=50)
    title: str = Field(..., max_length=255)
    content_reference: Optional[str] = None
    duration_minutes: int = 10
    sequence: int = 1
    required: bool = True


class CourseContentCreate(CourseContentBase):
    pass


class CourseContentResponse(CourseContentBase):
    id: str
    module_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningModuleBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    sequence: int = 1
    duration_minutes: int = 30
    mandatory: bool = True


class LearningModuleCreate(LearningModuleBase):
    contents: Optional[List[CourseContentCreate]] = None


class LearningModuleResponse(LearningModuleBase):
    id: str
    course_id: str
    created_at: datetime
    updated_at: datetime
    contents: Optional[List[CourseContentResponse]] = []

    class Config:
        from_attributes = True


class LearningCourseBase(BaseModel):
    course_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: str = Field("GENERAL", max_length=100)
    learning_type: str = Field("COURSE", max_length=50)
    difficulty: str = Field("INTERMEDIATE", max_length=50)
    duration_minutes: int = 60
    provider_id: Optional[str] = None
    delivery_mode: str = Field("ONLINE", max_length=50)
    language: str = Field("en", max_length=20)
    status: str = Field("DRAFT", max_length=32)


class LearningCourseCreate(LearningCourseBase):
    modules: Optional[List[LearningModuleCreate]] = None


class LearningCourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    learning_type: Optional[str] = None
    difficulty: Optional[str] = None
    duration_minutes: Optional[int] = None
    provider_id: Optional[str] = None
    delivery_mode: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None


class LearningCourseResponse(LearningCourseBase):
    id: str
    tenant_id: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    provider_name: Optional[str] = None
    module_count: int = 0
    modules: Optional[List[LearningModuleResponse]] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Learning Path Schemas
# ---------------------------------------------------------------------------

class LearningPathCourseItem(BaseModel):
    course_id: str
    sequence: int = 1
    mandatory: bool = True


class LearningPathBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    target_role: Optional[str] = None
    target_job_family: Optional[str] = None
    status: str = Field("DRAFT", max_length=32)


class LearningPathCreate(LearningPathBase):
    courses: Optional[List[LearningPathCourseItem]] = None


class LearningPathUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_role: Optional[str] = None
    target_job_family: Optional[str] = None
    status: Optional[str] = None


class LearningPathCourseResponse(BaseModel):
    id: str
    learning_path_id: str
    course_id: str
    sequence: int
    mandatory: bool
    course_title: Optional[str] = None
    course_code: Optional[str] = None

    class Config:
        from_attributes = True


class LearningPathResponse(LearningPathBase):
    id: str
    tenant_id: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    path_courses: Optional[List[LearningPathCourseResponse]] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Course Skill Mapping Schemas
# ---------------------------------------------------------------------------

class CourseSkillMappingCreate(BaseModel):
    course_id: str
    skill_id: str
    target_skill_level_id: Optional[str] = None
    proficiency_gain: float = 0.5


class CourseSkillMappingResponse(BaseModel):
    id: str
    tenant_id: str
    course_id: str
    skill_id: str
    target_skill_level_id: Optional[str]
    proficiency_gain: float
    created_at: datetime
    skill_name: Optional[str] = None
    skill_code: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Learning Enrollment & Progress Schemas
# ---------------------------------------------------------------------------

class LearningEnrollmentCreate(BaseModel):
    person_id: str
    course_id: Optional[str] = None
    learning_path_id: Optional[str] = None
    enrollment_type: str = "SELF"
    due_at: Optional[datetime] = None


class LearningEnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    completion_score: Optional[float] = None


class LearningProgressUpdate(BaseModel):
    progress_percentage: float
    time_spent_minutes: int = 0


class LearningProgressResponse(BaseModel):
    id: str
    tenant_id: str
    enrollment_id: str
    module_id: str
    progress_percentage: float
    started_at: datetime
    completed_at: Optional[datetime]
    time_spent_minutes: int
    last_accessed_at: datetime

    class Config:
        from_attributes = True


class LearningEnrollmentResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    course_id: Optional[str]
    learning_path_id: Optional[str]
    enrollment_type: str
    status: str
    enrolled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    due_at: Optional[datetime]
    progress_percentage: float
    completion_score: Optional[float]
    assigned_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    course_title: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Assessment & Question Schemas
# ---------------------------------------------------------------------------

class AssessmentQuestionCreate(BaseModel):
    question_type: str = "MULTIPLE_CHOICE"
    question_text: str
    options_json: Optional[str] = None  # JSON list string
    correct_answer: str
    sequence: int = 1
    points: float = 1.0


class AssessmentQuestionResponse(BaseModel):
    id: str
    assessment_id: str
    question_type: str
    question_text: str
    options_json: Optional[str]
    # NOTE: correct_answer is strictly excluded here for employee exam security!
    sequence: int
    points: float

    class Config:
        from_attributes = True


class LearningAssessmentCreate(BaseModel):
    course_id: str
    title: str = Field(..., max_length=255)
    passing_score: float = 70.0
    attempts_allowed: int = 3
    duration_minutes: Optional[int] = None
    questions: Optional[List[AssessmentQuestionCreate]] = None


class LearningAssessmentResponse(BaseModel):
    id: str
    tenant_id: str
    course_id: str
    title: str
    passing_score: float
    attempts_allowed: int
    duration_minutes: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime
    question_count: int = 0
    questions: Optional[List[AssessmentQuestionResponse]] = []

    class Config:
        from_attributes = True


class AssessmentAttemptCreate(BaseModel):
    assessment_id: str
    enrollment_id: Optional[str] = None
    answers: Dict[str, str]  # question_id -> candidate answer string


class AssessmentAttemptResponse(BaseModel):
    id: str
    tenant_id: str
    assessment_id: str
    person_id: str
    enrollment_id: Optional[str]
    attempt_number: int
    score: float
    passed: bool
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Certification Schemas
# ---------------------------------------------------------------------------

class CertificationBase(BaseModel):
    name: str = Field(..., max_length=255)
    issuing_body: str = Field(..., max_length=255)
    description: Optional[str] = None
    validity_months: Optional[int] = None
    status: str = "ACTIVE"


class CertificationCreate(CertificationBase):
    pass


class CertificationResponse(CertificationBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmployeeCertificationCreate(BaseModel):
    person_id: str
    certification_id: str
    credential_number: Optional[str] = None
    issued_date: date
    expiry_date: Optional[date] = None
    document_reference: Optional[str] = None


class EmployeeCertificationVerify(BaseModel):
    verification_status: str = "VERIFIED"  # VERIFIED or REJECTED


class EmployeeCertificationResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    certification_id: str
    credential_number: Optional[str]
    issued_date: date
    expiry_date: Optional[date]
    verification_status: str
    document_reference: Optional[str]
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    certification_name: Optional[str] = None
    issuing_body: Optional[str] = None
    person_name: Optional[str] = None
    is_expired: bool = False

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Training Requirement & Assignment Schemas
# ---------------------------------------------------------------------------

class TrainingRequirementCreate(BaseModel):
    name: str = Field(..., max_length=255)
    course_id: str
    applicability_rule: str = "ALL_EMPLOYEES"
    due_days: int = 30
    recurrence: str = "ANNUAL"
    mandatory: bool = True
    compliance_reference: Optional[str] = None


class TrainingRequirementResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    course_id: str
    applicability_rule: str
    due_days: int
    recurrence: str
    mandatory: bool
    compliance_reference: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    course_title: Optional[str] = None

    class Config:
        from_attributes = True


class TrainingAssignmentCreate(BaseModel):
    requirement_id: str
    person_id: str
    due_at: datetime


class TrainingAssignmentResponse(BaseModel):
    id: str
    tenant_id: str
    requirement_id: str
    person_id: str
    assigned_at: datetime
    due_at: datetime
    status: str
    completed_at: Optional[datetime]
    requirement_name: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Learning Plan Schemas
# ---------------------------------------------------------------------------

class LearningPlanItemCreate(BaseModel):
    course_id: Optional[str] = None
    learning_path_id: Optional[str] = None
    skill_id: Optional[str] = None
    target_skill_level_id: Optional[str] = None
    target_date: date
    priority: str = "MEDIUM"


class LearningPlanCreate(BaseModel):
    person_id: str
    name: str = Field(..., max_length=255)
    period_start: date
    period_end: date
    items: Optional[List[LearningPlanItemCreate]] = None


class LearningPlanItemResponse(BaseModel):
    id: str
    plan_id: str
    course_id: Optional[str]
    learning_path_id: Optional[str]
    skill_id: Optional[str]
    target_skill_level_id: Optional[str]
    target_date: date
    priority: str
    status: str
    course_title: Optional[str] = None
    skill_name: Optional[str] = None

    class Config:
        from_attributes = True


class LearningPlanResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    name: str
    period_start: date
    period_end: date
    status: str
    created_by: Optional[str]
    approved_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None
    items: Optional[List[LearningPlanItemResponse]] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Individual Development Plan (IDP) & Goals
# ---------------------------------------------------------------------------

class DevelopmentGoalCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    skill_id: Optional[str] = None
    target_level_id: Optional[str] = None
    due_date: Optional[date] = None


class DevelopmentPlanCreate(BaseModel):
    person_id: str
    current_role: str = Field(..., max_length=255)
    target_role: Optional[str] = None
    career_direction: Optional[str] = None
    review_period: str = "FY27"
    employee_notes: Optional[str] = None
    manager_notes: Optional[str] = None
    goals: Optional[List[DevelopmentGoalCreate]] = None


class DevelopmentGoalResponse(BaseModel):
    id: str
    development_plan_id: str
    title: str
    description: Optional[str]
    skill_id: Optional[str]
    target_level_id: Optional[str]
    due_date: Optional[date]
    status: str
    progress_percentage: float
    skill_name: Optional[str] = None

    class Config:
        from_attributes = True


class DevelopmentPlanResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    current_role: str
    target_role: Optional[str]
    career_direction: Optional[str]
    review_period: str
    status: str
    employee_notes: Optional[str]
    manager_notes: Optional[str] = None  # Protected / Redacted for normal employee view
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None
    goals: Optional[List[DevelopmentGoalResponse]] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Career Framework, Levels & Paths
# ---------------------------------------------------------------------------

class CareerLevelCreate(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=100)
    sequence: int = 1
    description: Optional[str] = None
    expected_skill_profile: Optional[str] = None


class CareerLevelResponse(CareerLevelCreate):
    id: str
    framework_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CareerPathCreate(BaseModel):
    from_level_id: str
    to_level_id: str
    typical_requirements: Optional[str] = None


class CareerPathResponse(CareerPathCreate):
    id: str
    framework_id: str
    from_level_name: Optional[str] = None
    to_level_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CareerFrameworkCreate(BaseModel):
    name: str = Field(..., max_length=255)
    job_family: str = Field(..., max_length=100)
    description: Optional[str] = None
    levels: Optional[List[CareerLevelCreate]] = None


class CareerFrameworkResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    job_family: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    levels: Optional[List[CareerLevelResponse]] = []
    paths: Optional[List[CareerPathResponse]] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Career Opportunities & Applications
# ---------------------------------------------------------------------------

class CareerOpportunityCreate(BaseModel):
    position_id: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    required_skills: Optional[str] = None
    required_level: Optional[str] = None
    eligibility_rules: Optional[str] = None
    application_deadline: Optional[date] = None


class CareerOpportunityResponse(BaseModel):
    id: str
    tenant_id: str
    position_id: Optional[str]
    title: str
    description: Optional[str]
    required_skills: Optional[str]
    required_level: Optional[str]
    eligibility_rules: Optional[str]
    application_deadline: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime
    application_count: int = 0

    class Config:
        from_attributes = True


class CareerApplicationCreate(BaseModel):
    opportunity_id: str


class CareerApplicationResponse(BaseModel):
    id: str
    tenant_id: str
    opportunity_id: str
    person_id: str
    status: str
    applied_at: datetime
    withdrawn_at: Optional[datetime]
    opportunity_title: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Mentoring Program & Relationship Schemas
# ---------------------------------------------------------------------------

class MentoringProgramCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    duration_months: int = 6


class MentoringProgramResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    duration_months: int
    status: str
    created_at: datetime
    updated_at: datetime
    active_pairs_count: int = 0

    class Config:
        from_attributes = True


class MentoringRelationshipCreate(BaseModel):
    program_id: str
    mentor_person_id: str
    mentee_person_id: str
    start_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None
    goals: Optional[str] = None


class MentoringRelationshipResponse(BaseModel):
    id: str
    tenant_id: str
    program_id: str
    mentor_person_id: str
    mentee_person_id: str
    start_date: date
    end_date: Optional[date]
    status: str
    goals: Optional[str]
    mentor_name: Optional[str] = None
    mentee_name: Optional[str] = None
    program_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Skill Gap Remediation & Skill Evidence Schemas
# ---------------------------------------------------------------------------

class SkillDevelopmentActionCreate(BaseModel):
    person_id: str
    skill_id: str
    skill_gap_reference: Optional[str] = None
    action_type: str = "COURSE"
    course_id: Optional[str] = None
    mentoring_program_id: Optional[str] = None
    target_level_id: Optional[str] = None
    due_date: Optional[date] = None


class SkillDevelopmentActionResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    skill_id: str
    skill_gap_reference: Optional[str]
    action_type: str
    course_id: Optional[str]
    mentoring_program_id: Optional[str]
    target_level_id: Optional[str]
    due_date: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime
    skill_name: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


class SkillEvidenceCreate(BaseModel):
    person_id: str
    skill_id: str
    evidence_type: str = "COURSE"
    source_reference: Optional[str] = None
    evidence_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None


class SkillEvidenceResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    skill_id: str
    evidence_type: str
    source_reference: Optional[str]
    evidence_date: date
    verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    skill_name: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Analytics & Dashboards
# ---------------------------------------------------------------------------

class LearningAnalyticsResponse(BaseModel):
    total_courses: int
    published_courses: int
    total_enrollments: int
    completed_enrollments: int
    completion_rate_pct: float
    total_training_hours: float
    mandatory_assignments_count: int
    mandatory_completed_count: int
    mandatory_compliance_rate_pct: float
    expiring_certifications_30d: int
    active_mentoring_relationships: int
    skill_evidence_records_count: int


class EmployeeLearningDashboard(BaseModel):
    assigned_courses_count: int
    in_progress_courses_count: int
    completed_courses_count: int
    active_certifications_count: int
    expiring_certifications_count: int
    development_goals_count: int
    active_mentoring_count: int
    recent_enrollments: List[LearningEnrollmentResponse] = []
    my_certifications: List[EmployeeCertificationResponse] = []


class ManagerTeamLearningDashboard(BaseModel):
    team_member_count: int
    team_enrollments_count: int
    team_completions_count: int
    team_completion_rate_pct: float
    overdue_mandatory_count: int
    team_expiring_certifications: int
    team_skill_gaps_count: int
