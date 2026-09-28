"""
routers/hr_policies.py - Module 8: HR Policy Management Router.

Endpoints:
- GET  /api/v3/hr-policies
- POST /api/v3/hr-policies
- GET  /api/v3/hr-policies/my/applicable
- GET  /api/v3/hr-policies/my/acknowledgements
- GET  /api/v3/hr-policies/{id}
- POST /api/v3/hr-policies/{id}/versions
- POST /api/v3/hr-policies/{id}/submit
- POST /api/v3/hr-policies/{id}/approve
- POST /api/v3/hr-policies/{id}/publish
- POST /api/v3/hr-policies/{id}/archive
- POST /api/v3/hr-policies/{id}/acknowledge
- GET  /api/v3/hr-policies/{id}/acknowledgements
- GET  /api/v3/hr-policies/{id}/compliance-status
"""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, require_permission, log_audit
from app.models import (
    AuditResult,
    User,
    UserRole,
    Person,
    Engagement,
)
from app.models_policy_er import (
    HRPolicy,
    PolicyAcknowledgementRecord,
    HRPolicyStatus,
    HRPolicyCategory,
)
from app.schemas_policy_er import (
    HRPolicyCreate,
    HRPolicyVersionCreate,
    HRPolicyOut,
    PolicyAcknowledgementOut,
    PolicyComplianceStatusOut,
)

router = APIRouter(prefix="/api/v3/hr-policies", tags=["hr_policies"])


def is_hr_or_super(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


# ===========================================================================
# 1. Policy Listing & Applicability Filtering
# ===========================================================================

@router.get("", response_model=List[HRPolicyOut])
def list_policies(
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List policies.
    - HR / Super Admin sees all policies across all statuses and versions.
    - Regular employees see only PUBLISHED policies applicable to their profile.
    """
    query = db.query(HRPolicy)

    if is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db):
        if status_filter:
            query = query.filter(HRPolicy.status == status_filter)
    else:
        # Regular employee: only published policies
        query = query.filter(HRPolicy.status == HRPolicyStatus.PUBLISHED)

        # Check applicability if person is mapped
        if current_user.person_id:
            eng = db.query(Engagement).filter(
                Engagement.person_id == current_user.person_id,
                Engagement.status == "active"
            ).first()
            if eng:
                query = query.filter(
                    (HRPolicy.department_id == None) | (HRPolicy.department_id == eng.department),
                    (HRPolicy.employment_type == None) | (HRPolicy.employment_type == str(eng.engagement_type.value if hasattr(eng.engagement_type, 'value') else eng.engagement_type))
                )

    if category:
        query = query.filter(HRPolicy.category == category)

    policies = query.order_by(HRPolicy.policy_code.asc(), HRPolicy.version.desc()).all()

    # Pre-fetch user acknowledgements if employee
    ack_policy_ids = set()
    if current_user.person_id:
        acks = db.query(PolicyAcknowledgementRecord.policy_id).filter(
            PolicyAcknowledgementRecord.person_id == current_user.person_id
        ).all()
        ack_policy_ids = {a[0] for a in acks}

    results = []
    for p in policies:
        results.append(
            HRPolicyOut(
                id=p.id,
                title=p.title,
                policy_code=p.policy_code,
                category=p.category,
                description=p.description,
                content=p.content,
                version=p.version,
                status=p.status,
                effective_date=p.effective_date,
                review_date=p.review_date,
                legal_entity_id=p.legal_entity_id,
                department_id=p.department_id,
                employment_type=p.employment_type,
                is_mandatory=p.is_mandatory,
                previous_version_id=p.previous_version_id,
                created_by_id=p.created_by_id,
                approved_by_id=p.approved_by_id,
                approved_at=p.approved_at,
                published_by_id=p.published_by_id,
                published_at=p.published_at,
                archived_at=p.archived_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
                has_acknowledged=p.id in ack_policy_ids,
            )
        )
    return results


@router.get("/my/applicable", response_model=List[HRPolicyOut])
def get_my_applicable_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Employee self-service: list all published policies applicable to the current employee."""
    if not current_user.person_id:
        return []

    eng = db.query(Engagement).filter(
        Engagement.person_id == current_user.person_id,
        Engagement.status == "active"
    ).first()

    query = db.query(HRPolicy).filter(HRPolicy.status == HRPolicyStatus.PUBLISHED)
    if eng:
        emp_type_str = str(eng.engagement_type.value if hasattr(eng.engagement_type, 'value') else eng.engagement_type)
        query = query.filter(
            (HRPolicy.department_id == None) | (HRPolicy.department_id == eng.department),
            (HRPolicy.employment_type == None) | (HRPolicy.employment_type == emp_type_str)
        )

    policies = query.order_by(HRPolicy.title.asc()).all()

    acks = db.query(PolicyAcknowledgementRecord.policy_id).filter(
        PolicyAcknowledgementRecord.person_id == current_user.person_id
    ).all()
    ack_set = {a[0] for a in acks}

    return [
        HRPolicyOut(
            id=p.id,
            title=p.title,
            policy_code=p.policy_code,
            category=p.category,
            description=p.description,
            content=p.content,
            version=p.version,
            status=p.status,
            effective_date=p.effective_date,
            review_date=p.review_date,
            legal_entity_id=p.legal_entity_id,
            department_id=p.department_id,
            employment_type=p.employment_type,
            is_mandatory=p.is_mandatory,
            previous_version_id=p.previous_version_id,
            created_by_id=p.created_by_id,
            approved_by_id=p.approved_by_id,
            approved_at=p.approved_at,
            published_by_id=p.published_by_id,
            published_at=p.published_at,
            archived_at=p.archived_at,
            created_at=p.created_at,
            updated_at=p.updated_at,
            has_acknowledged=p.id in ack_set,
        ) for p in policies
    ]


@router.get("/my/acknowledgements", response_model=List[PolicyAcknowledgementOut])
def get_my_acknowledgements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Employee self-service: list own policy acknowledgement history."""
    if not current_user.person_id:
        return []

    acks = db.query(PolicyAcknowledgementRecord).filter(
        PolicyAcknowledgementRecord.person_id == current_user.person_id
    ).order_by(PolicyAcknowledgementRecord.acknowledged_at.desc()).all()

    results = []
    for a in acks:
        pol = db.query(HRPolicy).filter(HRPolicy.id == a.policy_id).first()
        results.append(
            PolicyAcknowledgementOut(
                id=a.id,
                policy_id=a.policy_id,
                policy_title=pol.title if pol else None,
                policy_version=a.policy_version,
                person_id=a.person_id,
                person_name=None,
                acknowledged_at=a.acknowledged_at,
                ip_address=a.ip_address,
                status=a.status,
            )
        )
    return results


# ===========================================================================
# 2. Policy CRUD & Lifecycle
# ===========================================================================

@router.post("", response_model=HRPolicyOut, status_code=201)
def create_policy(
    payload: HRPolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new draft policy (HR/Admin)."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create HR policy")

    policy = HRPolicy(
        title=payload.title,
        policy_code=payload.policy_code,
        category=payload.category,
        description=payload.description,
        content=payload.content,
        version="1.0",
        status=HRPolicyStatus.DRAFT,
        effective_date=payload.effective_date,
        review_date=payload.review_date,
        legal_entity_id=payload.legal_entity_id,
        department_id=payload.department_id,
        employment_type=payload.employment_type,
        is_mandatory=payload.is_mandatory,
        created_by_id=current_user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    log_audit(
        db, user=current_user, action="hr_policy_created",
        entity="hr_policy", entity_id=policy.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"code": policy.policy_code, "version": policy.version}
    )

    return HRPolicyOut(
        id=policy.id,
        title=policy.title,
        policy_code=policy.policy_code,
        category=policy.category,
        description=policy.description,
        content=policy.content,
        version=policy.version,
        status=policy.status,
        effective_date=policy.effective_date,
        review_date=policy.review_date,
        legal_entity_id=policy.legal_entity_id,
        department_id=policy.department_id,
        employment_type=policy.employment_type,
        is_mandatory=policy.is_mandatory,
        previous_version_id=None,
        created_by_id=policy.created_by_id,
        approved_by_id=None,
        approved_at=None,
        published_by_id=None,
        published_at=None,
        archived_at=None,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        has_acknowledged=False,
    )


@router.get("/{policy_id}", response_model=HRPolicyOut)
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve policy details."""
    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    is_hr = is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db)
    if not is_hr:
        if policy.status != HRPolicyStatus.PUBLISHED:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Policy is not published")

    has_ack = False
    if current_user.person_id:
        ack = db.query(PolicyAcknowledgementRecord).filter(
            PolicyAcknowledgementRecord.policy_id == policy.id,
            PolicyAcknowledgementRecord.person_id == current_user.person_id
        ).first()
        has_ack = ack is not None

    return HRPolicyOut(
        id=policy.id,
        title=policy.title,
        policy_code=policy.policy_code,
        category=policy.category,
        description=policy.description,
        content=policy.content,
        version=policy.version,
        status=policy.status,
        effective_date=policy.effective_date,
        review_date=policy.review_date,
        legal_entity_id=policy.legal_entity_id,
        department_id=policy.department_id,
        employment_type=policy.employment_type,
        is_mandatory=policy.is_mandatory,
        previous_version_id=policy.previous_version_id,
        created_by_id=policy.created_by_id,
        approved_by_id=policy.approved_by_id,
        approved_at=policy.approved_at,
        published_by_id=policy.published_by_id,
        published_at=policy.published_at,
        archived_at=policy.archived_at,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        has_acknowledged=has_ack,
    )


@router.post("/{policy_id}/versions", response_model=HRPolicyOut, status_code=201)
def create_policy_version(
    policy_id: str,
    payload: HRPolicyVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new version of an existing policy.
    Preserves historical published version immutability.
    """
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to version policy")

    parent = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not parent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent policy not found")

    new_version_policy = HRPolicy(
        title=parent.title,
        policy_code=parent.policy_code,
        category=parent.category,
        description=payload.description or parent.description,
        content=payload.content,
        version=payload.version,
        status=HRPolicyStatus.DRAFT,
        effective_date=payload.effective_date,
        review_date=payload.review_date,
        legal_entity_id=parent.legal_entity_id,
        department_id=parent.department_id,
        employment_type=parent.employment_type,
        is_mandatory=parent.is_mandatory,
        previous_version_id=parent.id,
        created_by_id=current_user.id,
    )
    db.add(new_version_policy)
    db.commit()
    db.refresh(new_version_policy)

    log_audit(
        db, user=current_user, action="hr_policy_version_created",
        entity="hr_policy", entity_id=new_version_policy.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"code": new_version_policy.policy_code, "version": new_version_policy.version}
    )

    return HRPolicyOut(
        id=new_version_policy.id,
        title=new_version_policy.title,
        policy_code=new_version_policy.policy_code,
        category=new_version_policy.category,
        description=new_version_policy.description,
        content=new_version_policy.content,
        version=new_version_policy.version,
        status=new_version_policy.status,
        effective_date=new_version_policy.effective_date,
        review_date=new_version_policy.review_date,
        legal_entity_id=new_version_policy.legal_entity_id,
        department_id=new_version_policy.department_id,
        employment_type=new_version_policy.employment_type,
        is_mandatory=new_version_policy.is_mandatory,
        previous_version_id=new_version_policy.previous_version_id,
        created_by_id=new_version_policy.created_by_id,
        approved_by_id=None,
        approved_at=None,
        published_by_id=None,
        published_at=None,
        archived_at=None,
        created_at=new_version_policy.created_at,
        updated_at=new_version_policy.updated_at,
        has_acknowledged=False,
    )


@router.post("/{policy_id}/submit", response_model=HRPolicyOut)
def submit_policy_for_review(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a draft policy for review."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    if policy.status != HRPolicyStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Policy cannot be submitted from status {policy.status}")

    policy.status = HRPolicyStatus.REVIEW
    db.commit()
    db.refresh(policy)

    log_audit(
        db, user=current_user, action="hr_policy_submitted_for_review",
        entity="hr_policy", entity_id=policy.id,
        result=AuditResult.SUCCESS, request=request,
    )
    return policy


@router.post("/{policy_id}/approve", response_model=HRPolicyOut)
def approve_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a policy in review."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    if policy.status not in (HRPolicyStatus.DRAFT, HRPolicyStatus.REVIEW):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Policy cannot be approved from status {policy.status}")

    policy.status = HRPolicyStatus.APPROVED
    policy.approved_by_id = current_user.id
    policy.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)

    log_audit(
        db, user=current_user, action="hr_policy_approved",
        entity="hr_policy", entity_id=policy.id,
        result=AuditResult.SUCCESS, request=request,
    )
    return policy


@router.post("/{policy_id}/publish", response_model=HRPolicyOut)
def publish_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Publish an approved policy.
    Archives any previous published version of the same policy_code to keep lineage intact.
    """
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:publish", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to publish policy")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    if policy.status != HRPolicyStatus.APPROVED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Policy must be approved before publication")

    # Archive previous published versions with same code
    previous_published = db.query(HRPolicy).filter(
        HRPolicy.policy_code == policy.policy_code,
        HRPolicy.status == HRPolicyStatus.PUBLISHED,
        HRPolicy.id != policy.id,
    ).all()

    for old_p in previous_published:
        old_p.status = HRPolicyStatus.ARCHIVED
        old_p.archived_at = datetime.utcnow()

    policy.status = HRPolicyStatus.PUBLISHED
    policy.published_by_id = current_user.id
    policy.published_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)

    log_audit(
        db, user=current_user, action="hr_policy_published",
        entity="hr_policy", entity_id=policy.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"code": policy.policy_code, "version": policy.version}
    )
    return policy


@router.post("/{policy_id}/archive", response_model=HRPolicyOut)
def archive_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a published policy."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    policy.status = HRPolicyStatus.ARCHIVED
    policy.archived_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)

    log_audit(
        db, user=current_user, action="hr_policy_archived",
        entity="hr_policy", entity_id=policy.id,
        result=AuditResult.SUCCESS, request=request,
    )
    return policy


# ===========================================================================
# 3. Policy Acknowledgement
# ===========================================================================

@router.post("/{policy_id}/acknowledge", response_model=PolicyAcknowledgementOut, status_code=201)
def acknowledge_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Employee electronically acknowledges a published policy.
    Identity is strictly server-derived via current_user.person_id.
    """
    if not current_user.person_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only employees with valid personnel record can acknowledge policies")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    if policy.status != HRPolicyStatus.PUBLISHED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only published policies can be acknowledged")

    # Check applicability
    eng = db.query(Engagement).filter(
        Engagement.person_id == current_user.person_id,
        Engagement.status == "active"
    ).first()
    if eng:
        emp_type_str = str(eng.engagement_type.value if hasattr(eng.engagement_type, 'value') else eng.engagement_type)
        if policy.department_id and policy.department_id != eng.department:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This policy is not applicable to your department")
        if policy.employment_type and policy.employment_type != emp_type_str:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This policy is not applicable to your employment type")

    # Check if already acknowledged
    existing = db.query(PolicyAcknowledgementRecord).filter(
        PolicyAcknowledgementRecord.policy_id == policy.id,
        PolicyAcknowledgementRecord.person_id == current_user.person_id,
    ).first()

    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Policy version already acknowledged")

    ack = PolicyAcknowledgementRecord(
        policy_id=policy.id,
        policy_version=policy.version,
        person_id=current_user.person_id,
        user_id=current_user.id,
        acknowledged_at=datetime.utcnow(),
        ip_address=request.client.host if request.client else None,
        status="acknowledged",
    )
    db.add(ack)
    db.commit()
    db.refresh(ack)

    log_audit(
        db, user=current_user, action="hr_policy_acknowledged",
        entity="hr_policy", entity_id=policy.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"version": policy.version, "person_id": current_user.person_id}
    )

    person = db.query(Person).filter(Person.id == current_user.person_id).first()

    return PolicyAcknowledgementOut(
        id=ack.id,
        policy_id=ack.policy_id,
        policy_title=policy.title,
        policy_version=ack.policy_version,
        person_id=ack.person_id,
        person_name=person.full_name if person else None,
        acknowledged_at=ack.acknowledged_at,
        ip_address=ack.ip_address,
        status=ack.status,
    )


@router.get("/{policy_id}/acknowledgements", response_model=List[PolicyAcknowledgementOut])
def list_policy_acknowledgements(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """HR Admin tracks employee acknowledgements for a policy."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view acknowledgements")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    acks = db.query(PolicyAcknowledgementRecord).filter(
        PolicyAcknowledgementRecord.policy_id == policy.id
    ).order_by(PolicyAcknowledgementRecord.acknowledged_at.desc()).all()

    results = []
    for a in acks:
        p = db.query(Person).filter(Person.id == a.person_id).first()
        results.append(
            PolicyAcknowledgementOut(
                id=a.id,
                policy_id=a.policy_id,
                policy_title=policy.title,
                policy_version=a.policy_version,
                person_id=a.person_id,
                person_name=p.full_name if p else None,
                acknowledged_at=a.acknowledged_at,
                ip_address=a.ip_address,
                status=a.status,
            )
        )
    return results


@router.get("/{policy_id}/compliance-status", response_model=PolicyComplianceStatusOut)
def get_policy_compliance_status(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compliance reporting metrics for a policy version."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "hr_policy:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    policy = db.query(HRPolicy).filter(HRPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    total_active_employees = db.query(Engagement).filter(Engagement.status == "active").count()
    acks_count = db.query(PolicyAcknowledgementRecord).filter(
        PolicyAcknowledgementRecord.policy_id == policy.id
    ).count()

    rate = round((acks_count / total_active_employees * 100) if total_active_employees > 0 else 0.0, 1)

    return PolicyComplianceStatusOut(
        policy_id=policy.id,
        policy_title=policy.title,
        policy_code=policy.policy_code,
        version=policy.version,
        total_eligible_employees=total_active_employees,
        acknowledged_count=acks_count,
        compliance_rate_pct=rate,
    )
