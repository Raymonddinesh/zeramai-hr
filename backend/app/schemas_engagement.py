"""
schemas_engagement.py - Module 19: Employee Engagement, Surveys, Recognition & Organizational Culture Schemas
Zeramai Enterprise HRMS
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models_engagement import (
    SurveyType,
    SurveyTemplateStatus,
    SurveyQuestionType,
    SurveyCampaignStatus,
    SurveyAudienceType,
    SurveyVisibilityType,
    ParticipationStatus,
    FeedbackCategory,
    FeedbackVisibility,
    FeedbackStatus,
    SuggestionStatus,
    ActionPlanStatus,
    RecognitionType,
    AwardNominationStatus,
    CultureInitiativeCategory,
)


# ---------------------------------------------------------------------------
# 1. Survey Templates & Questions
# ---------------------------------------------------------------------------

class SurveyQuestionBase(BaseModel):
    question_type: SurveyQuestionType = SurveyQuestionType.RATING
    question_text: str
    category: str = "GENERAL"
    sequence: int = 1
    required: bool = True
    anonymous: bool = True
    scale_min: Optional[int] = 1
    scale_max: Optional[int] = 5
    options_json: Optional[List[str]] = None


class SurveyQuestionCreate(SurveyQuestionBase):
    template_id: Optional[str] = None


class SurveyQuestionResponse(SurveyQuestionBase):
    id: str
    tenant_id: str
    template_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SurveyTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    survey_type: SurveyType = SurveyType.ENGAGEMENT
    estimated_minutes: int = 10
    anonymous_by_default: bool = True


class SurveyTemplateCreate(SurveyTemplateBase):
    questions: Optional[List[SurveyQuestionBase]] = []


class SurveyTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    survey_type: Optional[SurveyType] = None
    status: Optional[SurveyTemplateStatus] = None
    estimated_minutes: Optional[int] = None
    anonymous_by_default: Optional[bool] = None


class SurveyTemplateResponse(SurveyTemplateBase):
    id: str
    tenant_id: str
    status: SurveyTemplateStatus
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    questions: List[SurveyQuestionResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 2. Survey Campaigns & Recipients
# ---------------------------------------------------------------------------

class SurveyCampaignBase(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None
    audience_type: SurveyAudienceType = SurveyAudienceType.ALL_EMPLOYEES
    target_department_id: Optional[str] = None
    target_organization_unit_id: Optional[str] = None
    start_at: datetime
    end_at: datetime
    anonymous: bool = True
    minimum_anonymity_threshold: int = 5
    visibility_type: SurveyVisibilityType = SurveyVisibilityType.ANONYMOUS


class SurveyCampaignCreate(SurveyCampaignBase):
    pass


class SurveyCampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SurveyCampaignStatus] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    minimum_anonymity_threshold: Optional[int] = None


class SurveyCampaignResponse(SurveyCampaignBase):
    id: str
    tenant_id: str
    status: SurveyCampaignStatus
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    template_name: Optional[str] = None
    recipient_count: int = 0
    response_count: int = 0

    class Config:
        from_attributes = True


class SurveyRecipientResponse(BaseModel):
    id: str
    tenant_id: str
    campaign_id: str
    person_id: str
    invitation_sent_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    participation_status: ParticipationStatus
    created_at: datetime
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 3. Survey Submission & Responses
# ---------------------------------------------------------------------------

class SurveyAnswerInput(BaseModel):
    question_id: str
    answer_text: Optional[str] = None
    answer_numeric: Optional[float] = None
    answer_option: Optional[str] = None


class SurveySubmitRequest(BaseModel):
    answers: List[SurveyAnswerInput]
    completion_time_seconds: Optional[int] = None
    recipient_token: Optional[str] = None


class SurveyAnswerResponse(BaseModel):
    id: str
    question_id: str
    answer_text: Optional[str] = None
    answer_numeric: Optional[float] = None
    answer_option: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SurveyResponseItem(BaseModel):
    id: str
    campaign_id: str
    recipient_id: Optional[str] = None  # None for anonymous
    submitted_at: datetime
    completion_time_seconds: Optional[int] = None
    answers: List[SurveyAnswerResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 4. Analytics & Metrics
# ---------------------------------------------------------------------------

class QuestionMetric(BaseModel):
    question_id: str
    question_text: str
    category: str
    question_type: str
    response_count: int
    average_score: Optional[float] = None
    favorable_percent: Optional[float] = None
    neutral_percent: Optional[float] = None
    unfavorable_percent: Optional[float] = None


class CategoryScore(BaseModel):
    category: str
    average_score: float
    favorable_percent: float
    response_count: int


class CampaignAnalyticsResponse(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    anonymous: bool
    minimum_anonymity_threshold: int
    invited_count: int
    started_count: int
    completed_count: int
    participation_rate: float
    completion_rate: float
    average_completion_time_seconds: Optional[float] = None
    overall_engagement_score: Optional[float] = None
    enps_score: Optional[float] = None
    sample_size: int
    is_threshold_met: bool
    threshold_notice: Optional[str] = None
    category_scores: List[CategoryScore] = []
    question_metrics: List[QuestionMetric] = []
    metric_labels: Dict[str, str] = Field(
        default_factory=lambda: {
            "type": "SURVEY RESULT",
            "aggregation": "AGGREGATED RESULT",
            "sample_size": "SAMPLE SIZE",
        }
    )


# ---------------------------------------------------------------------------
# 5. Feedback & Suggestion Box
# ---------------------------------------------------------------------------

class EmployeeFeedbackCreate(BaseModel):
    category: FeedbackCategory = FeedbackCategory.GENERAL
    subject: str
    message: str
    visibility: FeedbackVisibility = FeedbackVisibility.PRIVATE_HR


class EmployeeFeedbackUpdate(BaseModel):
    status: Optional[FeedbackStatus] = None
    admin_notes: Optional[str] = None
    is_grievance_referral: Optional[bool] = None
    er_case_id: Optional[str] = None
    grievance_case_id: Optional[str] = None


class EmployeeFeedbackResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    category: FeedbackCategory
    subject: str
    message: str
    visibility: FeedbackVisibility
    status: FeedbackStatus
    is_grievance_referral: bool
    er_case_id: Optional[str] = None
    grievance_case_id: Optional[str] = None
    submitted_at: datetime
    resolved_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


class EmployeeSuggestionCreate(BaseModel):
    category: str = "GENERAL"
    title: str
    description: str
    anonymous: bool = False


class EmployeeSuggestionUpdate(BaseModel):
    status: Optional[SuggestionStatus] = None
    admin_notes: Optional[str] = None


class EmployeeSuggestionResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: Optional[str] = None
    category: str
    title: str
    description: str
    anonymous: bool
    status: SuggestionStatus
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    admin_notes: Optional[str] = None
    votes_count: int
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 6. Action Plans & Action Items
# ---------------------------------------------------------------------------

class EngagementActionItemCreate(BaseModel):
    action: str
    owner_user_id: str
    due_date: Optional[date] = None
    notes: Optional[str] = None


class EngagementActionItemUpdate(BaseModel):
    action: Optional[str] = None
    owner_user_id: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[ActionPlanStatus] = None
    notes: Optional[str] = None


class EngagementActionItemResponse(BaseModel):
    id: str
    tenant_id: str
    action_plan_id: str
    action: str
    owner_user_id: str
    due_date: Optional[date] = None
    status: ActionPlanStatus
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class EngagementActionPlanCreate(BaseModel):
    campaign_id: Optional[str] = None
    organization_unit_id: Optional[str] = None
    department_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    owner_user_id: str
    due_date: Optional[date] = None
    items: Optional[List[EngagementActionItemCreate]] = []


class EngagementActionPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner_user_id: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[ActionPlanStatus] = None


class EngagementActionPlanResponse(BaseModel):
    id: str
    tenant_id: str
    campaign_id: Optional[str] = None
    organization_unit_id: Optional[str] = None
    department_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    owner_user_id: str
    due_date: Optional[date] = None
    status: ActionPlanStatus
    created_at: datetime
    updated_at: datetime
    owner_name: Optional[str] = None
    items: List[EngagementActionItemResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 7. Recognition Programs & Awards
# ---------------------------------------------------------------------------

class RecognitionProgramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    recognition_type: RecognitionType = RecognitionType.PEER
    points_reward: int = 0


class RecognitionProgramResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    status: str
    recognition_type: RecognitionType
    points_reward: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecognitionAwardCreate(BaseModel):
    program_id: str
    recipient_person_id: str
    title: str
    message: str
    category: str = "VALUES"
    visibility: str = "PUBLIC"


class RecognitionAwardResponse(BaseModel):
    id: str
    tenant_id: str
    program_id: str
    giver_person_id: str
    recipient_person_id: str
    title: str
    message: str
    category: str
    visibility: str
    awarded_at: datetime
    status: str
    created_at: datetime
    giver_name: Optional[str] = None
    recipient_name: Optional[str] = None

    class Config:
        from_attributes = True


class AwardDefinitionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    criteria: Optional[str] = None
    frequency: str = "ANNUAL"
    active: bool = True


class AwardDefinitionResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    criteria: Optional[str] = None
    frequency: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AwardNominationCreate(BaseModel):
    award_definition_id: str
    nominee_person_id: str
    justification: str


class AwardNominationReview(BaseModel):
    status: AwardNominationStatus
    review_comments: Optional[str] = None


class AwardNominationResponse(BaseModel):
    id: str
    tenant_id: str
    award_definition_id: str
    nominee_person_id: str
    nominated_by: str
    justification: str
    status: AwardNominationStatus
    nominated_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_comments: Optional[str] = None
    created_at: datetime
    award_name: Optional[str] = None
    nominee_name: Optional[str] = None
    nominator_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 8. Culture Initiatives & Participation
# ---------------------------------------------------------------------------

class CultureInitiativeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: CultureInitiativeCategory = CultureInitiativeCategory.COMMUNITY
    owner_user_id: str
    start_date: date
    end_date: Optional[date] = None
    target_participants: Optional[int] = None


class CultureInitiativeResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    category: CultureInitiativeCategory
    owner_user_id: str
    start_date: date
    end_date: Optional[date] = None
    status: str
    target_participants: Optional[int] = None
    participant_count: int = 0
    created_at: datetime
    updated_at: datetime
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class CultureParticipationCreate(BaseModel):
    initiative_id: str
    participation_type: str = "ATTENDEE"
    feedback: Optional[str] = None


class CultureParticipationResponse(BaseModel):
    id: str
    tenant_id: str
    initiative_id: str
    person_id: str
    participation_type: str
    feedback: Optional[str] = None
    participated_at: datetime
    created_at: datetime
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 9. Dashboards
# ---------------------------------------------------------------------------

class EmployeeExperienceDashboard(BaseModel):
    available_surveys: List[Dict[str, Any]] = []
    completed_surveys: List[Dict[str, Any]] = []
    recognitions_received: List[RecognitionAwardResponse] = []
    recognitions_given: List[RecognitionAwardResponse] = []
    my_suggestions: List[EmployeeSuggestionResponse] = []
    culture_initiatives: List[CultureInitiativeResponse] = []
    my_action_items: List[EngagementActionItemResponse] = []


class ManagerTeamEngagementDashboard(BaseModel):
    manager_name: str
    team_size: int
    minimum_anonymity_threshold: int = 5
    is_threshold_met: bool
    threshold_notice: Optional[str] = None
    team_participation_rate: Optional[float] = None
    team_engagement_score: Optional[float] = None
    category_scores: List[CategoryScore] = []
    active_action_plans: List[EngagementActionPlanResponse] = []
    recent_team_recognition: List[RecognitionAwardResponse] = []
    metric_labels: Dict[str, str] = Field(
        default_factory=lambda: {
            "type": "SURVEY RESULT",
            "aggregation": "AGGREGATED RESULT",
            "sample_size": "SAMPLE SIZE",
        }
    )


class EngagementHRDashboard(BaseModel):
    active_campaigns_count: int
    total_responses_collected: int
    average_participation_rate: float
    overall_engagement_score: Optional[float] = None
    average_enps: Optional[float] = None
    open_action_plans_count: int
    total_recognitions_awarded: int
    active_culture_initiatives_count: int
    recent_campaigns: List[SurveyCampaignResponse] = []
    pending_suggestions_count: int
