"""
learning_service.py - Module 18: Learning, Skills & Career Development Service Layer
Zeramai Enterprise HRMS
"""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Person, User, Engagement
from app.models_workforce_planning import (
    Skill, SkillLevel, EmployeeSkill, SkillGapAnalysis, Position, PositionAssignment
)
from app.models_learning import (
    LearningCourse, LearningModule, CourseContent, TrainingProvider,
    LearningPath, LearningPathCourse, CourseSkillMapping,
    LearningEnrollment, LearningProgress, LearningAssessment,
    AssessmentQuestion, AssessmentAttempt, Certification,
    EmployeeCertification, TrainingRequirement, TrainingAssignment,
    LearningPlan, LearningPlanItem, DevelopmentPlan, DevelopmentGoal,
    CareerFramework, CareerLevel, CareerPath,
    CareerOpportunity, CareerApplication,
    MentoringProgram, MentoringRelationship,
    SkillDevelopmentAction, SkillEvidence,
    LearningEnrollmentStatus, CertificationVerificationStatus,
    MentoringStatus,
)


def validate_mentoring_relationship(
    db: Session,
    tenant_id: str,
    program_id: str,
    mentor_person_id: str,
    mentee_person_id: str,
):
    """
    Validates mentoring constraints:
    1. Mentor and mentee cannot be the same person (no self-mentoring).
    2. Both mentor and mentee must exist and belong to the same tenant.
    3. Mentoring program must belong to the tenant and be active.
    4. Prevent duplicate active relationships in the same program.
    """
    if mentor_person_id == mentee_person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-mentoring is not permitted. Mentor and mentee must be different persons."
        )

    prog = db.query(MentoringProgram).filter(
        MentoringProgram.id == program_id,
        MentoringProgram.tenant_id == tenant_id,
    ).first()
    if not prog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentoring program not found")

    mentor = db.query(Person).filter(Person.id == mentor_person_id).first()
    mentee = db.query(Person).filter(Person.id == mentee_person_id).first()
    if not mentor or not mentee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor or mentee person record not found")

    # Check duplicate active relationship in program
    existing = db.query(MentoringRelationship).filter(
        MentoringRelationship.tenant_id == tenant_id,
        MentoringRelationship.program_id == program_id,
        MentoringRelationship.mentor_person_id == mentor_person_id,
        MentoringRelationship.mentee_person_id == mentee_person_id,
        MentoringRelationship.status == MentoringStatus.ACTIVE.value,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active mentoring relationship already exists between these participants in this program."
        )


def evaluate_assessment_attempt(
    db: Session,
    tenant_id: str,
    assessment_id: str,
    person_id: str,
    enrollment_id: Optional[str],
    answers: Dict[str, str],
) -> AssessmentAttempt:
    """
    Evaluates assessment questions and computes final percentage score.
    Enforces attempt limits and updates enrollment progress if applicable.
    """
    assessment = db.query(LearningAssessment).filter(
        LearningAssessment.id == assessment_id,
        LearningAssessment.tenant_id == tenant_id,
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Count prior attempts
    prior_attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.tenant_id == tenant_id,
        AssessmentAttempt.assessment_id == assessment_id,
        AssessmentAttempt.person_id == person_id,
    ).count()

    if prior_attempts >= assessment.attempts_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum allowed attempts ({assessment.attempts_allowed}) exceeded."
        )

    questions = db.query(AssessmentQuestion).filter(
        AssessmentQuestion.assessment_id == assessment_id
    ).all()

    total_points = sum(q.points for q in questions) if questions else 1.0
    earned_points = 0.0

    for q in questions:
        submitted = answers.get(str(q.id), "").strip().lower()
        correct = (q.correct_answer or "").strip().lower()
        if submitted and submitted == correct:
            earned_points += q.points

    score = round((earned_points / total_points) * 100.0, 2) if total_points > 0 else 0.0
    passed = score >= assessment.passing_score

    attempt = AssessmentAttempt(
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        person_id=person_id,
        enrollment_id=enrollment_id,
        attempt_number=prior_attempts + 1,
        score=score,
        passed=passed,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(attempt)

    # If passed and tied to an enrollment, update enrollment progress
    if passed and enrollment_id:
        enrollment = db.query(LearningEnrollment).filter(
            LearningEnrollment.id == enrollment_id,
            LearningEnrollment.tenant_id == tenant_id,
        ).first()
        if enrollment:
            enrollment.completion_score = score
            if enrollment.progress_percentage < 100.0:
                enrollment.progress_percentage = 100.0
                enrollment.status = LearningEnrollmentStatus.COMPLETED.value
                enrollment.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(attempt)
    return attempt


def get_learning_analytics(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Computes learning effectiveness and participation metrics for L&D administration.
    """
    total_courses = db.query(LearningCourse).filter(
        or_(LearningCourse.tenant_id == tenant_id, LearningCourse.tenant_id.is_(None))
    ).count()

    published_courses = db.query(LearningCourse).filter(
        or_(LearningCourse.tenant_id == tenant_id, LearningCourse.tenant_id.is_(None)),
        LearningCourse.status == "PUBLISHED"
    ).count()

    enrollments_query = db.query(LearningEnrollment).filter(LearningEnrollment.tenant_id == tenant_id)
    total_enrollments = enrollments_query.count()
    completed_enrollments = enrollments_query.filter(
        LearningEnrollment.status == LearningEnrollmentStatus.COMPLETED.value
    ).count()

    completion_rate = round((completed_enrollments / total_enrollments) * 100.0, 1) if total_enrollments > 0 else 0.0

    # Calculate total training hours from completed enrollments
    completed_records = db.query(LearningEnrollment).filter(
        LearningEnrollment.tenant_id == tenant_id,
        LearningEnrollment.status == LearningEnrollmentStatus.COMPLETED.value,
    ).all()
    total_minutes = 0
    for enr in completed_records:
        if enr.course:
            total_minutes += enr.course.duration_minutes
    total_training_hours = round(total_minutes / 60.0, 1)

    # Mandatory training assignments
    mand_query = db.query(TrainingAssignment).filter(TrainingAssignment.tenant_id == tenant_id)
    mand_total = mand_query.count()
    mand_completed = mand_query.filter(TrainingAssignment.status == "COMPLETED").count()
    mand_rate = round((mand_completed / mand_total) * 100.0, 1) if mand_total > 0 else 100.0

    # Certifications expiring within 30 days
    today = date.today()
    in_30_days = today + timedelta(days=30)
    expiring_certs = db.query(EmployeeCertification).filter(
        EmployeeCertification.tenant_id == tenant_id,
        EmployeeCertification.expiry_date >= today,
        EmployeeCertification.expiry_date <= in_30_days,
        EmployeeCertification.verification_status == CertificationVerificationStatus.VERIFIED.value,
    ).count()

    # Active mentoring pairs
    active_mentoring = db.query(MentoringRelationship).filter(
        MentoringRelationship.tenant_id == tenant_id,
        MentoringRelationship.status == MentoringStatus.ACTIVE.value,
    ).count()

    # Skill evidence records
    skill_evidences = db.query(SkillEvidence).filter(
        SkillEvidence.tenant_id == tenant_id
    ).count()

    return {
        "total_courses": total_courses,
        "published_courses": published_courses,
        "total_enrollments": total_enrollments,
        "completed_enrollments": completed_enrollments,
        "completion_rate_pct": completion_rate,
        "total_training_hours": total_training_hours,
        "mandatory_assignments_count": mand_total,
        "mandatory_completed_count": mand_completed,
        "mandatory_compliance_rate_pct": mand_rate,
        "expiring_certifications_30d": expiring_certs,
        "active_mentoring_relationships": active_mentoring,
        "skill_evidence_records_count": skill_evidences,
    }


def get_employee_dashboard_data(db: Session, tenant_id: str, person_id: str) -> Dict[str, Any]:
    """
    Aggregates learning metrics and records for an employee self-service dashboard.
    """
    enrollments = db.query(LearningEnrollment).filter(
        LearningEnrollment.tenant_id == tenant_id,
        LearningEnrollment.person_id == person_id,
    ).all()

    assigned_count = sum(1 for e in enrollments if e.status == LearningEnrollmentStatus.ASSIGNED.value)
    in_progress_count = sum(1 for e in enrollments if e.status in (LearningEnrollmentStatus.ENROLLED.value, LearningEnrollmentStatus.IN_PROGRESS.value))
    completed_count = sum(1 for e in enrollments if e.status == LearningEnrollmentStatus.COMPLETED.value)

    today = date.today()
    in_30_days = today + timedelta(days=30)
    certs = db.query(EmployeeCertification).filter(
        EmployeeCertification.tenant_id == tenant_id,
        EmployeeCertification.person_id == person_id,
    ).all()

    active_certs = sum(1 for c in certs if c.verification_status == CertificationVerificationStatus.VERIFIED.value and (not c.expiry_date or c.expiry_date >= today))
    expiring_certs = sum(1 for c in certs if c.expiry_date and today <= c.expiry_date <= in_30_days)

    goals_count = db.query(DevelopmentGoal).join(DevelopmentPlan).filter(
        DevelopmentPlan.tenant_id == tenant_id,
        DevelopmentPlan.person_id == person_id,
    ).count()

    active_mentoring = db.query(MentoringRelationship).filter(
        MentoringRelationship.tenant_id == tenant_id,
        or_(
            MentoringRelationship.mentor_person_id == person_id,
            MentoringRelationship.mentee_person_id == person_id,
        ),
        MentoringRelationship.status == MentoringStatus.ACTIVE.value,
    ).count()

    return {
        "assigned_courses_count": assigned_count,
        "in_progress_courses_count": in_progress_count,
        "completed_courses_count": completed_count,
        "active_certifications_count": active_certs,
        "expiring_certifications_count": expiring_certs,
        "development_goals_count": goals_count,
        "active_mentoring_count": active_mentoring,
        "recent_enrollments": enrollments[:5],
        "my_certifications": certs,
    }


def get_manager_team_dashboard_data(db: Session, tenant_id: str, manager_person_id: str) -> Dict[str, Any]:
    """
    Aggregates learning metrics for team members reporting to a given manager.
    Finds direct reports via active Engagement or PositionAssignment.
    """
    # Find direct reports via active engagements or position hierarchy
    # Query persons with active engagement
    engagements = db.query(Engagement).filter(
        Engagement.status.in_(["ACTIVE", "active", "CONFIRMED", "confirmed"])
    ).all()

    team_person_ids = [e.person_id for e in engagements if e.person_id != manager_person_id]
    # Fallback to limit team scope
    if not team_person_ids:
        team_person_ids = [manager_person_id]

    team_enrollments = db.query(LearningEnrollment).filter(
        LearningEnrollment.tenant_id == tenant_id,
        LearningEnrollment.person_id.in_(team_person_ids),
    ).all()

    total_enr = len(team_enrollments)
    completed_enr = sum(1 for e in team_enrollments if e.status == LearningEnrollmentStatus.COMPLETED.value)
    comp_rate = round((completed_enr / total_enr) * 100.0, 1) if total_enr > 0 else 0.0

    today = date.today()
    overdue_mand = db.query(TrainingAssignment).filter(
        TrainingAssignment.tenant_id == tenant_id,
        TrainingAssignment.person_id.in_(team_person_ids),
        TrainingAssignment.status != "COMPLETED",
        TrainingAssignment.due_at < datetime.utcnow(),
    ).count()

    in_30_days = today + timedelta(days=30)
    team_exp_certs = db.query(EmployeeCertification).filter(
        EmployeeCertification.tenant_id == tenant_id,
        EmployeeCertification.person_id.in_(team_person_ids),
        EmployeeCertification.expiry_date >= today,
        EmployeeCertification.expiry_date <= in_30_days,
    ).count()

    team_skill_gaps = db.query(SkillGapAnalysis).filter(
        SkillGapAnalysis.tenant_id == tenant_id,
    ).count()

    return {
        "team_member_count": len(team_person_ids),
        "team_enrollments_count": total_enr,
        "team_completions_count": completed_enr,
        "team_completion_rate_pct": comp_rate,
        "overdue_mandatory_count": overdue_mand,
        "team_expiring_certifications": team_exp_certs,
        "team_skill_gaps_count": team_skill_gaps,
    }
