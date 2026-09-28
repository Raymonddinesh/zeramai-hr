"""
routers/benefits.py - Module 7: Benefits Management Router.

Endpoints:
- GET  /api/v3/benefits/plans
- POST /api/v3/benefits/plans
- GET  /api/v3/benefits/enrollments
- POST /api/v3/benefits/enroll
- POST /api/v3/benefits/enrollments/{id}/terminate
- GET  /api/v3/benefits/my
"""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import (
    AuditResult,
    User,
    UserRole,
    Person,
)
from app.models_compensation import (
    BenefitPlan,
    BenefitEnrollment,
    EnrollmentStatus,
    BenefitType,
)
from app.schemas_compensation import (
    BenefitPlanCreate,
    BenefitPlanOut,
    BenefitEnrollmentCreate,
    BenefitEnrollmentOut,
)

router = APIRouter(prefix="/api/v3/benefits", tags=["benefits"])


def is_hr_or_super(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


# ===========================================================================
# 1. Benefit Plans
# ===========================================================================

@router.get("/plans", response_model=List[BenefitPlanOut])
def list_benefit_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available active benefit plans."""
    plans = db.query(BenefitPlan).filter(BenefitPlan.is_active == True).all()
    return [
        BenefitPlanOut(
            id=p.id,
            name=p.name,
            benefit_type=p.benefit_type,
            provider=p.provider,
            description=p.description,
            employer_contribution=float(p.employer_contribution),
            employee_deduction=float(p.employee_deduction),
            coverage_details=p.coverage_details,
            eligibility_criteria=p.eligibility_criteria,
            is_active=p.is_active,
            created_at=p.created_at,
        ) for p in plans
    ]


@router.post("/plans", response_model=BenefitPlanOut, status_code=201)
def create_benefit_plan(
    payload: BenefitPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new corporate benefit plan (HR Admin)."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create benefit plan")

    plan = BenefitPlan(
        name=payload.name,
        benefit_type=payload.benefit_type,
        provider=payload.provider,
        description=payload.description,
        employer_contribution=payload.employer_contribution,
        employee_deduction=payload.employee_deduction,
        coverage_details=payload.coverage_details,
        eligibility_criteria=payload.eligibility_criteria,
        is_active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    log_audit(
        db, user=current_user, action="benefit_plan_created",
        entity="benefit_plan", entity_id=plan.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"name": plan.name, "type": plan.benefit_type}
    )

    return BenefitPlanOut(
        id=plan.id,
        name=plan.name,
        benefit_type=plan.benefit_type,
        provider=plan.provider,
        description=plan.description,
        employer_contribution=float(plan.employer_contribution),
        employee_deduction=float(plan.employee_deduction),
        coverage_details=plan.coverage_details,
        eligibility_criteria=plan.eligibility_criteria,
        is_active=plan.is_active,
        created_at=plan.created_at,
    )


# ===========================================================================
# 2. Benefit Enrollments
# ===========================================================================

@router.get("/enrollments", response_model=List[BenefitEnrollmentOut])
def list_enrollments(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List employee benefit enrollments (HR Admin view)."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view enrollments")

    query = db.query(BenefitEnrollment)
    if person_id:
        query = query.filter(BenefitEnrollment.person_id == person_id)

    enrollments = query.order_by(BenefitEnrollment.created_at.desc()).all()
    results = []
    for be in enrollments:
        p = db.query(Person).filter(Person.id == be.person_id).first()
        plan = db.query(BenefitPlan).filter(BenefitPlan.id == be.benefit_plan_id).first()
        results.append(
            BenefitEnrollmentOut(
                id=be.id,
                person_id=be.person_id,
                person_name=p.full_name if p else None,
                benefit_plan_id=be.benefit_plan_id,
                plan_name=plan.name if plan else None,
                benefit_type=plan.benefit_type if plan else None,
                provider=plan.provider if plan else None,
                coverage_tier=be.coverage_tier,
                status=be.status,
                employee_contribution=float(be.employee_contribution),
                employer_contribution=float(be.employer_contribution),
                effective_date=be.effective_date,
                end_date=be.end_date,
                notes=be.notes,
                created_at=be.created_at,
            )
        )
    return results


@router.post("/enroll", response_model=BenefitEnrollmentOut, status_code=201)
def enroll_employee_in_benefit(
    payload: BenefitEnrollmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enroll an employee into a benefit plan."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to enroll employees in benefits")

    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target employee not found")

    plan = db.query(BenefitPlan).filter(BenefitPlan.id == payload.benefit_plan_id).first()
    if not plan or not plan.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active benefit plan not found")

    # Prevent duplicate active enrollment in same plan
    existing = db.query(BenefitEnrollment).filter(
        BenefitEnrollment.person_id == payload.person_id,
        BenefitEnrollment.benefit_plan_id == payload.benefit_plan_id,
        BenefitEnrollment.status == EnrollmentStatus.ENROLLED,
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Employee is already actively enrolled in this plan")

    emp_contrib = payload.employee_contribution if payload.employee_contribution is not None else float(plan.employee_deduction)
    empr_contrib = payload.employer_contribution if payload.employer_contribution is not None else float(plan.employer_contribution)

    enrollment = BenefitEnrollment(
        person_id=payload.person_id,
        benefit_plan_id=payload.benefit_plan_id,
        coverage_tier=payload.coverage_tier,
        status=EnrollmentStatus.ENROLLED,
        employee_contribution=emp_contrib,
        employer_contribution=empr_contrib,
        effective_date=payload.effective_date,
        enrolled_by_id=current_user.id,
        notes=payload.notes,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    log_audit(
        db, user=current_user, action="benefit_enrollment_created",
        entity="benefit_enrollment", entity_id=enrollment.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"person_id": payload.person_id, "plan_id": payload.benefit_plan_id}
    )

    return BenefitEnrollmentOut(
        id=enrollment.id,
        person_id=enrollment.person_id,
        person_name=person.full_name,
        benefit_plan_id=enrollment.benefit_plan_id,
        plan_name=plan.name,
        benefit_type=plan.benefit_type,
        provider=plan.provider,
        coverage_tier=enrollment.coverage_tier,
        status=enrollment.status,
        employee_contribution=float(enrollment.employee_contribution),
        employer_contribution=float(enrollment.employer_contribution),
        effective_date=enrollment.effective_date,
        end_date=enrollment.end_date,
        notes=enrollment.notes,
        created_at=enrollment.created_at,
    )


@router.post("/enrollments/{enrollment_id}/terminate", response_model=BenefitEnrollmentOut)
def terminate_benefit_enrollment(
    enrollment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Terminate an employee's benefit enrollment."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "compensation:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to terminate benefit enrollment")

    enrollment = db.query(BenefitEnrollment).filter(BenefitEnrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrollment not found")

    enrollment.status = EnrollmentStatus.TERMINATED
    enrollment.end_date = date.today()
    db.commit()
    db.refresh(enrollment)

    log_audit(
        db, user=current_user, action="benefit_enrollment_terminated",
        entity="benefit_enrollment", entity_id=enrollment.id,
        result=AuditResult.SUCCESS, request=request,
    )

    p = db.query(Person).filter(Person.id == enrollment.person_id).first()
    plan = db.query(BenefitPlan).filter(BenefitPlan.id == enrollment.benefit_plan_id).first()

    return BenefitEnrollmentOut(
        id=enrollment.id,
        person_id=enrollment.person_id,
        person_name=p.full_name if p else None,
        benefit_plan_id=enrollment.benefit_plan_id,
        plan_name=plan.name if plan else None,
        benefit_type=plan.benefit_type if plan else None,
        provider=plan.provider if plan else None,
        coverage_tier=enrollment.coverage_tier,
        status=enrollment.status,
        employee_contribution=float(enrollment.employee_contribution),
        employer_contribution=float(enrollment.employer_contribution),
        effective_date=enrollment.effective_date,
        end_date=enrollment.end_date,
        notes=enrollment.notes,
        created_at=enrollment.created_at,
    )


@router.get("/my", response_model=List[BenefitEnrollmentOut])
def get_my_benefit_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Employee self-service: view own active & historical benefit enrollments."""
    if not current_user.person_id:
        return []

    enrollments = db.query(BenefitEnrollment).filter(
        BenefitEnrollment.person_id == current_user.person_id
    ).order_by(BenefitEnrollment.effective_date.desc()).all()

    results = []
    for be in enrollments:
        plan = db.query(BenefitPlan).filter(BenefitPlan.id == be.benefit_plan_id).first()
        results.append(
            BenefitEnrollmentOut(
                id=be.id,
                person_id=be.person_id,
                person_name=None,
                benefit_plan_id=be.benefit_plan_id,
                plan_name=plan.name if plan else None,
                benefit_type=plan.benefit_type if plan else None,
                provider=plan.provider if plan else None,
                coverage_tier=be.coverage_tier,
                status=be.status,
                employee_contribution=float(be.employee_contribution),
                employer_contribution=float(be.employer_contribution),
                effective_date=be.effective_date,
                end_date=be.end_date,
                notes=be.notes,
                created_at=be.created_at,
            )
        )
    return results
