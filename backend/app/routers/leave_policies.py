"""Phase 5 – Leave policy engine: policies, balances, comp-off."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v6 import (
    LeavePolicy, LeaveBalance, CompOffRequest,
    AccrualFrequency, CompOffStatus,
)

router = APIRouter(prefix="/api/leave-policies", tags=["leave-policies"])


class LeavePolicyCreate(BaseModel):
    name: str
    leave_type: str
    annual_quota: float
    accrual_frequency: AccrualFrequency = AccrualFrequency.MONTHLY
    max_carry_forward: float = 0
    max_consecutive_days: int = 30
    requires_attachment: bool = False
    attachment_after_days: int = 2

class LeavePolicyOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    name: str
    leave_type: str
    annual_quota: float
    accrual_frequency: AccrualFrequency
    max_carry_forward: float
    is_active: bool

class BalanceCreate(BaseModel):
    person_id: str
    leave_policy_id: str
    year: int
    total_entitled: float
    carry_forward: float = 0

class BalanceOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    leave_policy_id: str
    year: int
    total_entitled: float
    used: float
    carry_forward: float
    remaining: float

class CompOffCreate(BaseModel):
    person_id: str
    worked_date: date
    reason: Optional[str] = None
    comp_off_date: Optional[date] = None

class CompOffOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    worked_date: date
    status: CompOffStatus


# ── Leave Policies ──────────────────────────────────────────────────────

@router.post("", response_model=LeavePolicyOut, status_code=201)
def create_leave_policy(
    payload: LeavePolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:approve")),
):
    pol = LeavePolicy(**payload.model_dump())
    db.add(pol)
    db.commit()
    db.refresh(pol)
    log_audit(db, user=current_user, action="leave_policy_created", entity="leave_policy",
              entity_id=pol.id, result=AuditResult.SUCCESS, request=request)
    return pol


@router.get("", response_model=list[LeavePolicyOut])
def list_leave_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:view")),
):
    return db.query(LeavePolicy).filter(LeavePolicy.is_active == True).all()


# ── Leave Balances ──────────────────────────────────────────────────────

@router.post("/balances", response_model=BalanceOut, status_code=201)
def create_balance(
    payload: BalanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:approve")),
):
    remaining = payload.total_entitled + payload.carry_forward
    bal = LeaveBalance(
        person_id=payload.person_id,
        leave_policy_id=payload.leave_policy_id,
        year=payload.year,
        total_entitled=payload.total_entitled,
        carry_forward=payload.carry_forward,
        remaining=remaining,
    )
    db.add(bal)
    db.commit()
    db.refresh(bal)
    return bal


@router.get("/balances/{person_id}", response_model=list[BalanceOut])
def get_balances(
    person_id: str,
    year: int = 2026,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:view")),
):
    return db.query(LeaveBalance).filter(
        LeaveBalance.person_id == person_id,
        LeaveBalance.year == year,
    ).all()


# ── Comp-Off ────────────────────────────────────────────────────────────

@router.post("/comp-off", response_model=CompOffOut, status_code=201)
def request_comp_off(
    payload: CompOffCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:create")),
):
    co = CompOffRequest(**payload.model_dump())
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


@router.patch("/comp-off/{comp_off_id}/review")
def review_comp_off(
    comp_off_id: str,
    approve: bool,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave:approve")),
):
    co = db.query(CompOffRequest).filter(CompOffRequest.id == comp_off_id).first()
    if not co:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comp-off not found")
    co.status = CompOffStatus.APPROVED if approve else CompOffStatus.REJECTED
    co.approved_by_id = current_user.id
    db.commit()
    return {"id": comp_off_id, "status": co.status}
