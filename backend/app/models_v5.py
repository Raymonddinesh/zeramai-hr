"""
models_v5.py – Phase 3 (Global ATS & Recruitment) + Phase 4 (Attendance & Shift Rostering)

Phase 3: InterviewSchedule, InterviewScorecard, OfferLetter
Phase 4: ShiftTemplate, ShiftAssignment, ShiftSwapRequest
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON, Float, Time
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Phase 3 — Global ATS & Recruitment
# ===========================================================================

class InterviewType(str, enum.Enum):
    PHONE_SCREEN = "phone_screen"
    VIDEO = "video"
    ONSITE = "onsite"
    PANEL = "panel"
    TECHNICAL = "technical"
    HR = "hr"
    CULTURE_FIT = "culture_fit"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class InterviewSchedule(Base):
    """Interview slot for a candidate application."""
    __tablename__ = "interview_schedules"

    id = Column(String, primary_key=True, default=gen_uuid)
    application_id = Column(String, ForeignKey("candidate_applications.id"), nullable=False)
    interviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    interview_type = Column(Enum(InterviewType), nullable=False)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)          # Room / video link
    meeting_link = Column(String, nullable=True)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.SCHEDULED, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scorecards = relationship("InterviewScorecard", back_populates="interview")


class ScorecardVerdict(str, enum.Enum):
    STRONG_YES = "strong_yes"
    YES = "yes"
    NEUTRAL = "neutral"
    NO = "no"
    STRONG_NO = "strong_no"


class InterviewScorecard(Base):
    """Interviewer feedback / scorecard per interview."""
    __tablename__ = "interview_scorecards"

    id = Column(String, primary_key=True, default=gen_uuid)
    interview_id = Column(String, ForeignKey("interview_schedules.id"), nullable=False)
    evaluator_id = Column(String, ForeignKey("users.id"), nullable=False)
    technical_score = Column(Integer, nullable=True)       # 1-5
    communication_score = Column(Integer, nullable=True)   # 1-5
    culture_fit_score = Column(Integer, nullable=True)     # 1-5
    overall_score = Column(Float, nullable=True)           # avg or weighted
    verdict = Column(Enum(ScorecardVerdict), nullable=False)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    interview = relationship("InterviewSchedule", back_populates="scorecards")


class OfferStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class OfferLetter(Base):
    """Offer letter management for a candidate application."""
    __tablename__ = "offer_letters"

    id = Column(String, primary_key=True, default=gen_uuid)
    application_id = Column(String, ForeignKey("candidate_applications.id"), nullable=False)
    offered_designation = Column(String, nullable=False)
    offered_department = Column(String, nullable=False)
    offered_salary = Column(Numeric(12, 2), nullable=False)
    offered_currency = Column(String, default="INR", nullable=False)
    joining_date = Column(Date, nullable=True)
    offer_expiry_date = Column(Date, nullable=True)
    status = Column(Enum(OfferStatus), default=OfferStatus.DRAFT, nullable=False)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ===========================================================================
# Phase 4 — Attendance & Shift Rostering
# ===========================================================================

class ShiftType(str, enum.Enum):
    GENERAL = "general"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    ROTATIONAL = "rotational"
    FLEXIBLE = "flexible"


class ShiftTemplate(Base):
    """Reusable shift definition (e.g., Morning 9-5, Night 10pm-6am)."""
    __tablename__ = "shift_templates"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)
    shift_type = Column(Enum(ShiftType), default=ShiftType.GENERAL, nullable=False)
    start_time = Column(String, nullable=False)    # "09:00" HH:MM
    end_time = Column(String, nullable=False)      # "17:00" HH:MM
    break_duration_minutes = Column(Integer, default=60)
    is_night_shift = Column(Boolean, default=False)
    min_rest_hours = Column(Integer, default=12)   # minimum rest between shifts
    color_code = Column(String, default="#3B82F6")  # for roster calendar UI
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    assignments = relationship("ShiftAssignment", back_populates="shift_template")


class ShiftAssignment(Base):
    """Assigns a person to a shift on a specific date."""
    __tablename__ = "shift_assignments"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    shift_template_id = Column(String, ForeignKey("shift_templates.id"), nullable=False)
    date = Column(Date, nullable=False)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    is_overtime = Column(Boolean, default=False)
    overtime_hours = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    shift_template = relationship("ShiftTemplate", back_populates="assignments")
    person = relationship("Person")


class SwapStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ShiftSwapRequest(Base):
    """Employee-initiated shift swap request."""
    __tablename__ = "shift_swap_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    requester_assignment_id = Column(String, ForeignKey("shift_assignments.id"), nullable=False)
    target_assignment_id = Column(String, ForeignKey("shift_assignments.id"), nullable=False)
    requester_id = Column(String, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(Enum(SwapStatus), default=SwapStatus.PENDING, nullable=False)
    reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
