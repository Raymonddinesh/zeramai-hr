import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# ATS v2 & AI Talent Sourcing
# ---------------------------------------------------------------------------

class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class JobOpening(Base):
    __tablename__ = "job_openings"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    department = Column(String, nullable=False)
    location = Column(String, nullable=False)
    employment_type = Column(String, default="full_time")
    description = Column(Text, nullable=True)
    required_skills = Column(JSON, nullable=True)  # ["Python", "FastAPI", "React"]
    min_experience_years = Column(Integer, default=0)
    salary_range_min = Column(Numeric(12, 2), nullable=True)
    salary_range_max = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, default="USD")
    status = Column(Enum(JobStatus), default=JobStatus.OPEN, nullable=False)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    applications = relationship("CandidateApplication", back_populates="job_opening")


class ApplicationStage(str, enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER_SENT = "offer_sent"
    HIRED = "hired"
    REJECTED = "rejected"


class CandidateApplication(Base):
    __tablename__ = "candidate_applications"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("job_openings.id"), nullable=False)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    stage = Column(Enum(ApplicationStage), default=ApplicationStage.APPLIED, nullable=False)
    ai_match_score = Column(Numeric(5, 2), nullable=True)   # e.g., 92.50%
    ai_match_reasons = Column(JSON, nullable=True)         # ["Matched Python", "Matched React"]
    parsed_skills = Column(JSON, nullable=True)
    cover_letter = Column(Text, nullable=True)
    offer_letter_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    job_opening = relationship("JobOpening", back_populates="applications")


# ---------------------------------------------------------------------------
# Custom Workflow & Approval Engine (No-Code Approval Chains)
# ---------------------------------------------------------------------------

class WorkflowType(str, enum.Enum):
    PROMOTION = "promotion"
    SALARY_HIKE = "salary_hike"
    EQUIPMENT_REQUEST = "equipment_request"
    DOCUMENT_VERIFICATION = "document_verification"
    CUSTOM = "custom"


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    workflow_type = Column(Enum(WorkflowType), default=WorkflowType.CUSTOM, nullable=False)
    steps_definition = Column(JSON, nullable=False)  # [{"step": 1, "role": "HIRING_MANAGER"}, {"step": 2, "role": "HR_ADMIN"}]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(String, primary_key=True, default=gen_uuid)
    template_id = Column(String, ForeignKey("workflow_templates.id"), nullable=False)
    requester_id = Column(String, ForeignKey("users.id"), nullable=False)
    current_step = Column(Integer, default=1, nullable=False)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False)
    payload_json = Column(JSON, nullable=True)   # Data being approved
    approval_history = Column(JSON, default=list) # [{"step": 1, "approved_by": "user_id", "timestamp": "...", "note": "..."}]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# SSO & SCIM Provisioning
# ---------------------------------------------------------------------------

class SAMLProvider(Base):
    __tablename__ = "saml_providers"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)  # e.g., Okta, Azure AD, Google Workspace
    entity_id = Column(String, nullable=False, unique=True)
    sso_url = Column(String, nullable=False)
    x509_cert = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
