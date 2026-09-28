"""
routers/compensation.py - Module 7: Compensation Management Router.

Endpoints:
- GET  /api/v3/compensation/overview
- GET  /api/v3/compensation/structures
- GET  /api/v3/compensation/structures/{person_id}
- GET  /api/v3/compensation/revisions
- GET  /api/v3/compensation/revisions/{id}
- POST /api/v3/compensation/revisions
- POST /api/v3/compensation/recommendations
- POST /api/v3/compensation/revisions/{id}/submit
- POST /api/v3/compensation/revisions/{id}/approve
- POST /api/v3/compensation/revisions/{id}/reject
- GET  /api/v3/compensation/{person_id}/history
- GET  /api/v3/compensation/bonuses
- POST /api/v3/compensation/bonuses
- POST /api/v3/compensation/bonuses/{id}/review
- GET  /api/v3/compensation/me
"""
import uuid
from datetime import datetime, date, timedelta
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
from app.models_v6 import SalaryStructure, ComponentType
from app.models_v3 import EmploymentHistory, HistoryChangeType
from app.models_compensation import (
    CompensationRevision,
    BonusIncentive,
    BenefitEnrollment,
    RevisionStatus,
    RevisionReason,
    BonusStatus,
    BonusType,
)
from app.schemas_compensation import (
    CompensationRevisionCreate,
    CompensationRevisionRecommend,
    CompensationRevisionReview,
    CompensationRevisionOut,
    CompensationStructureOut,
    CompensationHistoryItemOut,
    BonusIncentiveCreate,
    BonusIncentiveReview,
    BonusIncentiveOut,
    CompensationOverviewOut,
    EmployeeCompensationSummaryOut,
)

router = APIRouter(prefix="/api/v3/compensation", tags=["compensation"])


def is_hr_or_super(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


# ===========================================================================
# 1. Overview & Structures
# ===========================================================================

@router.get("/overview", response_model=CompensationOverviewOut)
def get_compensation_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Overview statistics for compensation management."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db) or has_permission(current_user, "stipends:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view compensation overview")

    active_structures = db.query(SalaryStructure).filter(SalaryStructure.is_active == True).all()
    pending_revisions = db.query(CompensationRevision).filter(
        CompensationRevision.status.in_([RevisionStatus.SUBMITTED, RevisionStatus.UNDER_REVIEW])
    ).count()
    approved_revisions = db.query(CompensationRevision).filter(
        CompensationRevision.status.in_([RevisionStatus.APPROVED, RevisionStatus.EFFECTIVE])
    ).count()
    pending_bonuses = db.query(BonusIncentive).filter(
        BonusIncentive.status == BonusStatus.SUBMITTED
    ).count()
    total_benefits = db.query(BenefitEnrollment).filter(
        BenefitEnrollment.status == "enrolled"
    ).count()

    total_payroll = sum(float(s.ctc_annual or 0) for s in active_structures)

    return CompensationOverviewOut(
        active_structures_count=len(active_structures),
        pending_revisions_count=pending_revisions,
        approved_revisions_count=approved_revisions,
        pending_bonuses_count=pending_bonuses,
        total_annual_payroll_commitment=round(total_payroll, 2),
        total_benefits_enrolled=total_benefits,
    )


@router.get("/structures", response_model=List[CompensationStructureOut])
def list_salary_structures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active salary structures across the organization."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view salary structures")

    structures = db.query(SalaryStructure).filter(SalaryStructure.is_active == True).all()
    results = []
    for s in structures:
        p = db.query(Person).filter(Person.id == s.person_id).first()
        results.append(
            CompensationStructureOut(
                id=s.id,
                person_id=s.person_id,
                person_name=p.full_name if p else None,
                name=s.name,
                effective_from=s.effective_from,
                effective_to=s.effective_to,
                ctc_annual=float(s.ctc_annual),
                ctc_monthly=float(s.ctc_monthly),
                components_json=s.components_json or [],
                currency=s.currency or "INR",
                is_active=s.is_active,
            )
        )
    return results


@router.get("/structures/{person_id}", response_model=CompensationStructureOut)
def get_salary_structure_for_person(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active salary structure for a specific employee."""
    # Check authorization: HR/Admin or self
    is_self = bool(current_user.person_id and str(current_user.person_id) == str(person_id))
    has_perm = is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)

    if not is_self and not has_perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to employee compensation")

    structure = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == person_id,
        SalaryStructure.is_active == True,
    ).first()

    if not structure:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active salary structure found for employee")

    p = db.query(Person).filter(Person.id == structure.person_id).first()
    return CompensationStructureOut(
        id=structure.id,
        person_id=structure.person_id,
        person_name=p.full_name if p else None,
        name=structure.name,
        effective_from=structure.effective_from,
        effective_to=structure.effective_to,
        ctc_annual=float(structure.ctc_annual),
        ctc_monthly=float(structure.ctc_monthly),
        components_json=structure.components_json or [],
        currency=structure.currency or "INR",
        is_active=structure.is_active,
    )


# ===========================================================================
# 2. Compensation Revisions Workflow
# ===========================================================================

@router.get("/revisions", response_model=List[CompensationRevisionOut])
def list_compensation_revisions(
    status_filter: Optional[str] = None,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List compensation revisions according to role & scope."""
    query = db.query(CompensationRevision)

    if is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db):
        # Full view
        pass
    elif has_permission(current_user, "compensation:recommend", db):
        # Manager scope: only revisions for direct reports or recommended by self
        direct_person_ids = [
            e.person_id for e in db.query(Engagement.person_id).filter(
                Engagement.reporting_manager_id == current_user.id
            ).all()
        ]
        query = query.filter(
            (CompensationRevision.person_id.in_(direct_person_ids)) |
            (CompensationRevision.recommended_by_id == current_user.id)
        )
    else:
        # Regular employee: only own approved/effective revisions
        if not current_user.person_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to revisions")
        query = query.filter(
            CompensationRevision.person_id == current_user.person_id,
            CompensationRevision.status.in_([RevisionStatus.APPROVED, RevisionStatus.EFFECTIVE])
        )

    if status_filter:
        query = query.filter(CompensationRevision.status == status_filter)
    if person_id:
        # Employee cannot filter for other employees
        if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)):
            if str(current_user.person_id) != str(person_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot query revisions for another employee")
        query = query.filter(CompensationRevision.person_id == person_id)

    revisions = query.order_by(CompensationRevision.created_at.desc()).all()
    results = []
    is_hr = is_hr_or_super(current_user) or has_permission(current_user, "compensation:manage", db)

    for r in revisions:
        p = db.query(Person).filter(Person.id == r.person_id).first()
        results.append(
            CompensationRevisionOut(
                id=r.id,
                person_id=r.person_id,
                person_name=p.full_name if p else None,
                previous_salary_structure_id=r.previous_salary_structure_id,
                previous_ctc_annual=float(r.previous_ctc_annual) if r.previous_ctc_annual else None,
                new_ctc_annual=float(r.new_ctc_annual),
                new_ctc_monthly=float(r.new_ctc_monthly),
                currency=r.currency,
                components_json=r.components_json or [],
                effective_date=r.effective_date,
                reason=r.reason,
                business_justification=r.business_justification,
                hr_notes=r.hr_notes if is_hr else None,  # Mask confidential notes for non-HR
                rejection_reason=r.rejection_reason,
                status=r.status,
                created_by_id=r.created_by_id,
                recommended_by_id=r.recommended_by_id,
                approved_by_id=r.approved_by_id,
                approved_at=r.approved_at,
                resulting_salary_structure_id=r.resulting_salary_structure_id,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return results


@router.get("/revisions/{revision_id}", response_model=CompensationRevisionOut)
def get_compensation_revision(
    revision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of a single compensation revision with field-level masking."""
    revision = db.query(CompensationRevision).filter(CompensationRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compensation revision not found")

    is_hr = is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)
    is_recommender = bool(revision.recommended_by_id and revision.recommended_by_id == current_user.id)
    is_owner = bool(current_user.person_id and str(current_user.person_id) == str(revision.person_id))

    # Check manager reporting relationship
    is_direct_manager = False
    if not is_hr and not is_owner and not is_recommender:
        eng = db.query(Engagement).filter(
            Engagement.person_id == revision.person_id,
            Engagement.reporting_manager_id == current_user.id
        ).first()
        is_direct_manager = eng is not None

    if not (is_hr or is_recommender or is_direct_manager or (is_owner and revision.status in [RevisionStatus.APPROVED, RevisionStatus.EFFECTIVE])):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to this compensation revision")

    p = db.query(Person).filter(Person.id == revision.person_id).first()
    return CompensationRevisionOut(
        id=revision.id,
        person_id=revision.person_id,
        person_name=p.full_name if p else None,
        previous_salary_structure_id=revision.previous_salary_structure_id,
        previous_ctc_annual=float(revision.previous_ctc_annual) if revision.previous_ctc_annual else None,
        new_ctc_annual=float(revision.new_ctc_annual),
        new_ctc_monthly=float(revision.new_ctc_monthly),
        currency=revision.currency,
        components_json=revision.components_json or [],
        effective_date=revision.effective_date,
        reason=revision.reason,
        business_justification=revision.business_justification,
        hr_notes=revision.hr_notes if is_hr else None,  # Confidential field masked
        rejection_reason=revision.rejection_reason,
        status=revision.status,
        created_by_id=revision.created_by_id,
        recommended_by_id=revision.recommended_by_id,
        approved_by_id=revision.approved_by_id,
        approved_at=revision.approved_at,
        resulting_salary_structure_id=revision.resulting_salary_structure_id,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


@router.post("/revisions", response_model=CompensationRevisionOut, status_code=201)
def create_compensation_revision(
    payload: CompensationRevisionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """HR/Admin creates a new compensation revision."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create compensation revision")

    # Verify target employee exists
    target_person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not target_person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target employee does not exist")

    # Fetch active structure to anchor previous values
    active_ss = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == payload.person_id,
        SalaryStructure.is_active == True,
    ).first()

    monthly = payload.new_ctc_monthly or round(payload.new_ctc_annual / 12.0, 2)

    revision = CompensationRevision(
        person_id=payload.person_id,
        previous_salary_structure_id=active_ss.id if active_ss else None,
        previous_ctc_annual=float(active_ss.ctc_annual) if active_ss else None,
        new_ctc_annual=payload.new_ctc_annual,
        new_ctc_monthly=monthly,
        currency=payload.currency,
        components_json=payload.components_json,
        effective_date=payload.effective_date,
        reason=payload.reason,
        business_justification=payload.business_justification,
        hr_notes=payload.hr_notes,
        status=RevisionStatus.SUBMITTED,
        created_by_id=current_user.id,
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)

    log_audit(
        db,
        user=current_user,
        action="compensation_revision_created",
        entity="compensation_revision",
        entity_id=revision.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"person_id": payload.person_id, "new_ctc": payload.new_ctc_annual},
    )

    return CompensationRevisionOut(
        id=revision.id,
        person_id=revision.person_id,
        person_name=target_person.full_name,
        previous_salary_structure_id=revision.previous_salary_structure_id,
        previous_ctc_annual=float(revision.previous_ctc_annual) if revision.previous_ctc_annual else None,
        new_ctc_annual=float(revision.new_ctc_annual),
        new_ctc_monthly=float(revision.new_ctc_monthly),
        currency=revision.currency,
        components_json=revision.components_json or [],
        effective_date=revision.effective_date,
        reason=revision.reason,
        business_justification=revision.business_justification,
        hr_notes=revision.hr_notes,
        rejection_reason=None,
        status=revision.status,
        created_by_id=revision.created_by_id,
        recommended_by_id=None,
        approved_by_id=None,
        approved_at=None,
        resulting_salary_structure_id=None,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


@router.post("/recommendations", response_model=CompensationRevisionOut, status_code=201)
def recommend_compensation_revision(
    payload: CompensationRevisionRecommend,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manager recommends a compensation revision for a direct report."""
    # Allow HIRING_MANAGER role to recommend compensation revisions
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:recommend", db) or current_user.role == UserRole.HIRING_MANAGER):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to recommend compensation changes")

    # Manager cannot recommend for themselves!
    if current_user.person_id and str(current_user.person_id) == str(payload.person_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot recommend compensation changes for yourself")

    # Verify that target employee reports directly to this manager (unless super admin)
    if not is_hr_or_super(current_user):
        eng = db.query(Engagement).filter(
            Engagement.person_id == payload.person_id,
            Engagement.reporting_manager_id == current_user.id
        ).first()
        if not eng:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You can only recommend compensation changes for direct reporting team members",
            )

    target_person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not target_person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target employee does not exist")

    active_ss = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == payload.person_id,
        SalaryStructure.is_active == True,
    ).first()

    monthly = round(payload.proposed_ctc_annual / 12.0, 2)
    components = payload.components_json or [
        {"code": "BASIC", "name": "Basic Salary", "amount": round(monthly * 0.5, 2), "type": "earning"},
        {"code": "HRA", "name": "House Rent Allowance", "amount": round(monthly * 0.3, 2), "type": "earning"},
        {"code": "SPECIAL", "name": "Special Allowance", "amount": round(monthly * 0.2, 2), "type": "earning"},
    ]

    revision = CompensationRevision(
        person_id=payload.person_id,
        previous_salary_structure_id=active_ss.id if active_ss else None,
        previous_ctc_annual=float(active_ss.ctc_annual) if active_ss else None,
        new_ctc_annual=payload.proposed_ctc_annual,
        new_ctc_monthly=monthly,
        currency="INR",
        components_json=components,
        effective_date=payload.effective_date,
        reason=payload.reason,
        business_justification=payload.business_justification,
        status=RevisionStatus.SUBMITTED,
        created_by_id=current_user.id,
        recommended_by_id=current_user.id,
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)

    log_audit(
        db,
        user=current_user,
        action="compensation_recommendation_submitted",
        entity="compensation_revision",
        entity_id=revision.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"person_id": payload.person_id, "proposed_ctc": payload.proposed_ctc_annual},
    )

    return CompensationRevisionOut(
        id=revision.id,
        person_id=revision.person_id,
        person_name=target_person.full_name,
        previous_salary_structure_id=revision.previous_salary_structure_id,
        previous_ctc_annual=float(revision.previous_ctc_annual) if revision.previous_ctc_annual else None,
        new_ctc_annual=float(revision.new_ctc_annual),
        new_ctc_monthly=float(revision.new_ctc_monthly),
        currency=revision.currency,
        components_json=revision.components_json or [],
        effective_date=revision.effective_date,
        reason=revision.reason,
        business_justification=revision.business_justification,
        hr_notes=None,
        rejection_reason=None,
        status=revision.status,
        created_by_id=revision.created_by_id,
        recommended_by_id=revision.recommended_by_id,
        approved_by_id=None,
        approved_at=None,
        resulting_salary_structure_id=None,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


@router.post("/revisions/{revision_id}/submit")
def submit_compensation_revision(
    revision_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a draft revision for review."""
    revision = db.query(CompensationRevision).filter(CompensationRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Revision not found")

    if not (is_hr_or_super(current_user) or revision.created_by_id == current_user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized to submit this revision")

    if revision.status != RevisionStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Revision cannot be submitted from status {revision.status}")

    revision.status = RevisionStatus.SUBMITTED
    db.commit()

    log_audit(
        db, user=current_user, action="compensation_revision_submitted",
        entity="compensation_revision", entity_id=revision.id,
        result=AuditResult.SUCCESS, request=request
    )
    return {"message": "Revision submitted successfully", "status": revision.status}


@router.post("/revisions/{revision_id}/approve", response_model=CompensationRevisionOut)
def approve_compensation_revision(
    revision_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Approve a compensation revision.
    Enforces:
    - User must have compensation:approve permission.
    - User CANNOT self-approve (cannot approve if they created or recommended the revision).
    - Transitions old structure to inactive with effective_to.
    - Inserts new active SalaryStructure and adds EmploymentHistory record.
    """
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:approve", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to approve compensation revisions")

    revision = db.query(CompensationRevision).filter(CompensationRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compensation revision not found")

    if revision.status in (RevisionStatus.APPROVED, RevisionStatus.EFFECTIVE):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Revision is already approved")

    # Anti-Self-Approval Check
    if current_user.person_id and str(revision.person_id) == str(current_user.person_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-approval prohibited: you cannot approve your own compensation revision")
    if revision.recommended_by_id and revision.recommended_by_id == current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-approval prohibited: you cannot approve a compensation change that you recommended")

    today = date.today()
    is_effective_now = revision.effective_date <= today
    new_status = RevisionStatus.EFFECTIVE if is_effective_now else RevisionStatus.APPROVED

    # 1. Update/deactivate prior active structure
    active_structures = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == revision.person_id,
        SalaryStructure.is_active == True,
    ).all()

    for s in active_structures:
        s.is_active = False
        s.effective_to = revision.effective_date - timedelta(days=1)

    # 2. Create new active SalaryStructure
    new_ss = SalaryStructure(
        person_id=revision.person_id,
        name=f"Revision-{revision.reason}-{revision.effective_date}",
        effective_from=revision.effective_date,
        ctc_annual=revision.new_ctc_annual,
        ctc_monthly=revision.new_ctc_monthly,
        components_json=revision.components_json,
        currency=revision.currency,
        is_active=True,
    )
    db.add(new_ss)
    db.flush()

    # 3. Create EmploymentHistory record
    from app.models_v3 import Tenant
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(tenant)
        db.flush()

    hist = EmploymentHistory(
        tenant_id=revision.tenant_id or tenant.id,
        person_id=revision.person_id,
        effective_date=revision.effective_date,
        change_type=HistoryChangeType.COMPENSATION_REVISION,
        salary_amount=revision.new_ctc_annual,
        salary_currency=revision.currency,
        notes=f"Approved revision ({revision.reason}): {revision.business_justification or ''}",
    )
    db.add(hist)


    # 4. Update revision record
    revision.status = new_status
    revision.approved_by_id = current_user.id
    revision.approved_at = datetime.utcnow()
    revision.resulting_salary_structure_id = new_ss.id
    db.commit()
    db.refresh(revision)

    log_audit(
        db,
        user=current_user,
        action="compensation_revision_approved",
        entity="compensation_revision",
        entity_id=revision.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"person_id": revision.person_id, "resulting_ss_id": new_ss.id, "status": new_status},
    )

    p = db.query(Person).filter(Person.id == revision.person_id).first()
    return CompensationRevisionOut(
        id=revision.id,
        person_id=revision.person_id,
        person_name=p.full_name if p else None,
        previous_salary_structure_id=revision.previous_salary_structure_id,
        previous_ctc_annual=float(revision.previous_ctc_annual) if revision.previous_ctc_annual else None,
        new_ctc_annual=float(revision.new_ctc_annual),
        new_ctc_monthly=float(revision.new_ctc_monthly),
        currency=revision.currency,
        components_json=revision.components_json or [],
        effective_date=revision.effective_date,
        reason=revision.reason,
        business_justification=revision.business_justification,
        hr_notes=revision.hr_notes,
        rejection_reason=None,
        status=revision.status,
        created_by_id=revision.created_by_id,
        recommended_by_id=revision.recommended_by_id,
        approved_by_id=revision.approved_by_id,
        approved_at=revision.approved_at,
        resulting_salary_structure_id=revision.resulting_salary_structure_id,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


@router.post("/revisions/{revision_id}/reject", response_model=CompensationRevisionOut)
def reject_compensation_revision(
    revision_id: str,
    payload: CompensationRevisionReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a compensation revision."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:approve", db) or has_permission(current_user, "compensation:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to reject compensation revisions")

    revision = db.query(CompensationRevision).filter(CompensationRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compensation revision not found")

    revision.status = RevisionStatus.REJECTED
    revision.rejection_reason = payload.rejection_reason or "Rejected by compensation reviewer"
    if payload.hr_notes:
        revision.hr_notes = payload.hr_notes
    revision.approved_by_id = current_user.id
    revision.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(revision)

    log_audit(
        db,
        user=current_user,
        action="compensation_revision_rejected",
        entity="compensation_revision",
        entity_id=revision.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"person_id": revision.person_id, "reason": revision.rejection_reason},
    )

    p = db.query(Person).filter(Person.id == revision.person_id).first()
    return CompensationRevisionOut(
        id=revision.id,
        person_id=revision.person_id,
        person_name=p.full_name if p else None,
        previous_salary_structure_id=revision.previous_salary_structure_id,
        previous_ctc_annual=float(revision.previous_ctc_annual) if revision.previous_ctc_annual else None,
        new_ctc_annual=float(revision.new_ctc_annual),
        new_ctc_monthly=float(revision.new_ctc_monthly),
        currency=revision.currency,
        components_json=revision.components_json or [],
        effective_date=revision.effective_date,
        reason=revision.reason,
        business_justification=revision.business_justification,
        hr_notes=revision.hr_notes,
        rejection_reason=revision.rejection_reason,
        status=revision.status,
        created_by_id=revision.created_by_id,
        recommended_by_id=revision.recommended_by_id,
        approved_by_id=revision.approved_by_id,
        approved_at=revision.approved_at,
        resulting_salary_structure_id=revision.resulting_salary_structure_id,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


@router.get("/{person_id}/history", response_model=List[CompensationHistoryItemOut])
def get_compensation_history(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full chronological compensation history for an employee."""
    is_self = bool(current_user.person_id and str(current_user.person_id) == str(person_id))
    has_perm = is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)

    if not is_self and not has_perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to employee compensation history")

    structures = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == person_id
    ).order_by(SalaryStructure.effective_from.desc()).all()

    items = []
    for s in structures:
        items.append(
            CompensationHistoryItemOut(
                id=s.id,
                type="salary_structure",
                effective_date=s.effective_from,
                ctc_annual=float(s.ctc_annual),
                ctc_monthly=float(s.ctc_monthly),
                currency=s.currency or "INR",
                reason=s.name,
                status="active" if s.is_active else "superseded",
                approved_at=s.created_at,
            )
        )
    return items


# ===========================================================================
# 3. Bonus & Incentive Records
# ===========================================================================

@router.get("/bonuses", response_model=List[BonusIncentiveOut])
def list_bonuses(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List bonus and incentive records."""
    query = db.query(BonusIncentive)

    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)):
        # Regular employee: can only view own approved bonuses
        if not current_user.person_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized")
        query = query.filter(
            BonusIncentive.person_id == current_user.person_id,
            BonusIncentive.status == BonusStatus.APPROVED
        )
    elif person_id:
        query = query.filter(BonusIncentive.person_id == person_id)

    bonuses = query.order_by(BonusIncentive.created_at.desc()).all()
    results = []
    for b in bonuses:
        p = db.query(Person).filter(Person.id == b.person_id).first()
        results.append(
            BonusIncentiveOut(
                id=b.id,
                person_id=b.person_id,
                person_name=p.full_name if p else None,
                bonus_type=b.bonus_type,
                amount=float(b.amount),
                currency=b.currency,
                pay_period=b.pay_period,
                effective_date=b.effective_date,
                reason=b.reason,
                status=b.status,
                payroll_status=b.payroll_status,
                created_by_id=b.created_by_id,
                approved_by_id=b.approved_by_id,
                approved_at=b.approved_at,
                rejection_reason=b.rejection_reason,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )
    return results


@router.post("/bonuses", response_model=BonusIncentiveOut, status_code=201)
def create_bonus(
    payload: BonusIncentiveCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new bonus / incentive award."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create bonus")

    target_person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not target_person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target employee not found")

    bonus = BonusIncentive(
        person_id=payload.person_id,
        bonus_type=payload.bonus_type,
        amount=payload.amount,
        currency=payload.currency,
        pay_period=payload.pay_period,
        effective_date=payload.effective_date,
        reason=payload.reason,
        status=BonusStatus.SUBMITTED,
        payroll_status="pending",
        created_by_id=current_user.id,
    )
    db.add(bonus)
    db.commit()
    db.refresh(bonus)

    log_audit(
        db, user=current_user, action="bonus_incentive_created",
        entity="bonus_incentive", entity_id=bonus.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"person_id": payload.person_id, "amount": payload.amount}
    )

    return BonusIncentiveOut(
        id=bonus.id,
        person_id=bonus.person_id,
        person_name=target_person.full_name,
        bonus_type=bonus.bonus_type,
        amount=float(bonus.amount),
        currency=bonus.currency,
        pay_period=bonus.pay_period,
        effective_date=bonus.effective_date,
        reason=bonus.reason,
        status=bonus.status,
        payroll_status=bonus.payroll_status,
        created_by_id=bonus.created_by_id,
        approved_by_id=None,
        approved_at=None,
        rejection_reason=None,
        created_at=bonus.created_at,
        updated_at=bonus.updated_at,
    )


@router.post("/bonuses/{bonus_id}/review", response_model=BonusIncentiveOut)
def review_bonus(
    bonus_id: str,
    payload: BonusIncentiveReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a bonus award."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:approve", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to review bonus")

    bonus = db.query(BonusIncentive).filter(BonusIncentive.id == bonus_id).first()
    if not bonus:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bonus record not found")

    if payload.action == "approve":
        # Check self-approval: cannot approve a bonus for yourself or your own manager recommendation
        if current_user.person_id and str(bonus.person_id) == str(current_user.person_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot approve a bonus for yourself")
        if bonus.created_by_id == current_user.id and current_user.role == UserRole.HIRING_MANAGER:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Managers cannot approve their own bonus recommendation")
        bonus.status = BonusStatus.APPROVED
        bonus.approved_by_id = current_user.id
        bonus.approved_at = datetime.utcnow()

    else:
        bonus.status = BonusStatus.REJECTED
        bonus.rejection_reason = payload.rejection_reason or "Rejected by compensation reviewer"

    db.commit()
    db.refresh(bonus)

    log_audit(
        db, user=current_user, action=f"bonus_{payload.action}d",
        entity="bonus_incentive", entity_id=bonus.id,
        result=AuditResult.SUCCESS, request=request,
    )

    p = db.query(Person).filter(Person.id == bonus.person_id).first()
    return BonusIncentiveOut(
        id=bonus.id,
        person_id=bonus.person_id,
        person_name=p.full_name if p else None,
        bonus_type=bonus.bonus_type,
        amount=float(bonus.amount),
        currency=bonus.currency,
        pay_period=bonus.pay_period,
        effective_date=bonus.effective_date,
        reason=bonus.reason,
        status=bonus.status,
        payroll_status=bonus.payroll_status,
        created_by_id=bonus.created_by_id,
        approved_by_id=bonus.approved_by_id,
        approved_at=bonus.approved_at,
        rejection_reason=bonus.rejection_reason,
        created_at=bonus.created_at,
        updated_at=bonus.updated_at,
    )


# ===========================================================================
# 4. Employee Self-Service Endpoint (/me)
# ===========================================================================

@router.get("/me", response_model=EmployeeCompensationSummaryOut)
def get_my_compensation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve current employee's own approved compensation breakdown & benefits."""
    if not current_user.person_id:
        return EmployeeCompensationSummaryOut(has_active_structure=False)

    person_id = current_user.person_id
    active_ss = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == person_id,
        SalaryStructure.is_active == True,
    ).first()

    # Revisions (only approved or effective; internal hr_notes masked)
    approved_revisions = db.query(CompensationRevision).filter(
        CompensationRevision.person_id == person_id,
        CompensationRevision.status.in_([RevisionStatus.APPROVED, RevisionStatus.EFFECTIVE])
    ).order_by(CompensationRevision.effective_date.desc()).all()

    rev_outs = [
        CompensationRevisionOut(
            id=r.id,
            person_id=r.person_id,
            person_name=None,
            previous_salary_structure_id=r.previous_salary_structure_id,
            previous_ctc_annual=float(r.previous_ctc_annual) if r.previous_ctc_annual else None,
            new_ctc_annual=float(r.new_ctc_annual),
            new_ctc_monthly=float(r.new_ctc_monthly),
            currency=r.currency,
            components_json=r.components_json or [],
            effective_date=r.effective_date,
            reason=r.reason,
            business_justification=r.business_justification,
            hr_notes=None,  # Stripped for employee
            rejection_reason=None,
            status=r.status,
            created_by_id=r.created_by_id,
            recommended_by_id=r.recommended_by_id,
            approved_by_id=r.approved_by_id,
            approved_at=r.approved_at,
            resulting_salary_structure_id=r.resulting_salary_structure_id,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ) for r in approved_revisions
    ]

    # Benefits
    enrollments = db.query(BenefitEnrollment).filter(
        BenefitEnrollment.person_id == person_id,
        BenefitEnrollment.status == "enrolled"
    ).all()

    from app.schemas_compensation import BenefitEnrollmentOut
    ben_outs = []
    for be in enrollments:
        plan = db.query(BenefitEnrollment).filter(BenefitEnrollment.id == be.id).first().benefit_plan
        ben_outs.append(
            BenefitEnrollmentOut(
                id=be.id,
                person_id=be.person_id,
                person_name=None,
                benefit_plan_id=be.benefit_plan_id,
                plan_name=plan.name if plan else None,
                benefit_type=plan.benefit_type if plan else None,
                provider=plan.provider if plan else None,
                coverage_tier=be.coverage_tier,
                status=be.status,
                employee_contribution=float(be.employee_contribution),
                employer_contribution=float(be.employer_contribution),
                effective_date=be.effective_date,
                end_date=be.end_date,
                notes=be.notes,
                created_at=be.created_at,
            )
        )

    if not active_ss:
        return EmployeeCompensationSummaryOut(
            has_active_structure=False,
            recent_revisions=rev_outs,
            enrolled_benefits=ben_outs,
        )

    return EmployeeCompensationSummaryOut(
        has_active_structure=True,
        ctc_annual=float(active_ss.ctc_annual),
        ctc_monthly=float(active_ss.ctc_monthly),
        currency=active_ss.currency or "INR",
        effective_from=active_ss.effective_from,
        components=active_ss.components_json or [],
        recent_revisions=rev_outs,
        enrolled_benefits=ben_outs,
    )
