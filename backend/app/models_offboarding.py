"""
models_offboarding.py - Module 5: Offboarding & Exit Management Models.
"""
import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ExitStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    NOTICE_PERIOD = "notice_period"
    CLEARANCE = "clearance"
    EXIT_INTERVIEW = "exit_interview"
    SETTLEMENT_PENDING = "settlement_pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExitClearanceDepartment(str, enum.Enum):
    MANAGER = "manager"
    HR = "hr"
    FINANCE = "finance"
    IT = "it"
    ASSETS = "assets"
    ADMIN = "admin"


class ExitRequest(Base):
    """
    Employee resignation & offboarding exit lifecycle record.
    """
    __tablename__ = "exit_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)

    # Ownership — person and user account of the departing employee
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Resignation & Notice Period Details
    resignation_date = Column(Date, nullable=False)
    proposed_last_working_day = Column(Date, nullable=False)
    approved_last_working_day = Column(Date, nullable=True)
    notice_period_days = Column(Integer, default=30, nullable=False)
    reason_category = Column(String, nullable=True)
    employee_comments = Column(Text, nullable=True)

    # Lifecycle Status
    status = Column(Enum(ExitStatus), default=ExitStatus.SUBMITTED, nullable=False, index=True)

    # Reviews & Approvals
    manager_comments = Column(Text, nullable=True)
    hr_comments = Column(Text, nullable=True)
    manager_reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    manager_approved_at = Column(DateTime, nullable=True)
    hr_reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    hr_approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    person = relationship("Person", foreign_keys=[person_id])
    clearance_tasks = relationship("ExitClearanceTask", back_populates="exit_request", cascade="all, delete-orphan", order_by="ExitClearanceTask.created_at")
    handovers = relationship("ExitHandover", back_populates="exit_request", cascade="all, delete-orphan", order_by="ExitHandover.created_at")
    interview = relationship("ExitInterview", back_populates="exit_request", uselist=False, cascade="all, delete-orphan")
    settlement = relationship("ExitSettlement", back_populates="exit_request", uselist=False, cascade="all, delete-orphan")


class ExitClearanceTask(Base):
    """
    Departmental exit clearance task (IT, Assets, Admin, Finance, Manager, HR).
    """
    __tablename__ = "exit_clearance_tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    exit_request_id = Column(String, ForeignKey("exit_requests.id"), nullable=False, index=True)
    department = Column(Enum(ExitClearanceDepartment), nullable=False)
    task_name = Column(String, nullable=False)
    is_cleared = Column(Boolean, default=False, nullable=False)
    cleared_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    cleared_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exit_request = relationship("ExitRequest", back_populates="clearance_tasks")
    cleared_by = relationship("User", foreign_keys=[cleared_by_user_id])


class ExitHandover(Base):
    """
    Knowledge & project handover item from departing employee to a designated peer/manager.
    """
    __tablename__ = "exit_handovers"

    id = Column(String, primary_key=True, default=gen_uuid)
    exit_request_id = Column(String, ForeignKey("exit_requests.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    recipient_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    recipient_name = Column(String, nullable=True)
    documentation_url = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, completed
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exit_request = relationship("ExitRequest", back_populates="handovers")
    recipient = relationship("User", foreign_keys=[recipient_user_id])


class ExitInterview(Base):
    """
    Confidential exit interview details.
    Sensitive feedback is hidden from unauthorized users and departing peers.
    """
    __tablename__ = "exit_interviews"

    id = Column(String, primary_key=True, default=gen_uuid)
    exit_request_id = Column(String, ForeignKey("exit_requests.id"), nullable=False, index=True)
    interview_date = Column(Date, nullable=True)
    interviewer_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    primary_reason = Column(String, nullable=True)
    feedback_company = Column(Text, nullable=True)
    feedback_management = Column(Text, nullable=True)
    feedback_role = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exit_request = relationship("ExitRequest", back_populates="interview")
    interviewer = relationship("User", foreign_keys=[interviewer_user_id])


class ExitSettlement(Base):
    """
    Final settlement readiness checklist.
    Integrates with payroll and leave balances without duplicating calculations.
    """
    __tablename__ = "exit_settlements"

    id = Column(String, primary_key=True, default=gen_uuid)
    exit_request_id = Column(String, ForeignKey("exit_requests.id"), nullable=False, index=True)
    payroll_reviewed = Column(Boolean, default=False, nullable=False)
    leave_balance_reviewed = Column(Boolean, default=False, nullable=False)
    leave_encashment_days = Column(Float, default=0.0, nullable=False)
    asset_clearance_completed = Column(Boolean, default=False, nullable=False)
    finance_clearance_completed = Column(Boolean, default=False, nullable=False)
    settlement_status = Column(String, default="pending", nullable=False)  # pending, in_review, approved, processed
    settlement_amount = Column(Numeric(12, 2), nullable=True)
    remarks = Column(Text, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exit_request = relationship("ExitRequest", back_populates="settlement")
