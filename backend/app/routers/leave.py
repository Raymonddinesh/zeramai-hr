from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit, require_permission
from app.models import AuditResult, LeaveRequest, LeaveStatus, LeaveType, User

router = APIRouter(prefix="/api/leave", tags=["leave"])


class LeaveCreate(BaseModel):
    person_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    days: float
    reason: Optional[str] = None


class LeaveReview(BaseModel):
    status: LeaveStatus
    review_note: Optional[str] = None


class LeaveOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    days: float
    reason: Optional[str]
    status: LeaveStatus


@router.post("", response_model=LeaveOut, status_code=201)
def create_leave(
    payload: LeaveCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if has_permission(current_user, "leave:create", db):
        pass  # HR/Admin can create for anyone
    elif (has_permission(current_user, "leave:create_own", db)
          and payload.person_id == current_user.person_id):
        pass  # Employee can create for themselves
    else:
        log_audit(db, user=current_user, action="denied:leave:create", entity="leave",
                  entity_id=None, result=AuditResult.DENIED, request=request)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    req = LeaveRequest(
        person_id=payload.person_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=Decimal(str(payload.days)),
        reason=payload.reason,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    log_audit(db, user=current_user, action="leave_created", entity="leave",
              entity_id=req.id, result=AuditResult.SUCCESS, request=request)
    return req


@router.get("", response_model=list[LeaveOut])
def list_leave(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if has_permission(current_user, "leave:view", db):
        q = db.query(LeaveRequest)
        if person_id:
            q = q.filter(LeaveRequest.person_id == person_id)
    elif has_permission(current_user, "leave:view_own", db):
        q = db.query(LeaveRequest).filter(LeaveRequest.person_id == current_user.person_id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return q.order_by(LeaveRequest.created_at.desc()).all()


@router.post("/{leave_id}/review", response_model=LeaveOut)
def review_leave(
    leave_id: str,
    payload: LeaveReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:approve")),
):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave request not found")
    req.status = payload.status
    req.reviewed_by_id = current_user.id
    req.review_note = payload.review_note
    db.commit()
    db.refresh(req)
    log_audit(db, user=current_user, action=f"leave_{payload.status.value}", entity="leave",
              entity_id=leave_id, result=AuditResult.SUCCESS, request=request)
    return req
