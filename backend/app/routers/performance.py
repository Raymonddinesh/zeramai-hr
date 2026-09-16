"""Phase 7 – Performance & OKR management."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v7 import (
    ReviewCycle, OKRObjective, OKRKeyResult, PerformanceReview,
    ReviewCycleStatus, ObjectiveStatus, KRStatus, ReviewRating,
)

router = APIRouter(prefix="/api/performance", tags=["performance"])


class CycleCreate(BaseModel):
    name: str
    cycle_type: str = "annual"
    start_date: date
    end_date: date

class CycleOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    name: str
    cycle_type: str
    start_date: date
    end_date: date
    status: ReviewCycleStatus

class ObjectiveCreate(BaseModel):
    person_id: str
    review_cycle_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    weight: float = 1.0
    parent_objective_id: Optional[str] = None

class ObjectiveOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    title: str
    status: ObjectiveStatus
    progress_pct: float
    weight: float

class KRCreate(BaseModel):
    title: str
    target_value: float
    unit: str = "percent"

class KROut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    objective_id: str
    title: str
    target_value: float
    current_value: float
    status: KRStatus

class ReviewCreate(BaseModel):
    person_id: str
    review_cycle_id: str
    reviewer_id: str
    self_rating: Optional[ReviewRating] = None
    manager_rating: Optional[ReviewRating] = None
    self_comments: Optional[str] = None
    manager_comments: Optional[str] = None


# ── Review Cycles ───────────────────────────────────────────────────────

@router.post("/cycles", response_model=CycleOut, status_code=201)
def create_cycle(
    payload: CycleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:create")),
):
    cycle = ReviewCycle(**payload.model_dump())
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle

@router.get("/cycles", response_model=list[CycleOut])
def list_cycles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:view")),
):
    return db.query(ReviewCycle).order_by(ReviewCycle.start_date.desc()).all()


# ── OKR Objectives ─────────────────────────────────────────────────────

@router.post("/objectives", response_model=ObjectiveOut, status_code=201)
def create_objective(
    payload: ObjectiveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:create")),
):
    obj = OKRObjective(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/objectives/{person_id}", response_model=list[ObjectiveOut])
def list_objectives(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:view")),
):
    return db.query(OKRObjective).filter(OKRObjective.person_id == person_id).all()


# ── Key Results ─────────────────────────────────────────────────────────

@router.post("/objectives/{objective_id}/kr", response_model=KROut, status_code=201)
def add_key_result(
    objective_id: str,
    payload: KRCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:create")),
):
    obj = db.query(OKRObjective).filter(OKRObjective.id == objective_id).first()
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Objective not found")
    kr = OKRKeyResult(objective_id=objective_id, **payload.model_dump())
    db.add(kr)
    db.commit()
    db.refresh(kr)
    return kr

@router.patch("/kr/{kr_id}/progress")
def update_kr_progress(
    kr_id: str,
    current_value: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:update")),
):
    kr = db.query(OKRKeyResult).filter(OKRKeyResult.id == kr_id).first()
    if not kr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Key result not found")
    kr.current_value = current_value
    kr.status = KRStatus.COMPLETED if current_value >= kr.target_value else KRStatus.IN_PROGRESS

    # Auto-recalculate objective progress
    obj = db.query(OKRObjective).filter(OKRObjective.id == kr.objective_id).first()
    if obj:
        all_krs = db.query(OKRKeyResult).filter(OKRKeyResult.objective_id == obj.id).all()
        if all_krs:
            avg_pct = sum(min(100, (k.current_value / k.target_value) * 100) for k in all_krs) / len(all_krs)
            obj.progress_pct = round(avg_pct, 1)
            if avg_pct >= 100:
                obj.status = ObjectiveStatus.COMPLETED

    db.commit()
    return {"id": kr_id, "current_value": current_value, "status": kr.status, "objective_progress": obj.progress_pct if obj else 0}


# ── Performance Reviews ────────────────────────────────────────────────

@router.post("/reviews", status_code=201)
def create_review(
    payload: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:create")),
):
    rev = PerformanceReview(**payload.model_dump())
    db.add(rev)
    db.commit()
    db.refresh(rev)
    log_audit(db, user=current_user, action="performance_review_created", entity="performance_review",
              entity_id=rev.id, result=AuditResult.SUCCESS, request=request)
    return {"id": rev.id, "person_id": rev.person_id, "is_submitted": rev.is_submitted}

@router.patch("/reviews/{review_id}/submit")
def submit_review(
    review_id: str,
    final_rating: ReviewRating,
    manager_comments: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:submit")),
):
    rev = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not rev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    rev.final_rating = final_rating
    if manager_comments:
        rev.manager_comments = manager_comments
    rev.is_submitted = True
    db.commit()
    return {"id": review_id, "final_rating": final_rating, "is_submitted": True}
