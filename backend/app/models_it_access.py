"""
models_it_access.py - IT access request and provisioning models for Module 11.
"""

import uuid
from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Enum as SAEnum,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ITAccessStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONED = "provisioned"
    REVOKED = "revoked"
    COMPLETED = "completed"


class ITAccessRequest(Base):
    """Employee request for IT access to a resource (system, app, VPN, etc.)."""

    __tablename__ = "it_access_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    resource = Column(String, nullable=False)  # e.g., "Salesforce", "GitHub"
    access_type = Column(String, nullable=False)  # read, write, admin, etc.
    requested_role = Column(String, nullable=True)  # optional role name
    business_justification = Column(Text, nullable=False)
    requested_start_date = Column(Date, nullable=True)
    requested_end_date = Column(Date, nullable=True)
    status = Column(SAEnum(ITAccessStatus), default=ITAccessStatus.PENDING, nullable=False)
    workflow_instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationships
    person = relationship("Person")
    user = relationship("User")
    workflow_instance = relationship("WorkflowInstance", foreign_keys=[workflow_instance_id])
    provisions = relationship("ITProvision", back_populates="access_request", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "person_id", "resource", "access_type", name="uq_it_access_per_employee"),
    )


class ITProvisionStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ITProvision(Base):
    """Record of actual provisioning of an IT access request.

    This does NOT perform the provisioning – external IT systems must be invoked separately.
    """

    __tablename__ = "it_provisions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    access_request_id = Column(String, ForeignKey("it_access_requests.id"), nullable=False, index=True)
    granted_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    external_reference = Column(String, nullable=True)  # e.g., ticket ID from ITSM
    resource_details = Column(Text, nullable=True)  # JSON or description of provisioned account
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(ITProvisionStatus), default=ITProvisionStatus.ACTIVE, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    access_request = relationship("ITAccessRequest", back_populates="provisions")
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_user_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "access_request_id", name="uq_it_provision_per_request"),
    )
