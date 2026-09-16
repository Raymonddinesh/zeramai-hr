"""
models_v9.py - Phase 11 (Dynamic Custom Fields & Forms) + Phase 12 (Compliance, Policies & Grievance)

Phase 11: CustomFieldDefinition, CustomFieldValue
Phase 12: CompliancePolicy, PolicyAcknowledgment, GrievanceCase
"""
import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum,
    Text, Integer, JSON, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Phase 11 - Dynamic Custom Fields & Form Builder
# ===========================================================================

class CustomFieldType(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"


class CustomFieldDefinition(Base):
    """Admin-defined custom attribute for entities (Person, Candidate, Engagement, Job)."""
    __tablename__ = "custom_field_definitions"

    id = Column(String, primary_key=True, default=gen_uuid)
    entity_type = Column(String, nullable=False, index=True)  # "person", "candidate", "job", "engagement"
    name = Column(String, nullable=False)                    # system code, e.g. "tshirt_size"
    label = Column(String, nullable=False)                   # display label, e.g. "T-Shirt Size"
    field_type = Column(Enum(CustomFieldType), default=CustomFieldType.TEXT, nullable=False)
    options_json = Column(JSON, nullable=True)               # ["S", "M", "L", "XL"] for select
    is_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CustomFieldValue(Base):
    """Stored value for an entity's custom field."""
    __tablename__ = "custom_field_values"

    id = Column(String, primary_key=True, default=gen_uuid)
    field_definition_id = Column(String, ForeignKey("custom_field_definitions.id"), nullable=False)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)   # ID of Person, Candidate, etc.
    value_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    definition = relationship("CustomFieldDefinition")


# ===========================================================================
# Phase 12 - Compliance, Policy Center & Grievance Resolution
# ===========================================================================

class PolicyCategory(str, enum.Enum):
    CODE_OF_CONDUCT = "code_of_conduct"
    INFO_SEC = "information_security"
    ANTI_HARASSMENT = "anti_harassment"
    LEAVE_POLICY = "leave_policy"
    COMPENSATION = "compensation"
    REMOTE_WORK = "remote_work"


class CompliancePolicy(Base):
    """Company governance policy requiring acknowledgment."""
    __tablename__ = "compliance_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    version = Column(String, default="1.0", nullable=False)
    category = Column(Enum(PolicyCategory), default=PolicyCategory.CODE_OF_CONDUCT, nullable=False)
    content = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    acknowledgments = relationship("PolicyAcknowledgment", back_populates="policy")


class PolicyAcknowledgment(Base):
    """Records an employee's electronic signature/acknowledgment of a policy."""
    __tablename__ = "policy_acknowledgments"

    id = Column(String, primary_key=True, default=gen_uuid)
    policy_id = Column(String, ForeignKey("compliance_policies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    acknowledged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)

    policy = relationship("CompliancePolicy", back_populates="acknowledgments")


class GrievanceCategory(str, enum.Enum):
    HARASSMENT = "harassment"
    DISCRIMINATION = "discrimination"
    COMPENSATION_DISPUTE = "compensation_dispute"
    SAFETY_HEALTH = "safety_health"
    ETHICS_VIOLATION = "ethics_violation"
    GENERAL = "general"


class GrievanceStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class GrievanceCase(Base):
    """Confidential or anonymous whistleblower & grievance case."""
    __tablename__ = "grievance_cases"

    id = Column(String, primary_key=True, default=gen_uuid)
    ticket_number = Column(String, unique=True, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    complainant_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    category = Column(Enum(GrievanceCategory), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(GrievanceStatus), default=GrievanceStatus.SUBMITTED, nullable=False)
    assigned_investigator_id = Column(String, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
