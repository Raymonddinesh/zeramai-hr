"""Phase 8 – Learning Management System (LMS)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
import uuid

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v7 import (
    Course, Enrollment, TrainingCertificate,
    CourseStatus, EnrollmentStatus,
)

router = APIRouter(prefix="/api/lms", tags=["lms"])


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    duration_hours: Optional[float] = None
    is_mandatory: bool = False
    instructor_name: Optional[str] = None
    max_enrollment: Optional[int] = None
    modules_json: Optional[list[dict]] = None

class CourseOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    title: str
    category: Optional[str]
    duration_hours: Optional[float]
    is_mandatory: bool
    status: CourseStatus

class EnrollCreate(BaseModel):
    course_id: str
    person_id: str

class EnrollOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    course_id: str
    person_id: str
    status: EnrollmentStatus
    progress_pct: float
    score: Optional[float]

class CertOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    person_id: str
    certificate_number: str
    issued_date: date


# ── Courses ─────────────────────────────────────────────────────────────

@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    course = Course(**payload.model_dump())
    course.status = CourseStatus.PUBLISHED
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard:view")),
):
    return db.query(Course).filter(Course.status != CourseStatus.ARCHIVED).all()


# ── Enrollments ─────────────────────────────────────────────────────────

@router.post("/enroll", response_model=EnrollOut, status_code=201)
def enroll_person(
    payload: EnrollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

    # Check max enrollment
    if course.max_enrollment:
        count = db.query(Enrollment).filter(Enrollment.course_id == payload.course_id).count()
        if count >= course.max_enrollment:
            raise HTTPException(status.HTTP_409_CONFLICT, "Course is full")

    enroll = Enrollment(course_id=payload.course_id, person_id=payload.person_id)
    db.add(enroll)
    db.commit()
    db.refresh(enroll)
    return enroll

@router.get("/enrollments/{person_id}", response_model=list[EnrollOut])
def get_enrollments(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard:view")),
):
    return db.query(Enrollment).filter(Enrollment.person_id == person_id).all()


@router.patch("/enrollments/{enrollment_id}/progress")
def update_progress(
    enrollment_id: str,
    progress_pct: float,
    score: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard:view")),
):
    enroll = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enroll:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrollment not found")
    enroll.progress_pct = progress_pct
    if score is not None:
        enroll.score = score
    enroll.status = EnrollmentStatus.IN_PROGRESS

    # Auto-complete at 100%
    if progress_pct >= 100:
        enroll.status = EnrollmentStatus.COMPLETED
        enroll.completed_at = datetime.utcnow()
        # Auto-generate certificate
        cert = TrainingCertificate(
            enrollment_id=enrollment_id,
            person_id=enroll.person_id,
            certificate_number=f"CERT-{uuid.uuid4().hex[:8].upper()}",
            issued_date=date.today(),
        )
        db.add(cert)

    db.commit()
    return {"id": enrollment_id, "progress_pct": progress_pct, "status": enroll.status}


@router.get("/certificates/{person_id}", response_model=list[CertOut])
def get_certificates(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard:view")),
):
    return db.query(TrainingCertificate).filter(TrainingCertificate.person_id == person_id).all()
