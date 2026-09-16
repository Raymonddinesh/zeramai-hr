"""Phase 4 – Shift templates, roster assignments, shift swap requests."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v5 import (
    ShiftTemplate, ShiftAssignment, ShiftSwapRequest,
    ShiftType, SwapStatus,
)

router = APIRouter(prefix="/api/shifts", tags=["shifts"])


# ── Schemas ──────────────────────────────────────────────────────────────

class ShiftTemplateCreate(BaseModel):
    name: str
    shift_type: ShiftType = ShiftType.GENERAL
    start_time: str  # "09:00"
    end_time: str    # "17:00"
    break_duration_minutes: int = 60
    is_night_shift: bool = False
    min_rest_hours: int = 12
    color_code: str = "#3B82F6"

class ShiftTemplateOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    name: str
    shift_type: ShiftType
    start_time: str
    end_time: str
    break_duration_minutes: int
    is_night_shift: bool
    min_rest_hours: int
    color_code: str
    is_active: bool

class ShiftAssignCreate(BaseModel):
    person_id: str
    shift_template_id: str
    date: date
    notes: Optional[str] = None

class ShiftAssignOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    shift_template_id: str
    date: date
    is_overtime: bool
    overtime_hours: Optional[float]

class SwapRequestCreate(BaseModel):
    requester_assignment_id: str
    target_assignment_id: str
    reason: Optional[str] = None

class SwapRequestOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    requester_assignment_id: str
    target_assignment_id: str
    requester_id: str
    status: SwapStatus


# ── Shift Templates ─────────────────────────────────────────────────────

@router.post("/templates", response_model=ShiftTemplateOut, status_code=201)
def create_shift_template(
    payload: ShiftTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance:create")),
):
    tmpl = ShiftTemplate(
        name=payload.name,
        shift_type=payload.shift_type,
        start_time=payload.start_time,
        end_time=payload.end_time,
        break_duration_minutes=payload.break_duration_minutes,
        is_night_shift=payload.is_night_shift,
        min_rest_hours=payload.min_rest_hours,
        color_code=payload.color_code,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    log_audit(db, user=current_user, action="shift_template_created", entity="shift_template",
              entity_id=tmpl.id, result=AuditResult.SUCCESS, request=request)
    return tmpl


@router.get("/templates", response_model=list[ShiftTemplateOut])
def list_shift_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance:view")),
):
    return db.query(ShiftTemplate).filter(ShiftTemplate.is_active == True).all()


# ── Shift Assignments (Roster) ──────────────────────────────────────────

@router.post("/assign", response_model=ShiftAssignOut, status_code=201)
def assign_shift(
    payload: ShiftAssignCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance:create")),
):
    tmpl = db.query(ShiftTemplate).filter(ShiftTemplate.id == payload.shift_template_id).first()
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shift template not found")

    # Conflict detection: check if person already has a shift on that date
    existing = db.query(ShiftAssignment).filter(
        ShiftAssignment.person_id == payload.person_id,
        ShiftAssignment.date == payload.date,
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Person already assigned to shift on {payload.date}")

    assignment = ShiftAssignment(
        person_id=payload.person_id,
        shift_template_id=payload.shift_template_id,
        date=payload.date,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    log_audit(db, user=current_user, action="shift_assigned", entity="shift_assignment",
              entity_id=assignment.id, result=AuditResult.SUCCESS, request=request)
    return assignment


@router.get("/roster")
def get_roster(
    start_date: date,
    end_date: date,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance:view")),
):
    q = db.query(ShiftAssignment).filter(
        ShiftAssignment.date >= start_date,
        ShiftAssignment.date <= end_date,
    )
    if person_id:
        q = q.filter(ShiftAssignment.person_id == person_id)
    assignments = q.order_by(ShiftAssignment.date).all()
    return [
        {
            "id": a.id,
            "person_id": a.person_id,
            "shift_template_id": a.shift_template_id,
            "date": str(a.date),
            "is_overtime": a.is_overtime,
            "overtime_hours": a.overtime_hours,
        }
        for a in assignments
    ]


# ── Shift Swap Requests ─────────────────────────────────────────────────

@router.post("/swap", response_model=SwapRequestOut, status_code=201)
def request_shift_swap(
    payload: SwapRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance:create_own")),
):
    req_assign = db.query(ShiftAssignment).filter(ShiftAssignment.id == payload.requester_assignment_id).first()
    tgt_assign = db.query(ShiftAssignment).filter(ShiftAssignment.id == payload.target_assignment_id).first()
    if not req_assign or not tgt_assign:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shift assignment not found")

    swap = ShiftSwapRequest(
        requester_assignment_id=payload.requester_assignment_id,
        target_assignment_id=payload.target_assignment_id,
        requester_id=current_user.id,
        reason=payload.reason,
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return swap


@router.patch("/swap/{swap_id}/review")
def review_shift_swap(
    swap_id: str,
    approve: bool,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance:update")),
):
    swap = db.query(ShiftSwapRequest).filter(ShiftSwapRequest.id == swap_id).first()
    if not swap:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Swap request not found")

    if approve:
        swap.status = SwapStatus.APPROVED
        # Actually swap the person_ids on the two assignments
        a1 = db.query(ShiftAssignment).filter(ShiftAssignment.id == swap.requester_assignment_id).first()
        a2 = db.query(ShiftAssignment).filter(ShiftAssignment.id == swap.target_assignment_id).first()
        if a1 and a2:
            a1.person_id, a2.person_id = a2.person_id, a1.person_id
    else:
        swap.status = SwapStatus.REJECTED

    swap.reviewed_by_id = current_user.id
    db.commit()
    log_audit(db, user=current_user, action="shift_swap_reviewed", entity="shift_swap",
              entity_id=swap_id, result=AuditResult.SUCCESS, request=request,
              metadata={"approved": approve})
    return {"id": swap_id, "status": swap.status}
