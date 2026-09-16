"""
models_v7.py – Phase 7 (Performance & OKRs) + Phase 8 (LMS)

Phase 7: OKRObjective, OKRKeyResult, PerformanceReview, ReviewCycle
Phase 8: Course, CourseModule, Enrollment, TrainingCertificate
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Phase 7 — Performance Management & OKRs
# ===========================================================================

class ObjectiveStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReviewCycleStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    CLOSED = "closed"


class ReviewRating(str, enum.Enum):
    EXCEEDS = "exceeds_expectations"
    MEETS = "meets_expectations"
    BELOW = "below_expectations"
    NEEDS_IMPROVEMENT = "needs_improvement"


class ReviewCycle(Base):
    """Performance review cycle (Q1, H1, Annual, etc.)."""
    __tablename__ = "review_cycles"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)           # "H1 2026"
    cycle_type = Column(String, default="annual")   # quarterly, half-yearly, annual
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum(ReviewCycleStatus), default=ReviewCycleStatus.UPCOMING)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OKRObjective(Base):
    """OKR Objective."""
    __tablename__ = "okr_objectives"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    review_cycle_id = Column(String, ForeignKey("review_cycles.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)             # Weight for scoring
    status = Column(Enum(ObjectiveStatus), default=ObjectiveStatus.DRAFT)
    progress_pct = Column(Float, default=0)          # 0-100
    parent_objective_id = Column(String, ForeignKey("okr_objectives.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    key_results = relationship("OKRKeyResult", back_populates="objective")


class KRStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class OKRKeyResult(Base):
    """Key Result under an Objective."""
    __tablename__ = "okr_key_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    objective_id = Column(String, ForeignKey("okr_objectives.id"), nullable=False)
    title = Column(String, nullable=False)
    target_value = Column(Float, nullable=False)     # e.g. 100
    current_value = Column(Float, default=0)
    unit = Column(String, default="percent")         # percent, count, currency
    status = Column(Enum(KRStatus), default=KRStatus.NOT_STARTED)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    objective = relationship("OKRObjective", back_populates="key_results")


class PerformanceReview(Base):
    """Individual performance review for a cycle."""
    __tablename__ = "performance_reviews"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    review_cycle_id = Column(String, ForeignKey("review_cycles.id"), nullable=False)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    self_rating = Column(Enum(ReviewRating), nullable=True)
    manager_rating = Column(Enum(ReviewRating), nullable=True)
    final_rating = Column(Enum(ReviewRating), nullable=True)
    self_comments = Column(Text, nullable=True)
    manager_comments = Column(Text, nullable=True)
    goals_met_pct = Column(Float, nullable=True)
    is_submitted = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ===========================================================================
# Phase 8 — Learning Management System (LMS)
# ===========================================================================

class CourseStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DROPPED = "dropped"


class Course(Base):
    """Training course."""
    __tablename__ = "courses"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)        # technical, soft_skills, compliance
    duration_hours = Column(Float, nullable=True)
    is_mandatory = Column(Boolean, default=False)
    instructor_name = Column(String, nullable=True)
    max_enrollment = Column(Integer, nullable=True)
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT)
    modules_json = Column(JSON, nullable=True)       # [{title, duration_min, order}]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    enrollments = relationship("Enrollment", back_populates="course")


class Enrollment(Base):
    """Person enrollment in a course."""
    __tablename__ = "enrollments"

    id = Column(String, primary_key=True, default=gen_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED)
    progress_pct = Column(Float, default=0)
    completed_modules = Column(JSON, default=list)   # [module_index, ...]
    score = Column(Float, nullable=True)             # Final assessment score
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    course = relationship("Course", back_populates="enrollments")
    person = relationship("Person")


class TrainingCertificate(Base):
    """Certificate issued on course completion."""
    __tablename__ = "training_certificates"

    id = Column(String, primary_key=True, default=gen_uuid)
    enrollment_id = Column(String, ForeignKey("enrollments.id"), nullable=False)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False)
    certificate_number = Column(String, unique=True, nullable=False)
    issued_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
