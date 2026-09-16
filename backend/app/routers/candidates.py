from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import log_audit, require_permission
from app.models import (
    AuditResult,
    Candidate,
    CandidateStatus,
    Engagement,
    EngagementStatus,
    EngagementType,
    Person,
    User,
)
from app.schemas import (
    CandidateCreate,
    CandidateOut,
    ConvertToTraineeRequest,
    EngagementOut,
)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])

CREATE_CAND = require_permission("candidates:create")
VIEW_CAND = require_permission("candidates:view")
SELECT_CAND = require_permission("candidates:select")
CONVERT_CAND = require_permission("candidates:convert_to_trainee")


@router.post("", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(CREATE_CAND)
):
    person = Person(full_name=payload.full_name, email=payload.email, phone=payload.phone)
    db.add(person)
    db.flush()  # get person.id without a separate round trip

    candidate = Candidate(
        person_id=person.id,
        applied_position=payload.applied_position,
        department=payload.department,
        recruiter=payload.recruiter,
        highest_qualification=payload.highest_qualification,
        college_university=payload.college_university,
        linkedin_url=payload.linkedin_url,
        github_url=payload.github_url,
        application_date=date.today(),
        status=CandidateStatus.APPLIED,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    log_audit(db, user=current_user, action="candidate_created", entity="candidate",
              entity_id=candidate.id, result=AuditResult.SUCCESS, request=request)
    return candidate


@router.get("", response_model=list[CandidateOut])
def list_candidates(db: Session = Depends(get_db), current_user: User = Depends(VIEW_CAND)):
    return db.query(Candidate).order_by(Candidate.created_at.desc()).all()


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: str, db: Session = Depends(get_db), current_user: User = Depends(VIEW_CAND)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return candidate


@router.post("/{candidate_id}/select", response_model=CandidateOut)
def mark_selected(
    candidate_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(SELECT_CAND),
):
    """Minimal status transition so the demo flow (APPLIED -> SELECTED ->
    convert-to-trainee) works end to end. Full interview pipeline (screening,
    interview score, rejection reasons) is a later slice."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    candidate.status = CandidateStatus.SELECTED
    db.commit()
    db.refresh(candidate)
    log_audit(db, user=current_user, action="candidate_selected", entity="candidate",
              entity_id=candidate_id, result=AuditResult.SUCCESS, request=request)
    return candidate


@router.post("/{candidate_id}/convert-to-trainee", response_model=EngagementOut)
def convert_to_trainee(
    candidate_id: str,
    payload: ConvertToTraineeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(CONVERT_CAND),
):
    """
    Implements PRD Stage 1->2: candidate must be SELECTED before conversion.
    Creates an Engagement row; the Candidate row is NOT deleted or mutated
    beyond its status — full history is preserved per the PRD's explicit
    "do not destroy historical records" requirement.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")

    if candidate.status != CandidateStatus.SELECTED:
        log_audit(db, user=current_user, action="convert_to_trainee", entity="candidate",
                  entity_id=candidate_id, result=AuditResult.DENIED, request=request,
                  metadata={"reason": f"candidate status is {candidate.status.value}, must be SELECTED"})
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Candidate must be SELECTED before conversion (current status: {candidate.status.value})",
        )

    end_date = payload.start_date + relativedelta(months=payload.duration_months)

    engagement = Engagement(
        person_id=candidate.person_id,
        converted_from_candidate_id=candidate.id,
        engagement_type=EngagementType.ENGINEERING_TRAINEE,
        designation=payload.designation,
        department=payload.department,
        reporting_manager_id=payload.reporting_manager_id,
        work_location=payload.work_location,
        start_date=payload.start_date,
        end_date=end_date,
        stipend_amount=payload.monthly_stipend,
        stipend_currency="INR",
        status=EngagementStatus.PENDING_JOINING,
    )
    db.add(engagement)

    candidate.status = CandidateStatus.CONVERTED_TO_TRAINEE
    db.commit()
    db.refresh(engagement)

    log_audit(db, user=current_user, action="convert_to_trainee", entity="engagement",
              entity_id=engagement.id, result=AuditResult.SUCCESS, request=request,
              metadata={"candidate_id": candidate_id, "end_date": str(end_date)})

    return engagement
