"""Phase 12 - Compliance, Policy Center & Grievance Resolution."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
import uuid

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v9 import (
    CompliancePolicy, PolicyAcknowledgment, GrievanceCase,
    PolicyCategory, GrievanceCategory, GrievanceStatus,
)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


# ── Schemas ──────────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    title: str
    version: str = "1.0"
    category: PolicyCategory = PolicyCategory.CODE_OF_CONDUCT
    content: str
    effective_date: date
    is_mandatory: bool = True


class PolicyOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    title: str
    version: str
    category: PolicyCategory
    effective_date: date
    is_mandatory: bool
    is_active: bool


class GrievanceCreate(BaseModel):
    is_anonymous: bool = False
    category: GrievanceCategory
    title: str
    description: str


class GrievanceOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    ticket_number: str
    is_anonymous: bool
    category: GrievanceCategory
    title: str
    status: GrievanceStatus
    created_at: datetime


# ── Policies ─────────────────────────────────────────────────────────────

@router.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(
    payload: PolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    policy = CompliancePolicy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    log_audit(db, user=current_user, action="compliance_policy_created", entity="compliance_policy",
              entity_id=policy.id, result=AuditResult.SUCCESS, request=request)
    return policy


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(CompliancePolicy).filter(CompliancePolicy.is_active == True).all()


@router.post("/policies/{policy_id}/acknowledge")
def acknowledge_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")

    existing = db.query(PolicyAcknowledgment).filter(
        PolicyAcknowledgment.policy_id == policy_id,
        PolicyAcknowledgment.user_id == current_user.id,
    ).first()
    if existing:
        return {"message": "Already acknowledged", "acknowledged_at": existing.acknowledged_at.isoformat()}

    ack = PolicyAcknowledgment(
        policy_id=policy_id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(ack)
    db.commit()
    log_audit(db, user=current_user, action="policy_acknowledged", entity="compliance_policy",
              entity_id=policy_id, result=AuditResult.SUCCESS, request=request)
    return {"message": "Policy acknowledged successfully", "acknowledged_at": ack.acknowledged_at.isoformat()}


@router.get("/policies/{policy_id}/acknowledgments-status")
def get_policy_acknowledgment_status(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:view")),
):
    acks_count = db.query(PolicyAcknowledgment).filter(PolicyAcknowledgment.policy_id == policy_id).count()
    total_users = db.query(User).filter(User.is_active == True).count()
    return {
        "policy_id": policy_id,
        "acknowledged_count": acks_count,
        "total_active_users": total_users,
        "compliance_rate_pct": round((acks_count / total_users * 100) if total_users > 0 else 0, 1),
    }


# ── Grievance & Whistleblower ───────────────────────────────────────────

@router.post("/grievances", response_model=GrievanceOut, status_code=201)
def submit_grievance(
    payload: GrievanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket_num = f"GRV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    complainant = None if payload.is_anonymous else current_user.id

    case = GrievanceCase(
        ticket_number=ticket_num,
        is_anonymous=payload.is_anonymous,
        complainant_user_id=complainant,
        category=payload.category,
        title=payload.title,
        description=payload.description,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    log_audit(db, user=current_user, action="grievance_submitted", entity="grievance_case",
              entity_id=case.id, result=AuditResult.SUCCESS, request=request,
              metadata={"anonymous": payload.is_anonymous})
    return case


@router.get("/grievances", response_model=list[GrievanceOut])
def list_grievances(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:view")),
):
    return db.query(GrievanceCase).order_by(GrievanceCase.created_at.desc()).all()


@router.patch("/grievances/{case_id}/resolve")
def resolve_grievance(
    case_id: str,
    resolution_notes: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:view")),
):
    case = db.query(GrievanceCase).filter(GrievanceCase.id == case_id).first()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grievance case not found")

    case.status = GrievanceStatus.RESOLVED
    case.resolution_notes = resolution_notes
    case.resolved_at = datetime.utcnow()
    case.assigned_investigator_id = current_user.id
    db.commit()
    log_audit(db, user=current_user, action="grievance_resolved", entity="grievance_case",
              entity_id=case.id, result=AuditResult.SUCCESS, request=request)
    return {"id": case.id, "status": case.status, "resolved_at": case.resolved_at.isoformat()}
