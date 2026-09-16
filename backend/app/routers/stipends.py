from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit, require_permission
from app.models import AuditResult, Stipend, StipendStatus, User

router = APIRouter(prefix="/api/stipends", tags=["stipends"])


class StipendCreate(BaseModel):
    person_id: str
    engagement_id: Optional[str] = None
    month: str  # "2026-09"
    amount: float
    currency: str = "INR"
    notes: Optional[str] = None


class StipendOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    engagement_id: Optional[str]
    month: str
    amount: float
    currency: str
    status: StipendStatus
    payment_date: Optional[date]
    notes: Optional[str]


@router.post("", response_model=StipendOut, status_code=201)
def create_stipend(
    payload: StipendCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:create")),
):
    s = Stipend(
        person_id=payload.person_id,
        engagement_id=payload.engagement_id,
        month=payload.month,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency,
        notes=payload.notes,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    log_audit(db, user=current_user, action="stipend_created", entity="stipend",
              entity_id=s.id, result=AuditResult.SUCCESS, request=request)
    return s


@router.get("", response_model=list[StipendOut])
def list_stipends(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if has_permission(current_user, "stipends:view", db):
        q = db.query(Stipend)
        if person_id:
            q = q.filter(Stipend.person_id == person_id)
    elif has_permission(current_user, "stipends:view_own", db):
        q = db.query(Stipend).filter(Stipend.person_id == current_user.person_id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return q.order_by(Stipend.month.desc()).all()


@router.post("/{stipend_id}/approve", response_model=StipendOut)
def approve_stipend(
    stipend_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    s = db.query(Stipend).filter(Stipend.id == stipend_id).first()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stipend not found")
    if s.status != StipendStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Stipend already {s.status.value}")
    s.status = StipendStatus.APPROVED
    s.approved_by_id = current_user.id
    db.commit()
    db.refresh(s)
    log_audit(db, user=current_user, action="stipend_approved", entity="stipend",
              entity_id=stipend_id, result=AuditResult.SUCCESS, request=request)
    return s


@router.post("/{stipend_id}/mark-paid", response_model=StipendOut)
def mark_paid(
    stipend_id: str,
    payment_date: date,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:approve")),
):
    s = db.query(Stipend).filter(Stipend.id == stipend_id).first()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stipend not found")
    s.status = StipendStatus.PAID
    s.payment_date = payment_date
    db.commit()
    db.refresh(s)
    log_audit(db, user=current_user, action="stipend_paid", entity="stipend",
              entity_id=stipend_id, result=AuditResult.SUCCESS, request=request)
    return s
