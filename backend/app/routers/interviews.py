"""Phase 3 – Interview scheduling, scorecards, offer management."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v2 import CandidateApplication, ApplicationStage
from app.models_v5 import (
    InterviewSchedule, InterviewScorecard, OfferLetter,
    InterviewType, InterviewStatus, ScorecardVerdict, OfferStatus,
)

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

# ── Schemas ──────────────────────────────────────────────────────────────

class InterviewCreate(BaseModel):
    application_id: str
    interviewer_id: str
    interview_type: InterviewType
    scheduled_start: datetime
    scheduled_end: datetime
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    notes: Optional[str] = None

class InterviewOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    application_id: str
    interviewer_id: str
    interview_type: InterviewType
    scheduled_start: datetime
    scheduled_end: datetime
    status: InterviewStatus
    location: Optional[str]
    meeting_link: Optional[str]

class ScorecardCreate(BaseModel):
    evaluator_id: str
    technical_score: Optional[int] = None
    communication_score: Optional[int] = None
    culture_fit_score: Optional[int] = None
    verdict: ScorecardVerdict
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    notes: Optional[str] = None

class ScorecardOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    interview_id: str
    evaluator_id: str
    technical_score: Optional[int]
    communication_score: Optional[int]
    culture_fit_score: Optional[int]
    overall_score: Optional[float]
    verdict: ScorecardVerdict

# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("", response_model=InterviewOut, status_code=201)
def schedule_interview(
    payload: InterviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:update")),
):
    app_rec = db.query(CandidateApplication).filter(CandidateApplication.id == payload.application_id).first()
    if not app_rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    # Move stage to interview
    app_rec.stage = ApplicationStage.INTERVIEW
    interview = InterviewSchedule(
        application_id=payload.application_id,
        interviewer_id=payload.interviewer_id,
        interview_type=payload.interview_type,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        location=payload.location,
        meeting_link=payload.meeting_link,
        notes=payload.notes,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    log_audit(db, user=current_user, action="interview_scheduled", entity="interview",
              entity_id=interview.id, result=AuditResult.SUCCESS, request=request)
    return interview


@router.get("/{application_id}", response_model=list[InterviewOut])
def list_interviews(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:view")),
):
    return db.query(InterviewSchedule).filter(InterviewSchedule.application_id == application_id).all()


@router.patch("/{interview_id}/status")
def update_interview_status(
    interview_id: str,
    new_status: InterviewStatus,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:update")),
):
    interview = db.query(InterviewSchedule).filter(InterviewSchedule.id == interview_id).first()
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    interview.status = new_status
    db.commit()
    return {"id": interview_id, "status": new_status}


@router.post("/{interview_id}/scorecard", response_model=ScorecardOut, status_code=201)
def submit_scorecard(
    interview_id: str,
    payload: ScorecardCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:update")),
):
    interview = db.query(InterviewSchedule).filter(InterviewSchedule.id == interview_id).first()
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")

    scores = [s for s in [payload.technical_score, payload.communication_score, payload.culture_fit_score] if s is not None]
    overall = sum(scores) / len(scores) if scores else None

    sc = InterviewScorecard(
        interview_id=interview_id,
        evaluator_id=payload.evaluator_id,
        technical_score=payload.technical_score,
        communication_score=payload.communication_score,
        culture_fit_score=payload.culture_fit_score,
        overall_score=overall,
        verdict=payload.verdict,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        notes=payload.notes,
    )
    db.add(sc)
    # Auto-complete interview if scorecard submitted
    interview.status = InterviewStatus.COMPLETED
    db.commit()
    db.refresh(sc)
    log_audit(db, user=current_user, action="scorecard_submitted", entity="scorecard",
              entity_id=sc.id, result=AuditResult.SUCCESS, request=request)
    return sc
