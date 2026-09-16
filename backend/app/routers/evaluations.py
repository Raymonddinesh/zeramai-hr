from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit, require_permission
from app.models import AuditResult, Evaluation, EvaluationStatus, User

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


class EvaluationCreate(BaseModel):
    person_id: str
    engagement_id: Optional[str] = None
    period_start: date
    period_end: date
    overall_rating: Optional[float] = None
    comments: Optional[str] = None


class EvaluationSubmit(BaseModel):
    overall_rating: Optional[float] = None
    comments: Optional[str] = None


class EvaluationOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    person_id: str
    engagement_id: Optional[str]
    evaluator_id: str
    period_start: date
    period_end: date
    overall_rating: Optional[float]
    comments: Optional[str]
    status: EvaluationStatus
    submitted_at: Optional[datetime]


@router.post("", response_model=EvaluationOut, status_code=201)
def create_evaluation(
    payload: EvaluationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:create")),
):
    ev = Evaluation(
        person_id=payload.person_id,
        engagement_id=payload.engagement_id,
        evaluator_id=current_user.id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        overall_rating=payload.overall_rating,
        comments=payload.comments,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    log_audit(db, user=current_user, action="evaluation_created", entity="evaluation",
              entity_id=ev.id, result=AuditResult.SUCCESS, request=request)
    return ev


@router.get("", response_model=list[EvaluationOut])
def list_evaluations(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if has_permission(current_user, "evaluations:view", db):
        q = db.query(Evaluation)
        if person_id:
            q = q.filter(Evaluation.person_id == person_id)
    elif has_permission(current_user, "evaluations:view_own", db):
        q = db.query(Evaluation).filter(Evaluation.person_id == current_user.person_id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return q.order_by(Evaluation.created_at.desc()).all()


@router.post("/{evaluation_id}/submit", response_model=EvaluationOut)
def submit_evaluation(
    evaluation_id: str,
    payload: EvaluationSubmit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evaluations:submit")),
):
    ev = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if not ev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found")
    if ev.evaluator_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Can only submit your own evaluations")
    if ev.status != EvaluationStatus.DRAFT:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evaluation already submitted")
    if payload.overall_rating is not None:
        ev.overall_rating = payload.overall_rating
    if payload.comments is not None:
        ev.comments = payload.comments
    ev.status = EvaluationStatus.SUBMITTED
    ev.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(ev)
    log_audit(db, user=current_user, action="evaluation_submitted", entity="evaluation",
              entity_id=evaluation_id, result=AuditResult.SUCCESS, request=request)
    return ev
