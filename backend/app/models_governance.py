"""
models_governance.py - Module 15: Data Governance, Privacy, Retention & Business Continuity Data Models.

Canonical models for:
- DataClassification
- DataAsset
- RetentionPolicy
- RetentionPolicyAssignment
- DataLifecycleRecord
- LegalHold
- LegalHoldTarget
- PrivacyRequest
- BackupPolicy
- BackupExecution
- DRPolicy
- DRTest
- BusinessContinuityPlan
- BCPAction
- DataResidencyPolicy
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    BigInteger,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SensitivityLevel(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"


class RecordLifecycleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVE_ELIGIBLE = "ARCHIVE_ELIGIBLE"
    ARCHIVED = "ARCHIVED"
    DELETION_ELIGIBLE = "DELETION_ELIGIBLE"
    DELETED = "DELETED"
    ANONYMIZED = "ANONYMIZED"


class LegalHoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class PrivacyRequestType(str, enum.Enum):
    ACCESS = "ACCESS"
    EXPORT = "EXPORT"
    RECTIFICATION = "RECTIFICATION"
    DELETION = "DELETION"
    RESTRICTION = "RESTRICTION"
    ANONYMIZATION = "ANONYMIZATION"


class PrivacyRequestStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class BackupStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DRPriority(str, enum.Enum):
    MISSION_CRITICAL = "MISSION_CRITICAL"
    BUSINESS_CRITICAL = "BUSINESS_CRITICAL"
    ESSENTIAL = "ESSENTIAL"
    NON_CRITICAL = "NON_CRITICAL"


class DRTestStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BCPCriticality(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BCPStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ARCHIVED = "ARCHIVED"


# ---------------------------------------------------------------------------
# 1. Data Classification & Inventory Catalog
# ---------------------------------------------------------------------------

class DataClassification(Base):
    """Configurable data classification levels (Public, Internal, Confidential, Restricted, etc.)."""
    __tablename__ = "data_classifications"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=True, index=True)  # Nullable for system global defaults
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sensitivity_level = Column(String(50), nullable=False, default=SensitivityLevel.INTERNAL.value)
    default_retention_days = Column(Integer, nullable=True)  # Optional default retention
    enabled = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    assets = relationship("DataAsset", back_populates="classification")


class DataAsset(Base):
    """Metadata catalog of organizational data assets and sensitivity attributes."""
    __tablename__ = "data_assets"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(100), nullable=False)  # DATABASE_TABLE, OBJECT_STORAGE, LOG_STORE, FILE_STORE
    source_module = Column(String(100), nullable=False)  # Employee, Payroll, Attendance, Performance, Compliance
    classification_id = Column(String, ForeignKey("data_classifications.id"), nullable=False, index=True)
    contains_personal_data = Column(Boolean, default=True, nullable=False)
    contains_sensitive_personal_data = Column(Boolean, default=False, nullable=False)
    retention_policy_id = Column(String, ForeignKey("retention_policies.id"), nullable=True, index=True)
    data_residency = Column(String(100), nullable=True, default="IN-CENTRAL")  # Region code
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, ARCHIVED, DECOMMISSIONED
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    classification = relationship("DataClassification", back_populates="assets")
    retention_policy = relationship("RetentionPolicy", back_populates="assets")


# ---------------------------------------------------------------------------
# 2. Retention Policies & Assignments
# ---------------------------------------------------------------------------

class RetentionPolicy(Base):
    """Statutory, legal, and operational data retention rules."""
    __tablename__ = "retention_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    record_type = Column(String(100), nullable=False, index=True)  # EMPLOYEE, PAYROLL, ATTENDANCE, AUDIT_LOG, DOCUMENT
    retention_period_days = Column(Integer, nullable=False)  # e.g., 2555 (7 years for payroll/tax)
    archive_after_days = Column(Integer, nullable=False)  # e.g., 365 (1 year)
    deletion_after_days = Column(Integer, nullable=True)  # None if retention requires indefinite preservation
    legal_basis = Column(String(255), nullable=True)  # e.g., "Income Tax Act 1961 Section 44AA", "EPF Act"
    jurisdiction = Column(String(50), nullable=False, default="IN")  # Country/State code
    enabled = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    assets = relationship("DataAsset", back_populates="retention_policy")
    assignments = relationship("RetentionPolicyAssignment", back_populates="policy", cascade="all, delete-orphan")


class RetentionPolicyAssignment(Base):
    """Scoped binding of a retention policy to a target category, department, or legal entity."""
    __tablename__ = "retention_policy_assignments"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    policy_id = Column(String, ForeignKey("retention_policies.id"), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)  # GLOBAL, LEGAL_ENTITY, DEPARTMENT, ASSET_TYPE
    target_reference = Column(String(255), nullable=False)  # Entity ID, department name, or asset type code
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    policy = relationship("RetentionPolicy", back_populates="assignments")


# ---------------------------------------------------------------------------
# 3. Record Lifecycle Management
# ---------------------------------------------------------------------------

class DataLifecycleRecord(Base):
    """Evaluation state and lifecycle milestones for individual governed data records."""
    __tablename__ = "data_lifecycle_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    asset_type = Column(String(100), nullable=False, index=True)  # Document, AuditLog, Employee, Candidate
    asset_id = Column(String, nullable=False, index=True)  # Primary key of governed target record
    classification_id = Column(String, ForeignKey("data_classifications.id"), nullable=True)
    retention_policy_id = Column(String, ForeignKey("retention_policies.id"), nullable=True, index=True)
    lifecycle_status = Column(String(50), nullable=False, default=RecordLifecycleStatus.ACTIVE.value, index=True)
    eligible_archive_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    eligible_delete_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    anonymized_at = Column(DateTime, nullable=True)
    legal_hold = Column(Boolean, default=False, nullable=False, index=True)
    last_evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 4. Legal Holds
# ---------------------------------------------------------------------------

class LegalHold(Base):
    """Litigation or regulatory holds that freeze data from deletion, archival, or anonymization."""
    __tablename__ = "legal_holds"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    matter_reference = Column(String(100), nullable=False, index=True)  # Legal case number / matter ID
    status = Column(String(50), nullable=False, default=LegalHoldStatus.ACTIVE.value, index=True)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    released_at = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    released_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    targets = relationship("LegalHoldTarget", back_populates="legal_hold", cascade="all, delete-orphan")


class LegalHoldTarget(Base):
    """Specific entity or subject placed under a legal hold."""
    __tablename__ = "legal_hold_targets"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_hold_id = Column(String, ForeignKey("legal_holds.id"), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)  # PERSON, EMPLOYEE, DEPARTMENT, DOCUMENT, LEGAL_ENTITY
    target_reference = Column(String(255), nullable=False, index=True)  # Specific person_id or document_id
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    legal_hold = relationship("LegalHold", back_populates="targets")


# ---------------------------------------------------------------------------
# 5. Privacy Requests (DSR / DSAR)
# ---------------------------------------------------------------------------

class PrivacyRequest(Base):
    """Data Subject Access / Erasure / Export Requests (GDPR / DPDP Act compliance)."""
    __tablename__ = "privacy_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=True, index=True)
    request_type = Column(String(50), nullable=False, default=PrivacyRequestType.EXPORT.value, index=True)
    status = Column(String(50), nullable=False, default=PrivacyRequestStatus.SUBMITTED.value, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime, nullable=False)  # Statutory deadline (typically 30 days)
    completed_at = Column(DateTime, nullable=True)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    verification_status = Column(String(50), default="VERIFIED", nullable=False)
    rejection_reason = Column(Text, nullable=True)
    export_reference = Column(String(255), nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 6. Backup Policies & Execution Tracking
# ---------------------------------------------------------------------------

class BackupPolicy(Base):
    """Governance configuration and standards for organizational backups."""
    __tablename__ = "backup_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    frequency = Column(String(50), nullable=False, default="DAILY")  # HOURLY, DAILY, WEEKLY, MONTHLY
    retention_days = Column(Integer, nullable=False, default=30)
    encryption_required = Column(Boolean, default=True, nullable=False)
    offsite_required = Column(Boolean, default=True, nullable=False)
    cross_region_required = Column(Boolean, default=False, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    executions = relationship("BackupExecution", back_populates="policy", cascade="all, delete-orphan")


class BackupExecution(Base):
    """Operational telemetry and verification records of backup jobs."""
    __tablename__ = "backup_executions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    backup_policy_id = Column(String, ForeignKey("backup_policies.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default=BackupStatus.COMPLETED.value, index=True)
    backup_reference = Column(String(255), nullable=True)  # Snapshot / archive URI identifier
    size_bytes = Column(BigInteger, default=0, nullable=False)
    checksum = Column(String(128), nullable=True)  # SHA-256 integrity hash
    region = Column(String(50), default="IN-CENTRAL", nullable=False)
    encryption_status = Column(String(50), default="ENCRYPTED_AES256", nullable=False)
    verification_status = Column(String(50), default="VERIFIED", nullable=False)
    error_message = Column(Text, nullable=True)

    policy = relationship("BackupPolicy", back_populates="executions")


# ---------------------------------------------------------------------------
# 7. Disaster Recovery (DR) Policies & Tests
# ---------------------------------------------------------------------------

class DRPolicy(Base):
    """Disaster recovery requirements, RPO and RTO thresholds."""
    __tablename__ = "dr_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    rpo_minutes = Column(Integer, nullable=False, default=60)  # Recovery Point Objective
    rto_minutes = Column(Integer, nullable=False, default=240)  # Recovery Time Objective
    primary_region = Column(String(50), nullable=False, default="IN-SOUTH")
    recovery_region = Column(String(50), nullable=False, default="IN-WEST")
    priority = Column(String(50), nullable=False, default=DRPriority.BUSINESS_CRITICAL.value)
    enabled = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tests = relationship("DRTest", back_populates="policy", cascade="all, delete-orphan")


class DRTest(Base):
    """Evidentiary record of Disaster Recovery drills and simulations."""
    __tablename__ = "dr_tests"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    dr_policy_id = Column(String, ForeignKey("dr_policies.id"), nullable=False, index=True)
    test_type = Column(String(50), nullable=False, default="FAILOVER_SIMULATION")  # TABLETOP, FAILOVER_SIMULATION, RESTORE_DRILL
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default=DRTestStatus.PASSED.value, index=True)
    actual_rpo_minutes = Column(Integer, nullable=True)
    actual_rto_minutes = Column(Integer, nullable=True)
    findings = Column(Text, nullable=True)
    corrective_actions = Column(Text, nullable=True)
    tested_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    policy = relationship("DRPolicy", back_populates="tests")


# ---------------------------------------------------------------------------
# 8. Business Continuity Plans (BCP) & Action Items
# ---------------------------------------------------------------------------

class BusinessContinuityPlan(Base):
    """Enterprise business continuity and resumption strategies for HR operations."""
    __tablename__ = "business_continuity_plans"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    criticality = Column(String(50), nullable=False, default=BCPCriticality.CRITICAL.value)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    recovery_strategy = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default=BCPStatus.ACTIVE.value, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    actions = relationship("BCPAction", back_populates="plan", cascade="all, delete-orphan")


class BCPAction(Base):
    """Step-by-step continuity action item associated with a plan."""
    __tablename__ = "bcp_actions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    plan_id = Column(String, ForeignKey("business_continuity_plans.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False, default=1)
    action = Column(Text, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED
    completed_at = Column(DateTime, nullable=True)

    plan = relationship("BusinessContinuityPlan", back_populates="actions")


# ---------------------------------------------------------------------------
# 9. Data Residency Policies
# ---------------------------------------------------------------------------

class DataResidencyPolicy(Base):
    """Sovereign data residency rules and cross-border transfer controls."""
    __tablename__ = "data_residency_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    data_category = Column(String(100), nullable=False, index=True)  # EMPLOYEE_PII, PAYROLL, BIOMETRIC, COMPLIANCE
    allowed_regions = Column(JSON, nullable=False)  # ["IN-CENTRAL", "IN-SOUTH"]
    primary_region = Column(String(50), nullable=False, default="IN-CENTRAL")
    cross_border_transfer_allowed = Column(Boolean, default=False, nullable=False)
    transfer_basis = Column(String(255), nullable=True)  # Standard Contractual Clauses (SCC), Adequacy Decision
    enabled = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
