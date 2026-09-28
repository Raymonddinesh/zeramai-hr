"""
models_policy_er.py - Module 8: HR Policy & Employee Relations Models.

Defines:
- HRPolicy: Policy documents, versions, publication lifecycle, and applicability rules.
- PolicyAcknowledgementRecord: Employee electronic signatures/acknowledgements of policy versions.
- EmployeeRelationsCase: Case management for conduct, behavior, performance, policy violations.
- ERCaseNote: Investigation notes, evidence, internal HR remarks, and employee communications.
- DisciplinaryAction: Formal disciplinary tracking (verbal/written/final warning, PIP, suspension).
"""
import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum,
    Text, Integer, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# HR Policy Enums
# ===========================================================================

class HRPolicyStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class HRPolicyCategory(str, enum.Enum):
    CODE_OF_CONDUCT = "code_of_conduct"
    LEAVE_ATTENDANCE = "leave_attendance"
    IT_SECURITY = "it_security"
    REMOTE_WORK = "remote_work"
    COMPENSATION_BENEFITS = "compensation_benefits"
    WORKPLACE_SAFETY = "workplace_safety"
    DISCIPLINARY = "disciplinary"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    GENERAL = "general"


# ===========================================================================
# Employee Relations Enums
# ===========================================================================

class ERCaseCategory(str, enum.Enum):
    CONDUCT = "conduct"
    ATTENDANCE = "attendance"
    PERFORMANCE = "performance"
    WORKPLACE_BEHAVIOR = "workplace_behavior"
    POLICY_VIOLATION = "policy_violation"
    DISCIPLINARY = "disciplinary"
    OTHER = "other"


class ERCaseStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    INVESTIGATION = "investigation"
    ACTION_REQUIRED = "action_required"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ERCaseSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DisciplinaryActionType(str, enum.Enum):
    VERBAL_WARNING = "verbal_warning"
    WRITTEN_WARNING = "written_warning"
    FINAL_WARNING = "final_warning"
    PIP = "pip"
    SUSPENSION = "suspension"
    OTHER = "other"


class DisciplinaryStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    REVOKED = "revoked"
    EXPIRED = "expired"


# ===========================================================================
# HR Policy & Versioning
# ===========================================================================

class HRPolicy(Base):
    """
    Enterprise HR Policy document supporting versioning, multi-stage approval,
    publication lifecycle, and applicability rules. Published versions remain immutable.
    """
    __tablename__ = "hr_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)

    title = Column(String, nullable=False)
    policy_code = Column(String, nullable=False, index=True)  # e.g. "POL-COC-001"
    category = Column(Enum(HRPolicyCategory), default=HRPolicyCategory.GENERAL, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)

    version = Column(String, default="1.0", nullable=False)
    status = Column(Enum(HRPolicyStatus), default=HRPolicyStatus.DRAFT, nullable=False)

    effective_date = Column(Date, nullable=False)
    review_date = Column(Date, nullable=True)

    # Applicability scope (optional targeting)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    employment_type = Column(String, nullable=True)  # e.g. "full_time_employee"
    is_mandatory = Column(Boolean, default=True, nullable=False)

    # Version lineage
    previous_version_id = Column(String, ForeignKey("hr_policies.id"), nullable=True)

    # Ownership & Audit lifecycle
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    published_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    published_by = relationship("User", foreign_keys=[published_by_id])
    acknowledgements = relationship("PolicyAcknowledgementRecord", back_populates="policy")


class PolicyAcknowledgementRecord(Base):
    """
    Immutable electronic acknowledgement record for a specific policy version by an employee.
    """
    __tablename__ = "policy_acknowledgement_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)

    policy_id = Column(String, ForeignKey("hr_policies.id"), nullable=False, index=True)
    policy_version = Column(String, nullable=False)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    acknowledged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)
    status = Column(String, default="acknowledged", nullable=False)

    # Relationships
    policy = relationship("HRPolicy", back_populates="acknowledgements")
    person = relationship("Person")
    user = relationship("User")


# ===========================================================================
# Employee Relations Cases & Disciplinary Tracking
# ===========================================================================

class EmployeeRelationsCase(Base):
    """
    Employee Relations (ER) case management.
    Separated strictly from GrievanceCase/whistleblower functionality.
    """
    __tablename__ = "employee_relations_cases"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)

    case_number = Column(String, unique=True, nullable=False, index=True)  # e.g. "ER-202609-0001"
    title = Column(String, nullable=False)
    category = Column(Enum(ERCaseCategory), default=ERCaseCategory.OTHER, nullable=False)
    severity = Column(Enum(ERCaseSeverity), default=ERCaseSeverity.MEDIUM, nullable=False)

    subject_person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    reporting_manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    hr_owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(ERCaseStatus), default=ERCaseStatus.OPEN, nullable=False)
    description = Column(Text, nullable=False)
    investigation_summary = Column(Text, nullable=True)  # Confidential HR internal note
    resolution_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    subject_person = relationship("Person")
    reporting_manager = relationship("User", foreign_keys=[reporting_manager_id])
    hr_owner = relationship("User", foreign_keys=[hr_owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    notes = relationship("ERCaseNote", back_populates="case", cascade="all, delete-orphan")
    disciplinary_actions = relationship("DisciplinaryAction", back_populates="case")


class ERCaseNote(Base):
    """
    Investigation notes, evidence logs, internal HR discussions, and employee communications.
    """
    __tablename__ = "er_case_notes"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    case_id = Column(String, ForeignKey("employee_relations_cases.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)

    note_type = Column(String, default="internal_hr", nullable=False)  # "internal_hr", "investigation", "evidence", "employee_communication"
    content = Column(Text, nullable=False)
    is_confidential = Column(Boolean, default=True, nullable=False)  # If true, hidden from non-HR

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("EmployeeRelationsCase", back_populates="notes")
    author = relationship("User")


class DisciplinaryAction(Base):
    """
    Formal disciplinary actions issued to an employee (warnings, PIP, suspension).
    """
    __tablename__ = "disciplinary_actions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    case_id = Column(String, ForeignKey("employee_relations_cases.id"), nullable=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)

    action_type = Column(Enum(DisciplinaryActionType), nullable=False)
    reason = Column(Text, nullable=False)
    action_plan = Column(Text, nullable=True)

    issued_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    issued_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)

    status = Column(Enum(DisciplinaryStatus), default=DisciplinaryStatus.ACTIVE, nullable=False)

    employee_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("EmployeeRelationsCase", back_populates="disciplinary_actions")
    person = relationship("Person")
    issued_by = relationship("User", foreign_keys=[issued_by_id])
