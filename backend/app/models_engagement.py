"""
models_engagement.py - Module 19: Employee Engagement, Surveys, Recognition & Organizational Culture Models
Zeramai Enterprise HRMS
"""
import uuid
import enum
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    Enum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SurveyType(str, enum.Enum):
    ENGAGEMENT = "ENGAGEMENT"
    PULSE = "PULSE"
    ONBOARDING = "ONBOARDING"
    EXIT = "EXIT"
    TRAINING_FEEDBACK = "TRAINING_FEEDBACK"
    EVENT_FEEDBACK = "EVENT_FEEDBACK"
    CUSTOM = "CUSTOM"


class SurveyTemplateStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class SurveyQuestionType(str, enum.Enum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTI_CHOICE = "MULTI_CHOICE"
    TEXT = "TEXT"
    RATING = "RATING"
    SCALE = "SCALE"
    YES_NO = "YES_NO"
    NPS = "NPS"


class SurveyCampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class SurveyAudienceType(str, enum.Enum):
    ALL_EMPLOYEES = "ALL_EMPLOYEES"
    DEPARTMENT = "DEPARTMENT"
    ORGANIZATION_UNIT = "ORGANIZATION_UNIT"
    MANAGER_TEAM = "MANAGER_TEAM"
    CUSTOM = "CUSTOM"


class SurveyVisibilityType(str, enum.Enum):
    PUBLIC = "PUBLIC"
    CONFIDENTIAL = "CONFIDENTIAL"
    ANONYMOUS = "ANONYMOUS"


class ParticipationStatus(str, enum.Enum):
    INVITED = "INVITED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    DECLINED = "DECLINED"


class FeedbackCategory(str, enum.Enum):
    PROCESS = "PROCESS"
    POLICY = "POLICY"
    WORKPLACE = "WORKPLACE"
    MANAGEMENT = "MANAGEMENT"
    CULTURE = "CULTURE"
    TOOLS = "TOOLS"
    GENERAL = "GENERAL"


class FeedbackVisibility(str, enum.Enum):
    PRIVATE_HR = "PRIVATE_HR"
    MANAGER = "MANAGER"
    PUBLIC_AGGREGATED = "PUBLIC_AGGREGATED"


class FeedbackStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTIONED = "ACTIONED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SuggestionStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    IMPLEMENTED = "IMPLEMENTED"
    DECLINED = "DECLINED"
    ARCHIVED = "ARCHIVED"


class ActionPlanStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RecognitionType(str, enum.Enum):
    PEER = "PEER"
    MANAGER = "MANAGER"
    TEAM = "TEAM"
    SERVICE = "SERVICE"
    ACHIEVEMENT = "ACHIEVEMENT"
    VALUES = "VALUES"


class AwardNominationStatus(str, enum.Enum):
    NOMINATED = "NOMINATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AWARDED = "AWARDED"
    WITHDRAWN = "WITHDRAWN"


class CultureInitiativeCategory(str, enum.Enum):
    VALUES = "VALUES"
    COLLABORATION = "COLLABORATION"
    LEARNING = "LEARNING"
    WELLBEING = "WELLBEING"
    COMMUNITY = "COMMUNITY"
    DIVERSITY = "DIVERSITY"
    INNOVATION = "INNOVATION"
    SOCIAL = "SOCIAL"


# ---------------------------------------------------------------------------
# 1. Survey Template & Questions
# ---------------------------------------------------------------------------

class SurveyTemplate(Base):
    __tablename__ = "survey_templates"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    survey_type = Column(Enum(SurveyType), default=SurveyType.ENGAGEMENT, nullable=False)
    status = Column(Enum(SurveyTemplateStatus), default=SurveyTemplateStatus.DRAFT, nullable=False)
    estimated_minutes = Column(Integer, default=10, nullable=False)
    anonymous_by_default = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    creator = relationship("User", foreign_keys=[created_by])
    questions = relationship("SurveyQuestion", back_populates="template", cascade="all, delete-orphan", order_by="SurveyQuestion.sequence")
    campaigns = relationship("SurveyCampaign", back_populates="template")


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("survey_templates.id"), nullable=False, index=True)
    question_type = Column(Enum(SurveyQuestionType), default=SurveyQuestionType.RATING, nullable=False)
    question_text = Column(Text, nullable=False)
    category = Column(String(100), default="GENERAL", nullable=False)
    sequence = Column(Integer, default=1, nullable=False)
    required = Column(Boolean, default=True, nullable=False)
    anonymous = Column(Boolean, default=True, nullable=False)
    scale_min = Column(Integer, default=1, nullable=True)
    scale_max = Column(Integer, default=5, nullable=True)
    options_json = Column(JSON, nullable=True)  # List of string options for choice questions
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    template = relationship("SurveyTemplate", back_populates="questions")


# ---------------------------------------------------------------------------
# 2. Survey Campaign & Distribution
# ---------------------------------------------------------------------------

class SurveyCampaign(Base):
    __tablename__ = "survey_campaigns"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("survey_templates.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    audience_type = Column(Enum(SurveyAudienceType), default=SurveyAudienceType.ALL_EMPLOYEES, nullable=False)
    target_department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    target_organization_unit_id = Column(String(36), nullable=True)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    anonymous = Column(Boolean, default=True, nullable=False)
    minimum_anonymity_threshold = Column(Integer, default=5, nullable=False)
    visibility_type = Column(Enum(SurveyVisibilityType), default=SurveyVisibilityType.ANONYMOUS, nullable=False)
    status = Column(Enum(SurveyCampaignStatus), default=SurveyCampaignStatus.DRAFT, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    template = relationship("SurveyTemplate", back_populates="campaigns")
    recipients = relationship("SurveyRecipient", back_populates="campaign", cascade="all, delete-orphan")
    responses = relationship("SurveyResponse", back_populates="campaign", cascade="all, delete-orphan")
    action_plans = relationship("EngagementActionPlan", back_populates="campaign")


class SurveyRecipient(Base):
    __tablename__ = "survey_recipients"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("survey_campaigns.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    invitation_sent_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    participation_status = Column(Enum(ParticipationStatus), default=ParticipationStatus.INVITED, nullable=False)
    response_token_hash = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("SurveyCampaign", back_populates="recipients")
    person = relationship("Person")


# ---------------------------------------------------------------------------
# 3. Survey Response & Answers (Anonymity-Preserving)
# ---------------------------------------------------------------------------

class SurveyResponse(Base):
    """
    SurveyResponse represents a single submission.
    For anonymous campaigns, recipient_id is explicitly NULL, and anonymous_response_id
    stores a one-way pseudorandom token that cannot be reverse-mapped to the respondent.
    """
    __tablename__ = "survey_responses"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("survey_campaigns.id"), nullable=False, index=True)
    recipient_id = Column(String(36), ForeignKey("survey_recipients.id"), nullable=True, index=True)  # NULL when anonymous
    anonymous_response_id = Column(String(64), nullable=True, index=True)
    department_id = Column(String(36), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("SurveyCampaign", back_populates="responses")
    recipient = relationship("SurveyRecipient")
    answers = relationship("SurveyAnswer", back_populates="response", cascade="all, delete-orphan")


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    response_id = Column(String(36), ForeignKey("survey_responses.id"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("survey_questions.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=True)
    answer_numeric = Column(Float, nullable=True)
    answer_option = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    response = relationship("SurveyResponse", back_populates="answers")
    question = relationship("SurveyQuestion")


# ---------------------------------------------------------------------------
# 4. Employee Feedback & Suggestion Box
# ---------------------------------------------------------------------------

class EmployeeFeedback(Base):
    __tablename__ = "employee_feedbacks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    category = Column(Enum(FeedbackCategory), default=FeedbackCategory.GENERAL, nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    visibility = Column(Enum(FeedbackVisibility), default=FeedbackVisibility.PRIVATE_HR, nullable=False)
    status = Column(Enum(FeedbackStatus), default=FeedbackStatus.SUBMITTED, nullable=False)
    is_grievance_referral = Column(Boolean, default=False, nullable=False)
    er_case_id = Column(String(36), ForeignKey("employee_relations_cases.id"), nullable=True)
    grievance_case_id = Column(String(36), ForeignKey("grievance_cases.id"), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    er_case = relationship("EmployeeRelationsCase", foreign_keys=[er_case_id])
    grievance_case = relationship("GrievanceCase", foreign_keys=[grievance_case_id])


class EmployeeSuggestion(Base):
    __tablename__ = "employee_suggestions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=True, index=True)  # NULL if anonymous
    category = Column(String(100), default="GENERAL", nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    anonymous = Column(Boolean, default=False, nullable=False)
    status = Column(Enum(SuggestionStatus), default=SuggestionStatus.SUBMITTED, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    votes_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ---------------------------------------------------------------------------
# 5. Engagement Action Plans
# ---------------------------------------------------------------------------

class EngagementActionPlan(Base):
    __tablename__ = "engagement_action_plans"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("survey_campaigns.id"), nullable=True, index=True)
    organization_unit_id = Column(String(36), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(ActionPlanStatus), default=ActionPlanStatus.OPEN, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    campaign = relationship("SurveyCampaign", back_populates="action_plans")
    owner = relationship("User", foreign_keys=[owner_user_id])
    department = relationship("Department", foreign_keys=[department_id])
    items = relationship("EngagementActionItem", back_populates="action_plan", cascade="all, delete-orphan")


class EngagementActionItem(Base):
    __tablename__ = "engagement_action_items"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    action_plan_id = Column(String(36), ForeignKey("engagement_action_plans.id"), nullable=False, index=True)
    action = Column(Text, nullable=False)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(ActionPlanStatus), default=ActionPlanStatus.OPEN, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    action_plan = relationship("EngagementActionPlan", back_populates="items")
    owner = relationship("User", foreign_keys=[owner_user_id])


# ---------------------------------------------------------------------------
# 6. Recognition & Awards
# ---------------------------------------------------------------------------

class RecognitionProgram(Base):
    __tablename__ = "recognition_programs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    recognition_type = Column(Enum(RecognitionType), default=RecognitionType.PEER, nullable=False)
    points_reward = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    awards = relationship("RecognitionAward", back_populates="program", cascade="all, delete-orphan")


class RecognitionAward(Base):
    __tablename__ = "recognition_awards"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    program_id = Column(String(36), ForeignKey("recognition_programs.id"), nullable=False, index=True)
    giver_person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    recipient_person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100), default="VALUES", nullable=False)
    visibility = Column(String(50), default="PUBLIC", nullable=False)
    awarded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="PUBLISHED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    program = relationship("RecognitionProgram", back_populates="awards")
    giver = relationship("Person", foreign_keys=[giver_person_id])
    recipient = relationship("Person", foreign_keys=[recipient_person_id])


class AwardDefinition(Base):
    __tablename__ = "award_definitions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    criteria = Column(Text, nullable=True)
    frequency = Column(String(50), default="ANNUAL", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    nominations = relationship("AwardNomination", back_populates="award_definition", cascade="all, delete-orphan")


class AwardNomination(Base):
    __tablename__ = "award_nominations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    award_definition_id = Column(String(36), ForeignKey("award_definitions.id"), nullable=False, index=True)
    nominee_person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    nominated_by = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    justification = Column(Text, nullable=False)
    status = Column(Enum(AwardNominationStatus), default=AwardNominationStatus.NOMINATED, nullable=False)
    nominated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    review_comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    award_definition = relationship("AwardDefinition", back_populates="nominations")
    nominee = relationship("Person", foreign_keys=[nominee_person_id])
    nominator = relationship("Person", foreign_keys=[nominated_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ---------------------------------------------------------------------------
# 7. Culture Initiatives & Participation
# ---------------------------------------------------------------------------

class CultureInitiative(Base):
    __tablename__ = "culture_initiatives"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(CultureInitiativeCategory), default=CultureInitiativeCategory.COMMUNITY, nullable=False)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    target_participants = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", foreign_keys=[owner_user_id])
    participants = relationship("CultureParticipation", back_populates="initiative", cascade="all, delete-orphan")


class CultureParticipation(Base):
    __tablename__ = "culture_participations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    initiative_id = Column(String(36), ForeignKey("culture_initiatives.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    participation_type = Column(String(100), default="ATTENDEE", nullable=False)
    feedback = Column(Text, nullable=True)
    participated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    initiative = relationship("CultureInitiative", back_populates="participants")
    person = relationship("Person")

    __table_args__ = (
        UniqueConstraint("initiative_id", "person_id", name="uq_culture_initiative_person"),
    )
