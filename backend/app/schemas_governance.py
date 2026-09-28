"""
schemas_governance.py - Pydantic schemas for Module 15: Data Governance, Privacy, Retention & Business Continuity.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data Classification
# ---------------------------------------------------------------------------

class DataClassificationBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    sensitivity_level: str = "INTERNAL"
    default_retention_days: Optional[int] = None
    enabled: bool = True


class DataClassificationCreate(DataClassificationBase):
    pass


class DataClassificationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sensitivity_level: Optional[str] = None
    default_retention_days: Optional[int] = None
    enabled: Optional[bool] = None


class DataClassificationResponse(DataClassificationBase):
    id: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Data Asset Inventory
# ---------------------------------------------------------------------------

class DataAssetBase(BaseModel):
    name: str = Field(..., max_length=255)
    asset_type: str = Field(..., max_length=100)
    source_module: str = Field(..., max_length=100)
    classification_id: str
    legal_entity_id: Optional[str] = None
    contains_personal_data: bool = True
    contains_sensitive_personal_data: bool = False
    retention_policy_id: Optional[str] = None
    data_residency: Optional[str] = "IN-CENTRAL"
    owner_user_id: Optional[str] = None
    status: str = "ACTIVE"


class DataAssetCreate(DataAssetBase):
    pass


class DataAssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    source_module: Optional[str] = None
    classification_id: Optional[str] = None
    legal_entity_id: Optional[str] = None
    contains_personal_data: Optional[bool] = None
    contains_sensitive_personal_data: Optional[bool] = None
    retention_policy_id: Optional[str] = None
    data_residency: Optional[str] = None
    owner_user_id: Optional[str] = None
    status: Optional[str] = None


class DataAssetResponse(DataAssetBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    classification_name: Optional[str] = None
    retention_policy_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Retention Policies & Assignments
# ---------------------------------------------------------------------------

class RetentionPolicyBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    record_type: str = Field(..., max_length=100)
    retention_period_days: int
    archive_after_days: int
    deletion_after_days: Optional[int] = None
    legal_basis: Optional[str] = None
    jurisdiction: str = "IN"
    enabled: bool = True


class RetentionPolicyCreate(RetentionPolicyBase):
    pass


class RetentionPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    record_type: Optional[str] = None
    retention_period_days: Optional[int] = None
    archive_after_days: Optional[int] = None
    deletion_after_days: Optional[int] = None
    legal_basis: Optional[str] = None
    jurisdiction: Optional[str] = None
    enabled: Optional[bool] = None


class RetentionPolicyAssignmentCreate(BaseModel):
    target_type: str = Field(..., max_length=50)  # GLOBAL, LEGAL_ENTITY, DEPARTMENT, ASSET_TYPE
    target_reference: str = Field(..., max_length=255)
    effective_from: date
    effective_to: Optional[date] = None


class RetentionPolicyAssignmentResponse(BaseModel):
    id: str
    tenant_id: str
    policy_id: str
    target_type: str
    target_reference: str
    effective_from: date
    effective_to: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RetentionPolicyResponse(RetentionPolicyBase):
    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    assignments: List[RetentionPolicyAssignmentResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Record Lifecycle
# ---------------------------------------------------------------------------

class DataLifecycleRecordResponse(BaseModel):
    id: str
    tenant_id: str
    asset_type: str
    asset_id: str
    classification_id: Optional[str] = None
    retention_policy_id: Optional[str] = None
    lifecycle_status: str
    eligible_archive_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    eligible_delete_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    anonymized_at: Optional[datetime] = None
    legal_hold: bool = False
    last_evaluated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LifecycleEvaluateRequest(BaseModel):
    asset_type: Optional[str] = None
    dry_run: bool = False


class LifecycleEvaluateSummary(BaseModel):
    total_evaluated: int
    eligible_for_archive: int
    archived_count: int
    eligible_for_deletion: int
    blocked_by_legal_hold: int
    dry_run: bool
    evaluation_timestamp: datetime


# ---------------------------------------------------------------------------
# Legal Holds
# ---------------------------------------------------------------------------

class LegalHoldTargetCreate(BaseModel):
    target_type: str = Field(..., max_length=50)  # PERSON, EMPLOYEE, DEPARTMENT, DOCUMENT, LEGAL_ENTITY
    target_reference: str = Field(..., max_length=255)


class LegalHoldTargetResponse(BaseModel):
    id: str
    tenant_id: str
    legal_hold_id: str
    target_type: str
    target_reference: str
    created_at: datetime

    class Config:
        from_attributes = True


class LegalHoldCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    matter_reference: str = Field(..., max_length=100)
    targets: List[LegalHoldTargetCreate] = []


class LegalHoldUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    matter_reference: Optional[str] = None


class LegalHoldResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    matter_reference: str
    status: str
    issued_at: datetime
    released_at: Optional[datetime] = None
    created_by: str
    released_by: Optional[str] = None
    created_at: datetime
    targets: List[LegalHoldTargetResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Privacy Requests (DSR / DSAR)
# ---------------------------------------------------------------------------

class PrivacyRequestCreate(BaseModel):
    person_id: Optional[str] = None
    request_type: str = "EXPORT"  # ACCESS, EXPORT, RECTIFICATION, DELETION, RESTRICTION, ANONYMIZATION
    assigned_to: Optional[str] = None
    processing_notes: Optional[str] = None


class PrivacyRequestUpdateStatus(BaseModel):
    status: str  # IDENTITY_VERIFICATION, IN_REVIEW, APPROVED, PROCESSING, COMPLETED, REJECTED, CANCELLED
    rejection_reason: Optional[str] = None
    processing_notes: Optional[str] = None


class PrivacyRequestResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: Optional[str] = None
    person_name: Optional[str] = None
    request_type: str
    status: str
    submitted_at: datetime
    due_at: datetime
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    verification_status: str
    rejection_reason: Optional[str] = None
    export_reference: Optional[str] = None
    processing_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrivacyExportResponse(BaseModel):
    request_id: str
    tenant_id: str
    person_id: str
    generated_at: datetime
    data: Dict[str, Any]


class PrivacyAnonymizeResponse(BaseModel):
    request_id: str
    tenant_id: str
    person_id: str
    success: bool
    message: str
    anonymized_fields: List[str]
    preserved_records: List[str]
    blocked_by_legal_hold: bool = False


# ---------------------------------------------------------------------------
# Backup Policies & Executions
# ---------------------------------------------------------------------------

class BackupPolicyBase(BaseModel):
    name: str = Field(..., max_length=255)
    frequency: str = "DAILY"
    retention_days: int = 30
    encryption_required: bool = True
    offsite_required: bool = True
    cross_region_required: bool = False
    enabled: bool = True


class BackupPolicyCreate(BackupPolicyBase):
    pass


class BackupPolicyUpdate(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    retention_days: Optional[int] = None
    encryption_required: Optional[bool] = None
    offsite_required: Optional[bool] = None
    cross_region_required: Optional[bool] = None
    enabled: Optional[bool] = None


class BackupExecutionCreate(BaseModel):
    backup_reference: Optional[str] = None
    size_bytes: int = 0
    checksum: Optional[str] = None
    region: str = "IN-CENTRAL"
    status: str = "COMPLETED"


class BackupExecutionResponse(BaseModel):
    id: str
    tenant_id: str
    backup_policy_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    backup_reference: Optional[str] = None
    size_bytes: int
    checksum: Optional[str] = None
    region: str
    encryption_status: str
    verification_status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class BackupPolicyResponse(BackupPolicyBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    recent_executions: List[BackupExecutionResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Disaster Recovery (DR)
# ---------------------------------------------------------------------------

class DRPolicyBase(BaseModel):
    name: str = Field(..., max_length=255)
    rpo_minutes: int = 60
    rto_minutes: int = 240
    primary_region: str = "IN-SOUTH"
    recovery_region: str = "IN-WEST"
    priority: str = "BUSINESS_CRITICAL"
    enabled: bool = True


class DRPolicyCreate(DRPolicyBase):
    pass


class DRPolicyUpdate(BaseModel):
    name: Optional[str] = None
    rpo_minutes: Optional[int] = None
    rto_minutes: Optional[int] = None
    primary_region: Optional[str] = None
    recovery_region: Optional[str] = None
    priority: Optional[str] = None
    enabled: Optional[bool] = None


class DRTestCreate(BaseModel):
    test_type: str = "FAILOVER_SIMULATION"
    status: str = "PASSED"
    actual_rpo_minutes: Optional[int] = None
    actual_rto_minutes: Optional[int] = None
    findings: Optional[str] = None
    corrective_actions: Optional[str] = None


class DRTestResponse(BaseModel):
    id: str
    tenant_id: str
    dr_policy_id: str
    test_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    actual_rpo_minutes: Optional[int] = None
    actual_rto_minutes: Optional[int] = None
    findings: Optional[str] = None
    corrective_actions: Optional[str] = None
    tested_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class DRPolicyResponse(DRPolicyBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    tests: List[DRTestResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Business Continuity Plans (BCP)
# ---------------------------------------------------------------------------

class BCPActionBase(BaseModel):
    sequence: int = 1
    action: str
    owner_user_id: Optional[str] = None
    status: str = "PENDING"


class BCPActionCreate(BCPActionBase):
    pass


class BCPActionUpdate(BaseModel):
    sequence: Optional[int] = None
    action: Optional[str] = None
    owner_user_id: Optional[str] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


class BCPActionResponse(BCPActionBase):
    id: str
    tenant_id: str
    plan_id: str
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BCPBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    criticality: str = "CRITICAL"
    owner_user_id: Optional[str] = None
    recovery_strategy: str
    status: str = "ACTIVE"
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None


class BCPCreate(BCPBase):
    actions: List[BCPActionCreate] = []


class BCPUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    criticality: Optional[str] = None
    owner_user_id: Optional[str] = None
    recovery_strategy: Optional[str] = None
    status: Optional[str] = None
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None


class BCPResponse(BCPBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    actions: List[BCPActionResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Data Residency
# ---------------------------------------------------------------------------

class DataResidencyPolicyBase(BaseModel):
    data_category: str = Field(..., max_length=100)
    allowed_regions: List[str]
    primary_region: str = "IN-CENTRAL"
    cross_border_transfer_allowed: bool = False
    transfer_basis: Optional[str] = None
    enabled: bool = True


class DataResidencyPolicyCreate(DataResidencyPolicyBase):
    pass


class DataResidencyPolicyUpdate(BaseModel):
    data_category: Optional[str] = None
    allowed_regions: Optional[List[str]] = None
    primary_region: Optional[str] = None
    cross_border_transfer_allowed: Optional[bool] = None
    transfer_basis: Optional[str] = None
    enabled: Optional[bool] = None


class DataResidencyPolicyResponse(DataResidencyPolicyBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Dashboard Overview
# ---------------------------------------------------------------------------

class GovernanceDashboardSummary(BaseModel):
    classifications_count: int
    data_assets_count: int
    retention_policies_count: int
    active_legal_holds_count: int
    pending_privacy_requests_count: int
    total_privacy_requests_count: int
    backup_status: str  # HEALTHY, WARNING, CRITICAL
    last_backup_at: Optional[datetime] = None
    dr_readiness_status: str  # READY, ATTENTION_REQUIRED
    active_bcp_count: int
    residency_policies_count: int
