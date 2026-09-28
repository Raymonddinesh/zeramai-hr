"""
governance_service.py - Module 15: Core business logic for Data Governance, Retention, Legal Holds, and Privacy.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models import (
    Person, User, Engagement, Document, Candidate, Stipend, Evaluation
)
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
)


# ---------------------------------------------------------------------------
# Legal Holds Service
# ---------------------------------------------------------------------------

def is_target_under_active_legal_hold(
    db: Session,
    tenant_id: str,
    target_reference: str,
    target_type: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Checks if a target record/person/document is subject to any ACTIVE legal hold.
    Returns (is_held, hold_matter_reference).
    """
    query = (
        db.query(LegalHoldTarget, LegalHold)
        .join(LegalHold, LegalHoldTarget.legal_hold_id == LegalHold.id)
        .filter(
            LegalHold.tenant_id == tenant_id,
            LegalHold.status == LegalHoldStatus.ACTIVE.value,
            LegalHoldTarget.target_reference == target_reference
        )
    )
    if target_type:
        query = query.filter(LegalHoldTarget.target_type == target_type)

    result = query.first()
    if result:
        _, hold = result
        return True, hold.matter_reference
    return False, None


# ---------------------------------------------------------------------------
# Lifecycle Evaluation Engine
# ---------------------------------------------------------------------------

def evaluate_record_lifecycle(
    db: Session,
    tenant_id: str,
    asset_type: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Idempotently evaluates lifecycle records against retention policies and active legal holds.
    Transitions:
    ACTIVE -> ARCHIVE_ELIGIBLE -> ARCHIVED -> DELETION_ELIGIBLE
    Active legal hold freezes state and prevents archive/deletion transitions.
    """
    now = datetime.utcnow()
    query = db.query(DataLifecycleRecord).filter(DataLifecycleRecord.tenant_id == tenant_id)
    if asset_type:
        query = query.filter(DataLifecycleRecord.asset_type == asset_type)

    records = query.all()
    
    # If no records exist, index existing governed assets / documents into lifecycle records
    if not records:
        # Auto-discover documents
        docs = db.query(Document).all()
        for doc in docs:
            # find default retention policy for DOCUMENT
            policy = db.query(RetentionPolicy).filter(
                RetentionPolicy.tenant_id == tenant_id,
                RetentionPolicy.record_type == "DOCUMENT"
            ).first()
            new_rec = DataLifecycleRecord(
                tenant_id=tenant_id,
                asset_type="DOCUMENT",
                asset_id=doc.id,
                retention_policy_id=policy.id if policy else None,
                lifecycle_status=RecordLifecycleStatus.ACTIVE.value,
                created_at=doc.created_at or now,
                last_evaluated_at=now
            )
            db.add(new_rec)
        db.flush()
        records = query.all()

    total_evaluated = 0
    eligible_for_archive = 0
    archived_count = 0
    eligible_for_deletion = 0
    blocked_by_legal_hold = 0

    for rec in records:
        total_evaluated += 1
        
        # Check active legal hold
        is_held, _ = is_target_under_active_legal_hold(db, tenant_id, rec.asset_id)
        if is_held:
            blocked_by_legal_hold += 1
            if not dry_run:
                rec.legal_hold = True
                rec.last_evaluated_at = now
            continue
        else:
            if not dry_run:
                rec.legal_hold = False

        # Evaluate against retention policy
        policy = None
        if rec.retention_policy_id:
            policy = db.query(RetentionPolicy).filter(RetentionPolicy.id == rec.retention_policy_id).first()
        if not policy:
            policy = db.query(RetentionPolicy).filter(
                RetentionPolicy.tenant_id == tenant_id,
                RetentionPolicy.record_type == rec.asset_type,
                RetentionPolicy.enabled.is_(True)
            ).first()

        if not policy:
            if not dry_run:
                rec.last_evaluated_at = now
            continue

        age_days = (now - rec.created_at).days

        # Check deletion eligibility first
        if policy.deletion_after_days and age_days >= policy.deletion_after_days:
            eligible_for_deletion += 1
            if not dry_run:
                rec.lifecycle_status = RecordLifecycleStatus.DELETION_ELIGIBLE.value
                rec.eligible_delete_at = rec.eligible_delete_at or now

        elif age_days >= policy.retention_period_days:
            eligible_for_deletion += 1
            if not dry_run:
                rec.lifecycle_status = RecordLifecycleStatus.DELETION_ELIGIBLE.value
                rec.eligible_delete_at = rec.eligible_delete_at or now

        # Check archive eligibility
        elif age_days >= policy.archive_after_days:
            eligible_for_archive += 1
            if not dry_run:
                rec.lifecycle_status = RecordLifecycleStatus.ARCHIVE_ELIGIBLE.value
                rec.eligible_archive_at = rec.eligible_archive_at or now

        if rec.lifecycle_status == RecordLifecycleStatus.ARCHIVED.value:
            archived_count += 1

        if not dry_run:
            rec.last_evaluated_at = now

    if not dry_run:
        db.commit()

    return {
        "total_evaluated": total_evaluated,
        "eligible_for_archive": eligible_for_archive,
        "archived_count": archived_count,
        "eligible_for_deletion": eligible_for_deletion,
        "blocked_by_legal_hold": blocked_by_legal_hold,
        "dry_run": dry_run,
        "evaluation_timestamp": now
    }


# ---------------------------------------------------------------------------
# Privacy Requests (DSR / DSAR): Data Subject Export
# ---------------------------------------------------------------------------

def export_data_subject_profile(
    db: Session,
    tenant_id: str,
    person_id: str
) -> Dict[str, Any]:
    """
    Assembles a complete, sanitized export of all personal and employment data for a person.
    STRICT SECURITY RULE: Passwords, tokens, api keys, and encrypted secrets are NEVER included.
    """
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise ValueError(f"Person with ID {person_id} not found")

    # Person Info
    person_data = {
        "id": person.id,
        "full_name": person.full_name,
        "preferred_name": person.preferred_name,
        "email": person.email,
        "phone": person.phone,
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "gender": person.gender,
        "current_address": person.current_address,
        "permanent_address": person.permanent_address,
        "emergency_contact": person.emergency_contact,
        "created_at": person.created_at.isoformat() if person.created_at else None,
    }

    # User Accounts (Strictly sanitize secrets)
    user = db.query(User).filter(User.person_id == person_id).first()
    user_data = None
    if user:
        user_data = {
            "id": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "password_hash": "[REDACTED_SECURITY_POLICY]",
        }

    # Engagements
    engagements = db.query(Engagement).filter(Engagement.person_id == person_id).all()
    eng_list = []
    for eng in engagements:
        eng_list.append({
            "id": eng.id,
            "engagement_type": eng.engagement_type.value if hasattr(eng.engagement_type, "value") else str(eng.engagement_type),
            "status": eng.status.value if hasattr(eng.status, "value") else str(eng.status),
            "designation": eng.designation,
            "department": eng.department,
            "start_date": eng.start_date.isoformat() if eng.start_date else None,
            "end_date": eng.end_date.isoformat() if eng.end_date else None,
        })

    # Documents (Metadata only)
    docs = db.query(Document).filter(Document.person_id == person_id).all()
    doc_list = []
    for doc in docs:
        doc_list.append({
            "id": doc.id,
            "document_type": doc.document_type,
            "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
            "file_name": doc.file_name,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })

    # Candidate info
    candidate = db.query(Candidate).filter(Candidate.person_id == person_id).first()
    candidate_data = None
    if candidate:
        candidate_data = {
            "applied_position": candidate.applied_position,
            "department": candidate.department,
            "application_date": candidate.application_date.isoformat() if candidate.application_date else None,
        }

    # Evaluations
    evals = db.query(Evaluation).filter(Evaluation.person_id == person_id).all()
    eval_list = []
    for ev in evals:
        eval_list.append({
            "id": ev.id,
            "period_start": ev.period_start.isoformat() if ev.period_start else None,
            "period_end": ev.period_end.isoformat() if ev.period_end else None,
            "overall_rating": float(ev.overall_rating) if ev.overall_rating is not None else None,
            "status": ev.status.value if hasattr(ev.status, "value") else str(ev.status),
        })

    # Stipends
    stipends = db.query(Stipend).filter(Stipend.person_id == person_id).all()
    stipend_list = []
    for st in stipends:
        stipend_list.append({
            "id": st.id,
            "month": st.month,
            "amount": float(st.amount) if st.amount is not None else 0.0,
            "currency": st.currency,
            "status": st.status.value if hasattr(st.status, "value") else str(st.status),
        })

    return {
        "person": person_data,
        "user_account": user_data,
        "engagements": eng_list,
        "documents": doc_list,
        "recruitment": candidate_data,
        "evaluations": eval_list,
        "stipends": stipend_list,
        "statutory_records_notice": "Statutory payroll and tax filings are retained in accordance with the Income Tax Act 1961 and EPF Act.",
    }


# ---------------------------------------------------------------------------
# Privacy Requests: Controlled Anonymization / Erasure
# ---------------------------------------------------------------------------

def anonymize_data_subject(
    db: Session,
    tenant_id: str,
    person_id: str
) -> Dict[str, Any]:
    """
    Executes controlled anonymization/erasure of personal data.
    - Strictly blocks if active legal hold is present.
    - Anonymizes PII fields in Person and deactivates User account.
    - Preserves statutory/tax/EPF compliance and payroll records.
    - Updates DataLifecycleRecord to ANONYMIZED.
    """
    # 1. Check legal hold
    is_held, matter_ref = is_target_under_active_legal_hold(db, tenant_id, person_id)
    if is_held:
        return {
            "success": False,
            "message": f"Anonymization blocked: Target person is subject to active Legal Hold matter '{matter_ref}'.",
            "anonymized_fields": [],
            "preserved_records": ["All records preserved due to legal hold"],
            "blocked_by_legal_hold": True
        }

    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise ValueError(f"Person with ID {person_id} not found")

    now = datetime.utcnow()
    anonymized_fields = []

    # 2. Anonymize Person PII
    person.full_name = "Anonymized Employee"
    person.preferred_name = None
    person.email = f"anonymized_{person.id[:8]}@redacted.local"
    person.phone = "REDACTED"
    person.current_address = "REDACTED"
    person.permanent_address = "REDACTED"
    person.emergency_contact = "REDACTED"
    anonymized_fields.extend(["full_name", "preferred_name", "email", "phone", "addresses", "emergency_contact"])

    # 3. Deactivate User Account
    user = db.query(User).filter(User.person_id == person_id).first()
    if user:
        user.email = f"anonymized_{user.id[:8]}@redacted.local"
        user.is_active = False
        anonymized_fields.extend(["user_login", "user_status"])

    # 4. Update Lifecycle Record
    lifecycle_rec = db.query(DataLifecycleRecord).filter(
        DataLifecycleRecord.tenant_id == tenant_id,
        DataLifecycleRecord.asset_id == person_id
    ).first()
    if lifecycle_rec:
        lifecycle_rec.lifecycle_status = RecordLifecycleStatus.ANONYMIZED.value
        lifecycle_rec.anonymized_at = now
    else:
        lifecycle_rec = DataLifecycleRecord(
            tenant_id=tenant_id,
            asset_type="PERSON",
            asset_id=person_id,
            lifecycle_status=RecordLifecycleStatus.ANONYMIZED.value,
            anonymized_at=now,
            last_evaluated_at=now
        )
        db.add(lifecycle_rec)

    db.commit()

    preserved_records = [
        "Income Tax Act 1961 statutory payroll run history",
        "Employees' Provident Fund (EPF) and ESI historical contribution records",
        "Financial ledger audit trails",
    ]

    return {
        "success": True,
        "message": "Data subject PII successfully anonymized while maintaining statutory compliance archives.",
        "anonymized_fields": anonymized_fields,
        "preserved_records": preserved_records,
        "blocked_by_legal_hold": False
    }


# ---------------------------------------------------------------------------
# Dashboard Overview Aggregation
# ---------------------------------------------------------------------------

def get_governance_dashboard_metrics(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Computes summary metrics for the Governance Console dashboard.
    """
    classifications_count = db.query(DataClassification).filter(
        or_(DataClassification.tenant_id == tenant_id, DataClassification.tenant_id.is_(None))
    ).count()

    data_assets_count = db.query(DataAsset).filter(DataAsset.tenant_id == tenant_id).count()
    retention_policies_count = db.query(RetentionPolicy).filter(RetentionPolicy.tenant_id == tenant_id).count()
    active_legal_holds_count = db.query(LegalHold).filter(
        LegalHold.tenant_id == tenant_id,
        LegalHold.status == LegalHoldStatus.ACTIVE.value
    ).count()

    pending_privacy_requests_count = db.query(PrivacyRequest).filter(
        PrivacyRequest.tenant_id == tenant_id,
        PrivacyRequest.status.in_([PrivacyRequestStatus.SUBMITTED.value, PrivacyRequestStatus.IN_REVIEW.value, PrivacyRequestStatus.PROCESSING.value])
    ).count()

    total_privacy_requests_count = db.query(PrivacyRequest).filter(PrivacyRequest.tenant_id == tenant_id).count()

    # Backup metrics
    last_exec = db.query(BackupExecution).filter(
        BackupExecution.tenant_id == tenant_id
    ).order_by(BackupExecution.started_at.desc()).first()

    backup_status = "HEALTHY"
    if not last_exec or last_exec.status == BackupStatus.FAILED.value:
        backup_status = "WARNING"
    elif (datetime.utcnow() - last_exec.started_at).days > 3:
        backup_status = "WARNING"

    # DR readiness
    dr_tests = db.query(DRTest).filter(DRTest.tenant_id == tenant_id).all()
    failed_tests = [t for t in dr_tests if t.status == "FAILED"]
    dr_readiness = "READY" if not failed_tests else "ATTENTION_REQUIRED"

    active_bcp_count = db.query(BusinessContinuityPlan).filter(
        BusinessContinuityPlan.tenant_id == tenant_id,
        BusinessContinuityPlan.status == "ACTIVE"
    ).count()

    residency_policies_count = db.query(DataResidencyPolicy).filter(
        DataResidencyPolicy.tenant_id == tenant_id
    ).count()

    return {
        "classifications_count": classifications_count,
        "data_assets_count": data_assets_count,
        "retention_policies_count": retention_policies_count,
        "active_legal_holds_count": active_legal_holds_count,
        "pending_privacy_requests_count": pending_privacy_requests_count,
        "total_privacy_requests_count": total_privacy_requests_count,
        "backup_status": backup_status,
        "last_backup_at": last_exec.completed_at if last_exec else None,
        "dr_readiness_status": dr_readiness,
        "active_bcp_count": active_bcp_count,
        "residency_policies_count": residency_policies_count,
    }
