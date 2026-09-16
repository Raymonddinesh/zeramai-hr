from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit, require_permission
from app.models import (
    AuditResult, Attendance, AttendanceStatus, User,
)

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

VIEW_ATT = require_permission("attendance:view")
VIEW_OWN = require_permission("attendance:view_own")
CREATE_ATT = require_permission("attendance:create")
CREATE_OWN = require_permission("attendance:create_own")


class AttendanceCreate(BaseModel):
    person_id: str
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    notes: Optional[str] = None


class AttendanceOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    date: date
    status: AttendanceStatus
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    notes: Optional[str]


@router.post("", response_model=AttendanceOut, status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # HR/Admin: attendance:create; Employee: attendance:create_own for own record
    if has_permission(current_user, "attendance:create", db):
        pass
    elif (has_permission(current_user, "attendance:create_own", db)
          and payload.person_id == current_user.person_id):
        pass
    else:
        log_audit(db, user=current_user, action="denied:attendance:create", entity="attendance",
                  entity_id=None, result=AuditResult.DENIED, request=request)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    rec = Attendance(
        person_id=payload.person_id,
        date=payload.date,
        status=payload.status,
        check_in=payload.check_in,
        check_out=payload.check_out,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    log_audit(db, user=current_user, action="attendance_created", entity="attendance",
              entity_id=rec.id, result=AuditResult.SUCCESS, request=request)
    return rec


@router.get("", response_model=list[AttendanceOut])
def list_attendance(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if has_permission(current_user, "attendance:view", db):
        q = db.query(Attendance)
        if person_id:
            q = q.filter(Attendance.person_id == person_id)
    elif has_permission(current_user, "attendance:view_own", db):
        q = db.query(Attendance).filter(Attendance.person_id == current_user.person_id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return q.order_by(Attendance.date.desc()).all()
