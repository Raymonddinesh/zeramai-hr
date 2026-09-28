"""
routers/governance.py - Module 15: Data Governance, Privacy, Retention & Business Continuity Endpoints.

All endpoints mounted under /api/v3/governance/...
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import AuditResult, User, UserRole, Person
from app.models_v3 import Tenant
from app.models_governance import (
    DataClassification,
    DataAsset,
    RetentionPolicy,
    RetentionPolicyAssignment,
    DataLifecycleRecord,
    LegalHold,
    LegalHoldTarget,
    PrivacyRequest,
    BackupPolicy,
    BackupExecution,
    DRPolicy,
    DRTest,
    BusinessContinuityPlan,
    BCPAction,
    DataResidencyPolicy,
    LegalHoldStatus,
    RecordLifecycleStatus,
    PrivacyRequestStatus,
    BackupStatus,
    DRTestStatus,
)
from app.schemas_governance import (
    DataClassificationCreate,
    DataClassificationUpdate,
    DataClassificationResponse,
    DataAssetCreate,
    DataAssetUpdate,
    DataAssetResponse,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    RetentionPolicyResponse,
    RetentionPolicyAssignmentCreate,
    RetentionPolicyAssignmentResponse,
    DataLifecycleRecordResponse,
    LifecycleEvaluateRequest,
    LifecycleEvaluateSummary,
    LegalHoldCreate,
    LegalHoldUpdate,
    LegalHoldResponse,
    LegalHoldTargetCreate,
    LegalHoldTargetResponse,
    PrivacyRequestCreate,
    PrivacyRequestUpdateStatus,
    PrivacyRequestResponse,
    PrivacyExportResponse,
    PrivacyAnonymizeResponse,
    BackupPolicyCreate,
    BackupPolicyUpdate,
    BackupPolicyResponse,
    BackupExecutionCreate,
    BackupExecutionResponse,
    DRPolicyCreate,
    DRPolicyUpdate,
    DRPolicyResponse,
    DRTestCreate,
    DRTestResponse,
    BCPCreate,
    BCPUpdate,
    BCPResponse,
    BCPActionCreate,
    BCPActionUpdate,
    BCPActionResponse,
    DataResidencyPolicyCreate,
    DataResidencyPolicyUpdate,
    DataResidencyPolicyResponse,
    GovernanceDashboardSummary,
)
from app.services.governance_service import (
    is_target_under_active_legal_hold,
    evaluate_record_lifecycle,
    export_data_subject_profile,
    anonymize_data_subject,
    get_governance_dashboard_metrics,
)

router = APIRouter(prefix="/api/v3/governance", tags=["governance"])


def _resolve_tenant_id(request: Request, db: Session, user: Optional[User] = None) -> str:
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    if user and user.person and getattr(user.person, "tenant_id", None):
        return user.person.tenant_id
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def _can_read_governance(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "governance:read", db)
        or has_permission(user, "governance:view", db)
        or has_permission(user, "governance:manage", db)
    )


def _can_manage_governance(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "governance:manage", db)
    )


# ---------------------------------------------------------------------------
# 1. Dashboard Overview
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=GovernanceDashboardSummary)
def get_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    metrics = get_governance_dashboard_metrics(db, tenant_id)
    return metrics


# ---------------------------------------------------------------------------
# 2. Data Classifications
# ---------------------------------------------------------------------------

@router.get("/classifications", response_model=List[DataClassificationResponse])
def list_classifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    items = db.query(DataClassification).filter(
        or_(DataClassification.tenant_id == tenant_id, DataClassification.tenant_id.is_(None))
    ).order_by(DataClassification.created_at.asc()).all()
    return items


@router.post("/classifications", response_model=DataClassificationResponse, status_code=status.HTTP_201_CREATED)
def create_classification(
    payload: DataClassificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    item = DataClassification(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        sensitivity_level=payload.sensitivity_level,
        default_retention_days=payload.default_retention_days,
        enabled=payload.enabled,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/classifications/{classification_id}", response_model=DataClassificationResponse)
def update_classification(
    classification_id: str,
    payload: DataClassificationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    item = db.query(DataClassification).filter(
        DataClassification.id == classification_id,
        or_(DataClassification.tenant_id == tenant_id, DataClassification.tenant_id.is_(None))
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classification not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# 3. Data Assets Inventory
# ---------------------------------------------------------------------------

@router.get("/assets", response_model=List[DataAssetResponse])
def list_assets(
    request: Request,
    module: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(DataAsset).filter(DataAsset.tenant_id == tenant_id)
    if module:
        query = query.filter(DataAsset.source_module == module)
    assets = query.order_by(DataAsset.name.asc()).all()

    resp = []
    for a in assets:
        r = DataAssetResponse.from_orm(a)
        if a.classification:
            r.classification_name = a.classification.name
        if a.retention_policy:
            r.retention_policy_name = a.retention_policy.name
        resp.append(r)
    return resp


@router.post("/assets", response_model=DataAssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: DataAssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    asset = DataAsset(
        tenant_id=tenant_id,
        name=payload.name,
        asset_type=payload.asset_type,
        source_module=payload.source_module,
        classification_id=payload.classification_id,
        legal_entity_id=payload.legal_entity_id,
        contains_personal_data=payload.contains_personal_data,
        contains_sensitive_personal_data=payload.contains_sensitive_personal_data,
        retention_policy_id=payload.retention_policy_id,
        data_residency=payload.data_residency,
        owner_user_id=payload.owner_user_id or current_user.id,
        status=payload.status,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.put("/assets/{asset_id}", response_model=DataAssetResponse)
def update_asset(
    asset_id: str,
    payload: DataAssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    asset = db.query(DataAsset).filter(DataAsset.id == asset_id, DataAsset.tenant_id == tenant_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(asset, k, v)
    db.commit()
    db.refresh(asset)
    return asset


# ---------------------------------------------------------------------------
# 4. Retention Policies
# ---------------------------------------------------------------------------

@router.get("/retention-policies", response_model=List[RetentionPolicyResponse])
def list_retention_policies(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return db.query(RetentionPolicy).filter(RetentionPolicy.tenant_id == tenant_id).all()


@router.post("/retention-policies", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_retention_policy(
    payload: RetentionPolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:retention:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Retention manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = RetentionPolicy(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        record_type=payload.record_type,
        retention_period_days=payload.retention_period_days,
        archive_after_days=payload.archive_after_days,
        deletion_after_days=payload.deletion_after_days,
        legal_basis=payload.legal_basis,
        jurisdiction=payload.jurisdiction,
        enabled=payload.enabled,
        created_by=current_user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/retention-policies/{policy_id}/assignments", response_model=RetentionPolicyAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_retention_policy(
    policy_id: str,
    payload: RetentionPolicyAssignmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:retention:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Retention manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = db.query(RetentionPolicy).filter(RetentionPolicy.id == policy_id, RetentionPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    assignment = RetentionPolicyAssignment(
        tenant_id=tenant_id,
        policy_id=policy_id,
        target_type=payload.target_type,
        target_reference=payload.target_reference,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


# ---------------------------------------------------------------------------
# 5. Record Lifecycle Management Engine
# ---------------------------------------------------------------------------

@router.get("/lifecycle/records", response_model=List[DataLifecycleRecordResponse])
def list_lifecycle_records(
    request: Request,
    status_filter: Optional[str] = None,
    asset_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(DataLifecycleRecord).filter(DataLifecycleRecord.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(DataLifecycleRecord.lifecycle_status == status_filter)
    if asset_type:
        query = query.filter(DataLifecycleRecord.asset_type == asset_type)

    return query.order_by(DataLifecycleRecord.last_evaluated_at.desc()).limit(limit).all()


@router.post("/lifecycle/evaluate", response_model=LifecycleEvaluateSummary)
def trigger_lifecycle_evaluation(
    payload: LifecycleEvaluateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:retention:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Retention manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    res = evaluate_record_lifecycle(
        db=db,
        tenant_id=tenant_id,
        asset_type=payload.asset_type,
        dry_run=payload.dry_run
    )
    return res


# ---------------------------------------------------------------------------
# 6. Legal Holds Framework
# ---------------------------------------------------------------------------

@router.get("/legal-holds", response_model=List[LegalHoldResponse])
def list_legal_holds(
    request: Request,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(LegalHold).filter(LegalHold.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(LegalHold.status == status_filter)
    return query.order_by(LegalHold.created_at.desc()).all()


@router.post("/legal-holds", response_model=LegalHoldResponse, status_code=status.HTTP_201_CREATED)
def create_legal_hold(
    payload: LegalHoldCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:legal_hold:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Legal hold manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    hold = LegalHold(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        matter_reference=payload.matter_reference,
        status=LegalHoldStatus.ACTIVE.value,
        issued_at=datetime.utcnow(),
        created_by=current_user.id,
    )
    db.add(hold)
    db.flush()

    for t in payload.targets:
        target = LegalHoldTarget(
            tenant_id=tenant_id,
            legal_hold_id=hold.id,
            target_type=t.target_type,
            target_reference=t.target_reference,
        )
        db.add(target)

    db.commit()
    db.refresh(hold)
    return hold


@router.get("/legal-holds/{hold_id}", response_model=LegalHoldResponse)
def get_legal_hold(
    hold_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    hold = db.query(LegalHold).filter(LegalHold.id == hold_id, LegalHold.tenant_id == tenant_id).first()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal hold not found")
    return hold


@router.post("/legal-holds/{hold_id}/release", response_model=LegalHoldResponse)
def release_legal_hold(
    hold_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:legal_hold:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Legal hold manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    hold = db.query(LegalHold).filter(LegalHold.id == hold_id, LegalHold.tenant_id == tenant_id).first()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal hold not found")

    hold.status = LegalHoldStatus.RELEASED.value
    hold.released_at = datetime.utcnow()
    hold.released_by = current_user.id
    db.commit()
    db.refresh(hold)
    return hold


@router.post("/legal-holds/{hold_id}/targets", response_model=LegalHoldTargetResponse, status_code=status.HTTP_201_CREATED)
def add_legal_hold_target(
    hold_id: str,
    payload: LegalHoldTargetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:legal_hold:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Legal hold manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    hold = db.query(LegalHold).filter(LegalHold.id == hold_id, LegalHold.tenant_id == tenant_id).first()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal hold not found")

    target = LegalHoldTarget(
        tenant_id=tenant_id,
        legal_hold_id=hold.id,
        target_type=payload.target_type,
        target_reference=payload.target_reference,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


# ---------------------------------------------------------------------------
# 7. Privacy Requests (DSR / DSAR)
# ---------------------------------------------------------------------------

@router.get("/privacy-requests", response_model=List[PrivacyRequestResponse])
def list_privacy_requests(
    request: Request,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(PrivacyRequest).filter(PrivacyRequest.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(PrivacyRequest.status == status_filter)
    reqs = query.order_by(PrivacyRequest.submitted_at.desc()).all()

    resp = []
    for r in reqs:
        p = PrivacyRequestResponse.from_orm(r)
        if r.person_id:
            person = db.query(Person).filter(Person.id == r.person_id).first()
            if person:
                p.person_name = person.full_name
        resp.append(p)
    return resp


@router.post("/privacy-requests", response_model=PrivacyRequestResponse, status_code=status.HTTP_201_CREATED)
def create_privacy_request(
    payload: PrivacyRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    
    # If not admin, normal users can only request for their own person_id
    person_id = payload.person_id
    if not _can_manage_governance(current_user, db):
        if not current_user.person_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No person identity linked to user")
        person_id = current_user.person_id

    req = PrivacyRequest(
        tenant_id=tenant_id,
        person_id=person_id,
        request_type=payload.request_type,
        status=PrivacyRequestStatus.SUBMITTED.value,
        submitted_at=datetime.utcnow(),
        due_at=datetime.utcnow() + timedelta(days=30),  # Statutory 30-day requirement
        assigned_to=payload.assigned_to,
        processing_notes=payload.processing_notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/privacy-requests/{request_id}", response_model=PrivacyRequestResponse)
def get_privacy_request(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    req = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id, PrivacyRequest.tenant_id == tenant_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    p = PrivacyRequestResponse.from_orm(req)
    if req.person_id:
        person = db.query(Person).filter(Person.id == req.person_id).first()
        if person:
            p.person_name = person.full_name
    return p


@router.patch("/privacy-requests/{request_id}/status", response_model=PrivacyRequestResponse)
def update_privacy_request_status(
    request_id: str,
    payload: PrivacyRequestUpdateStatus,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:privacy:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Privacy manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    req = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id, PrivacyRequest.tenant_id == tenant_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    req.status = payload.status
    if payload.rejection_reason:
        req.rejection_reason = payload.rejection_reason
    if payload.processing_notes:
        req.processing_notes = payload.processing_notes
    if payload.status in (PrivacyRequestStatus.COMPLETED.value, PrivacyRequestStatus.REJECTED.value, PrivacyRequestStatus.CANCELLED.value):
        req.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(req)
    return req


@router.post("/privacy-requests/{request_id}/export", response_model=PrivacyExportResponse)
def export_privacy_data(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:privacy:manage", db)
        or has_permission(current_user, "governance:privacy:export", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Privacy export permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    req = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id, PrivacyRequest.tenant_id == tenant_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if not req.person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No person associated with request")

    profile_data = export_data_subject_profile(db, tenant_id, req.person_id)
    
    req.status = PrivacyRequestStatus.COMPLETED.value
    req.completed_at = datetime.utcnow()
    req.export_reference = f"export_{req.person_id}_{int(datetime.utcnow().timestamp())}.json"
    db.commit()

    return {
        "request_id": req.id,
        "tenant_id": tenant_id,
        "person_id": req.person_id,
        "generated_at": datetime.utcnow(),
        "data": profile_data
    }


@router.post("/privacy-requests/{request_id}/anonymize", response_model=PrivacyAnonymizeResponse)
def execute_privacy_anonymization(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:privacy:delete", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Privacy deletion/anonymization permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    req = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id, PrivacyRequest.tenant_id == tenant_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if not req.person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No person associated with request")

    res = anonymize_data_subject(db, tenant_id, req.person_id)
    if res["blocked_by_legal_hold"]:
        req.status = PrivacyRequestStatus.REJECTED.value
        req.rejection_reason = res["message"]
        db.commit()
    else:
        req.status = PrivacyRequestStatus.COMPLETED.value
        req.completed_at = datetime.utcnow()
        req.processing_notes = "PII anonymized per statutory privacy request; historical tax/EPF compliance preserved."
        db.commit()

    return {
        "request_id": req.id,
        "tenant_id": tenant_id,
        "person_id": req.person_id,
        "success": res["success"],
        "message": res["message"],
        "anonymized_fields": res["anonymized_fields"],
        "preserved_records": res["preserved_records"],
        "blocked_by_legal_hold": res["blocked_by_legal_hold"],
    }


# ---------------------------------------------------------------------------
# 8. Backup Policies & Executions
# ---------------------------------------------------------------------------

@router.get("/backup-policies", response_model=List[BackupPolicyResponse])
def list_backup_policies(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policies = db.query(BackupPolicy).filter(BackupPolicy.tenant_id == tenant_id).all()
    resp = []
    for p in policies:
        r = BackupPolicyResponse.from_orm(p)
        r.recent_executions = [BackupExecutionResponse.from_orm(e) for e in p.executions[-5:]]
        resp.append(r)
    return resp


@router.post("/backup-policies", response_model=BackupPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_backup_policy(
    payload: BackupPolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:backup:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Backup manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = BackupPolicy(
        tenant_id=tenant_id,
        name=payload.name,
        frequency=payload.frequency,
        retention_days=payload.retention_days,
        encryption_required=payload.encryption_required,
        offsite_required=payload.offsite_required,
        cross_region_required=payload.cross_region_required,
        enabled=payload.enabled,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/backup-executions", response_model=List[BackupExecutionResponse])
def list_backup_executions(
    request: Request,
    policy_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(BackupExecution).filter(BackupExecution.tenant_id == tenant_id)
    if policy_id:
        query = query.filter(BackupExecution.backup_policy_id == policy_id)
    return query.order_by(BackupExecution.started_at.desc()).limit(limit).all()


@router.post("/backup-executions", response_model=BackupExecutionResponse, status_code=status.HTTP_201_CREATED)
def record_backup_execution(
    payload: BackupExecutionCreate,
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:backup:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Backup manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = db.query(BackupPolicy).filter(BackupPolicy.id == policy_id, BackupPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup policy not found")

    now = datetime.utcnow()
    exec_rec = BackupExecution(
        tenant_id=tenant_id,
        backup_policy_id=policy.id,
        started_at=now,
        completed_at=now,
        status=payload.status,
        backup_reference=payload.backup_reference or f"snap-{uuid.uuid4().hex[:12]}",
        size_bytes=payload.size_bytes,
        checksum=payload.checksum or f"sha256:{uuid.uuid4().hex}",
        region=payload.region,
        encryption_status="ENCRYPTED_AES256" if policy.encryption_required else "UNENCRYPTED",
        verification_status="VERIFIED",
    )
    db.add(exec_rec)
    db.commit()
    db.refresh(exec_rec)
    return exec_rec


# ---------------------------------------------------------------------------
# 9. Disaster Recovery (DR)
# ---------------------------------------------------------------------------

@router.get("/dr-policies", response_model=List[DRPolicyResponse])
def list_dr_policies(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policies = db.query(DRPolicy).filter(DRPolicy.tenant_id == tenant_id).all()
    resp = []
    for p in policies:
        r = DRPolicyResponse.from_orm(p)
        r.tests = [DRTestResponse.from_orm(t) for t in p.tests]
        resp.append(r)
    return resp


@router.post("/dr-policies", response_model=DRPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_dr_policy(
    payload: DRPolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:dr:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DR manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = DRPolicy(
        tenant_id=tenant_id,
        name=payload.name,
        rpo_minutes=payload.rpo_minutes,
        rto_minutes=payload.rto_minutes,
        primary_region=payload.primary_region,
        recovery_region=payload.recovery_region,
        priority=payload.priority,
        enabled=payload.enabled,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/dr-tests", response_model=List[DRTestResponse])
def list_dr_tests(
    request: Request,
    policy_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(DRTest).filter(DRTest.tenant_id == tenant_id)
    if policy_id:
        query = query.filter(DRTest.dr_policy_id == policy_id)
    return query.order_by(DRTest.started_at.desc()).all()


@router.post("/dr-tests", response_model=DRTestResponse, status_code=status.HTTP_201_CREATED)
def record_dr_test(
    payload: DRTestCreate,
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:dr:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DR manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = db.query(DRPolicy).filter(DRPolicy.id == policy_id, DRPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DR policy not found")

    now = datetime.utcnow()
    test = DRTest(
        tenant_id=tenant_id,
        dr_policy_id=policy.id,
        test_type=payload.test_type,
        started_at=now - timedelta(minutes=payload.actual_rto_minutes or 30),
        completed_at=now,
        status=payload.status,
        actual_rpo_minutes=payload.actual_rpo_minutes or policy.rpo_minutes,
        actual_rto_minutes=payload.actual_rto_minutes or policy.rto_minutes,
        findings=payload.findings,
        corrective_actions=payload.corrective_actions,
        tested_by=current_user.id,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


# ---------------------------------------------------------------------------
# 10. Business Continuity Plans (BCP)
# ---------------------------------------------------------------------------

@router.get("/bcp", response_model=List[BCPResponse])
def list_bcp_plans(
    request: Request,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(BusinessContinuityPlan).filter(BusinessContinuityPlan.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(BusinessContinuityPlan.status == status_filter)
    plans = query.order_by(BusinessContinuityPlan.created_at.desc()).all()

    resp = []
    for p in plans:
        r = BCPResponse.from_orm(p)
        r.actions = [BCPActionResponse.from_orm(a) for a in p.actions]
        resp.append(r)
    return resp


@router.post("/bcp", response_model=BCPResponse, status_code=status.HTTP_201_CREATED)
def create_bcp_plan(
    payload: BCPCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:bcp:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BCP manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = BusinessContinuityPlan(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        criticality=payload.criticality,
        owner_user_id=payload.owner_user_id or current_user.id,
        recovery_strategy=payload.recovery_strategy,
        status=payload.status,
        last_reviewed_at=datetime.utcnow(),
        next_review_at=datetime.utcnow() + timedelta(days=180),
    )
    db.add(plan)
    db.flush()

    for act in payload.actions:
        action_item = BCPAction(
            tenant_id=tenant_id,
            plan_id=plan.id,
            sequence=act.sequence,
            action=act.action,
            owner_user_id=act.owner_user_id or current_user.id,
            status=act.status,
        )
        db.add(action_item)

    db.commit()
    db.refresh(plan)
    return plan


@router.get("/bcp/{plan_id}", response_model=BCPResponse)
def get_bcp_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = db.query(BusinessContinuityPlan).filter(
        BusinessContinuityPlan.id == plan_id,
        BusinessContinuityPlan.tenant_id == tenant_id
    ).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BCP plan not found")
    
    r = BCPResponse.from_orm(plan)
    r.actions = [BCPActionResponse.from_orm(a) for a in plan.actions]
    return r


@router.post("/bcp/{plan_id}/actions", response_model=BCPActionResponse, status_code=status.HTTP_201_CREATED)
def add_bcp_action(
    plan_id: str,
    payload: BCPActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:bcp:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BCP manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = db.query(BusinessContinuityPlan).filter(
        BusinessContinuityPlan.id == plan_id,
        BusinessContinuityPlan.tenant_id == tenant_id
    ).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BCP plan not found")

    action_item = BCPAction(
        tenant_id=tenant_id,
        plan_id=plan.id,
        sequence=payload.sequence,
        action=payload.action,
        owner_user_id=payload.owner_user_id or current_user.id,
        status=payload.status,
    )
    db.add(action_item)
    db.commit()
    db.refresh(action_item)
    return action_item


@router.patch("/bcp/actions/{action_id}", response_model=BCPActionResponse)
def update_bcp_action(
    action_id: str,
    payload: BCPActionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:bcp:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BCP manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    action_item = db.query(BCPAction).filter(
        BCPAction.id == action_id,
        BCPAction.tenant_id == tenant_id
    ).first()
    if not action_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BCP Action not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(action_item, k, v)
    if payload.status == "COMPLETED" and not action_item.completed_at:
        action_item.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(action_item)
    return action_item


# ---------------------------------------------------------------------------
# 11. Data Residency Policies
# ---------------------------------------------------------------------------

@router.get("/residency-policies", response_model=List[DataResidencyPolicyResponse])
def list_residency_policies(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_governance(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return db.query(DataResidencyPolicy).filter(DataResidencyPolicy.tenant_id == tenant_id).all()


@router.post("/residency-policies", response_model=DataResidencyPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_residency_policy(
    payload: DataResidencyPolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_governance(current_user, db)
        or has_permission(current_user, "governance:residency:manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Residency manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    policy = DataResidencyPolicy(
        tenant_id=tenant_id,
        data_category=payload.data_category,
        allowed_regions=payload.allowed_regions,
        primary_region=payload.primary_region,
        cross_border_transfer_allowed=payload.cross_border_transfer_allowed,
        transfer_basis=payload.transfer_basis,
        enabled=payload.enabled,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy
