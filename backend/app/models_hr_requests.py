"""
models_hr_requests.py - HR Service Desk: HRRequest and HRRequestComment models.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Date, Enum, Text, ForeignKey, Boolean,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class HRRequestCategory(str, enum.Enum):
    PAYROLL = "payroll"
    LEAVE = "leave"
    ATTENDANCE = "attendance"
    BENEFITS = "benefits"
    DOCUMENTS = "documents"
    EMPLOYMENT_VERIFICATION = "employment_verification"
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"
    IT_ACCESS = "it_access"
    POLICY = "policy"
    GENERAL_HR = "general_hr"


class HRRequestPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class HRRequestStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_EMPLOYEE = "waiting_for_employee"
    RESOLVED = "resolved"
    CLOSED = "closed"


class HRRequest(Base):
    """
    An employee HR support request / ticket.
    Created by the employee via self-service.
    Managed by HR/Admin through the service desk.
    """
    __tablename__ = "hr_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    ticket_number = Column(String, unique=True, nullable=False, index=True)

    # Multi-tenancy & Ownership
    tenant_id = Column(String, nullable=True, index=True)
    requester_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Request details
    category = Column(Enum(HRRequestCategory), nullable=False)
    priority = Column(Enum(HRRequestPriority), default=HRRequestPriority.MEDIUM, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # Lifecycle
    status = Column(Enum(HRRequestStatus), default=HRRequestStatus.OPEN, nullable=False, index=True)
    assigned_to_user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Resolution
    resolution = Column(Text, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # SLA foundation
    sla_due_date = Column(Date, nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    requester = relationship("User", foreign_keys=[requester_user_id])
    assignee = relationship("User", foreign_keys=[assigned_to_user_id])
    comments = relationship("HRRequestComment", back_populates="hr_request", order_by="HRRequestComment.created_at")


class HRRequestComment(Base):
    """
    A comment on an HR request. Can be employee-visible or internal HR-only.
    """
    __tablename__ = "hr_request_comments"

    id = Column(String, primary_key=True, default=gen_uuid)
    hr_request_id = Column(String, ForeignKey("hr_requests.id"), nullable=False, index=True)
    author_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)  # True = HR-only, hidden from employee
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    hr_request = relationship("HRRequest", back_populates="comments")
    author = relationship("User")
