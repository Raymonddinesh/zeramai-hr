from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User, Candidate
from app.models_v2 import JobOpening, CandidateApplication, JobStatus, ApplicationStage
from app.services.ai_resume_matcher import match_candidate_to_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobOpeningCreate(BaseModel):
    title: str
    department: str
    location: str
    employment_type: str = "full_time"
    description: Optional[str] = None
    required_skills: list[str] = []
    min_experience_years: int = 0
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    currency: str = "USD"


class JobOpeningOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    title: str
    department: str
    location: str
    employment_type: str
    status: JobStatus
    required_skills: Optional[list[str]]
    min_experience_years: int


class ApplicationCreate(BaseModel):
    candidate_id: str
    resume_text: str = ""
    candidate_experience_years: int = 0
    cover_letter: Optional[str] = None


class ApplicationOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    job_id: str
    candidate_id: str
    stage: ApplicationStage
    ai_match_score: Optional[float]
    ai_match_reasons: Optional[list[str]]


@router.post("", response_model=JobOpeningOut, status_code=201)
def create_job_opening(
    payload: JobOpeningCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:create")),
):
    job = JobOpening(
        title=payload.title,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        description=payload.description,
        required_skills=payload.required_skills,
        min_experience_years=payload.min_experience_years,
        salary_range_min=payload.salary_range_min,
        salary_range_max=payload.salary_range_max,
        currency=payload.currency,
        created_by_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    log_audit(db, user=current_user, action="job_opening_created", entity="job_opening",
              entity_id=job.id, result=AuditResult.SUCCESS, request=request)
    return job


@router.get("", response_model=list[JobOpeningOut])
def list_job_openings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:view")),
):
    return db.query(JobOpening).order_by(JobOpening.created_at.desc()).all()


@router.post("/{job_id}/apply", response_model=ApplicationOut, status_code=201)
def apply_to_job(
    job_id: str,
    payload: ApplicationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:create")),
):
    job = db.query(JobOpening).filter(JobOpening.id == job_id).first()
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job opening not found")

    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")

    # Run AI Resume Match Scoring
    skills = job.required_skills or []
    min_exp = job.min_experience_years or 0
    match_result = match_candidate_to_job(
        resume_text=payload.resume_text,
        required_skills=skills,
        min_experience_years=min_exp,
        candidate_experience_years=payload.candidate_experience_years
    )

    app_rec = CandidateApplication(
        job_id=job_id,
        candidate_id=payload.candidate_id,
        stage=ApplicationStage.APPLIED,
        ai_match_score=match_result["score"],
        ai_match_reasons=match_result["reasons"],
        parsed_skills=match_result["matched_skills"],
        cover_letter=payload.cover_letter,
    )
    db.add(app_rec)
    db.commit()
    db.refresh(app_rec)

    log_audit(db, user=current_user, action="candidate_applied_ai_scored", entity="candidate_application",
              entity_id=app_rec.id, result=AuditResult.SUCCESS, request=request,
              metadata={"match_score": match_result["score"]})
    return app_rec
