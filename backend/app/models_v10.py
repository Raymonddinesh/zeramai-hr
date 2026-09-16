"""
models_v10.py - Phase 13 (Multi-Country Localization), Phase 14 (Enterprise Security & IAM), Phase 15 (AI Intelligence)

Phase 13: HolidayCalendar, Holiday, CurrencyRate
Phase 14: SecurityPolicy, ActiveSession
Phase 15: AIAssessment, AIHelpdeskKnowledge
"""
import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum,
    Text, Integer, JSON, Float, Numeric
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Phase 13 - Multi-Country Localization
# ===========================================================================

class HolidayType(str, enum.Enum):
    PUBLIC = "public"
    REGIONAL = "regional"
    OPTIONAL = "optional"


class HolidayCalendar(Base):
    """Country/region specific holiday calendar."""
    __tablename__ = "holiday_calendars"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)           # "India - Karnataka 2026"
    country_code = Column(String, nullable=False)   # "IN", "US", "SG", "GB"
    year = Column(Integer, nullable=False)          # 2026
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    holidays = relationship("Holiday", back_populates="calendar", cascade="all, delete-orphan")


class Holiday(Base):
    """Individual holiday on a calendar."""
    __tablename__ = "holidays"

    id = Column(String, primary_key=True, default=gen_uuid)
    calendar_id = Column(String, ForeignKey("holiday_calendars.id"), nullable=False)
    name = Column(String, nullable=False)           # "Independence Day"
    date = Column(Date, nullable=False)
    holiday_type = Column(Enum(HolidayType), default=HolidayType.PUBLIC, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    calendar = relationship("HolidayCalendar", back_populates="holidays")


class CurrencyRate(Base):
    """FX rates for multi-country payroll & stipend conversions."""
    __tablename__ = "currency_rates"

    id = Column(String, primary_key=True, default=gen_uuid)
    from_currency = Column(String, nullable=False)  # "USD"
    to_currency = Column(String, nullable=False)    # "INR"
    exchange_rate = Column(Float, nullable=False)   # 83.50
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ===========================================================================
# Phase 14 - Enterprise IAM & Security Controls
# ===========================================================================

class SecurityPolicy(Base):
    """Enterprise security & password hardening rules."""
    __tablename__ = "security_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    min_password_length = Column(Integer, default=8, nullable=False)
    require_uppercase = Column(Boolean, default=True, nullable=False)
    require_numbers = Column(Boolean, default=True, nullable=False)
    require_special_char = Column(Boolean, default=True, nullable=False)
    session_timeout_minutes = Column(Integer, default=60, nullable=False)
    max_failed_logins = Column(Integer, default=5, nullable=False)
    ip_whitelist_enabled = Column(Boolean, default=False, nullable=False)
    ip_whitelist_json = Column(JSON, default=list)  # ["192.168.1.0/24", "10.0.0.1"]
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActiveSession(Base):
    """Tracks active user tokens/sessions for instant enterprise revocation."""
    __tablename__ = "active_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_token_hash = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)


# ===========================================================================
# Phase 15 - Governed AI Intelligence Suite
# ===========================================================================

class AIAssessmentType(str, enum.Enum):
    ATTRITION_RISK = "attrition_risk"
    CANDIDATE_FIT = "candidate_fit"
    COMPENSATION_BENCHMARK = "compensation_benchmark"
    PERFORMANCE_ANOMALY = "performance_anomaly"


class AIAssessment(Base):
    """Auditable AI prediction & decision support result."""
    __tablename__ = "ai_assessments"

    id = Column(String, primary_key=True, default=gen_uuid)
    entity_type = Column(String, nullable=False, index=True)  # "person", "candidate", "job"
    entity_id = Column(String, nullable=False, index=True)
    assessment_type = Column(Enum(AIAssessmentType), nullable=False)
    risk_score = Column(Float, nullable=False)               # 0.0 - 100.0 (e.g. 78% risk)
    confidence_score = Column(Float, default=0.85)           # 0.0 - 1.0
    factors_json = Column(JSON, nullable=True)               # ["Overtime spike", "Stagnant salary"]
    recommendations_json = Column(JSON, nullable=True)       # ["Schedule 1-on-1", "Review compensation"]
    model_version = Column(String, default="zeramai-ai-v3")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AIHelpdeskKnowledge(Base):
    """HR Policy & Onboarding AI FAQ knowledge base."""
    __tablename__ = "ai_helpdesk_knowledge"

    id = Column(String, primary_key=True, default=gen_uuid)
    category = Column(String, nullable=False)                # "leave", "payroll", "benefits"
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    keywords_json = Column(JSON, default=list)               # ["maternity", "leave days"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
