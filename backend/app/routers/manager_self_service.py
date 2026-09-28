from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import (
    AuditResult,
    User,
    Engagement,
    Person,
    LeaveRequest,
    LeaveStatus,
    Attendance,
    AttendanceStatus,
    Evaluation,
    EvaluationStatus,
    Candidate,
)
# Onboarding models are in a separate module (v4)
from app.models_v4 import OnboardingTask, OnboardingProcess, TaskStatus

from app.schemas_manager import (
    ManagerDashboardOut,
    TeamMemberOut,
    LeavePendingOut,
    AttendanceExceptionOut,
    OnboardingTaskPendingOut,
    EvaluationPendingOut,
    CandidateOut,
)

router = APIRouter(prefix="/api/v3/manager", tags=["manager_self_service"])

# Helper to fetch IDs of persons that report to the current manager
def get_team_person_ids(current_user: User, db: Session) -> List[str]:
    # Engagement.reporting_manager_id references User.id
    engagements = (
        db.query(Engagement.person_id)
        .filter(Engagement.reporting_manager_id == current_user.id)
        .all()
    )
    return [e[0] for e in engagements]

@router.get("/me", response_model=ManagerDashboardOut)
def get_manager_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard:view")),
):
    # Ensure the user is a manager (has reporting relationships)
    team_person_ids = get_team_person_ids(current_user, db)
    if not team_person_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No team members found for this manager",
        )

    # Team members
    team_members = (
        db.query(Person)
        .filter(Person.id.in_(team_person_ids))
        .all()
    )
    team_out: List[TeamMemberOut] = []
    for p in team_members:
        # Derive designation & department from the latest active engagement if available
        engagement = (
            db.query(Engagement)
            .filter(Engagement.person_id == p.id)
            .order_by(Engagement.start_date.desc())
            .first()
        )
        team_out.append(
            TeamMemberOut(
                id=p.id,
                full_name=p.full_name,
                designation=engagement.designation if engagement else None,
                department=engagement.department if engagement else None,
                joining_date=engagement.start_date if engagement else None,
                status=engagement.status.value if engagement else None,
            )
        )

    # Pending leaves for the team
    pending_leaves = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.person_id.in_(team_person_ids),
            LeaveRequest.status == LeaveStatus.PENDING,
        )
        .all()
    )
    leaves_out: List[LeavePendingOut] = [
        LeavePendingOut(
            id=l.id,
            person_id=l.person_id,
            leave_type=l.leave_type.value,
            start_date=l.start_date,
            end_date=l.end_date,
            days=float(l.days),
            reason=l.reason,
            status=l.status.value,
        )
        for l in pending_leaves
    ]

    # Attendance exceptions (anything other than PRESENT)
    attendance_exceptions = (
        db.query(Attendance)
        .filter(
            Attendance.person_id.in_(team_person_ids),
            Attendance.status != AttendanceStatus.PRESENT,
        )
        .all()
    )
    attendance_out: List[AttendanceExceptionOut] = [
        AttendanceExceptionOut(
            id=a.id,
            person_id=a.person_id,
            date=a.date,
            status=a.status.value,
            notes=a.notes,
        )
        for a in attendance_exceptions
    ]

    # Onboarding task pending for team members
    pending_tasks = (
        db.query(OnboardingTask)
        .join(OnboardingProcess, OnboardingTask.process_id == OnboardingProcess.id)
        .filter(
            OnboardingProcess.person_id.in_(team_person_ids),
            OnboardingTask.status == TaskStatus.PENDING,
        )
        .all()
    )
    tasks_out: List[OnboardingTaskPendingOut] = [
        OnboardingTaskPendingOut(
            id=t.id,
            title=t.title,
            category=t.category.value,
            assignee_role=t.assignee_role.value,
            status=t.status.value,
            due_date=t.due_date,
        )
        for t in pending_tasks
    ]

    # Pending evaluations (drafts) for team members
    pending_evals = (
        db.query(Evaluation)
        .filter(
            Evaluation.person_id.in_(team_person_ids),
            Evaluation.status == EvaluationStatus.DRAFT,
        )
        .all()
    )
    evals_out: List[EvaluationPendingOut] = [
        EvaluationPendingOut(
            id=e.id,
            person_id=e.person_id,
            evaluator_id=e.evaluator_id,
            period_start=e.period_start,
            period_end=e.period_end,
            status=e.status.value,
        )
        for e in pending_evals
    ]

    # Candidates where this manager is the hiring manager
    candidates = (
        db.query(Candidate)
        .filter(Candidate.hiring_manager_id == current_user.id)
        .all()
    )
    candidates_out: List[CandidateOut] = [
        CandidateOut(
            id=c.id,
            person_id=c.person_id,
            hiring_manager_id=c.hiring_manager_id,
            applied_position=c.applied_position,
            department=c.department,
            status=c.status.value,
        )
        for c in candidates
    ]

    dashboard = ManagerDashboardOut(
        team_headcount=len(team_out),
        active_employees=len([m for m in team_out if m.status == "active"]),
        pending_leaves=leaves_out,
        attendance_exceptions=attendance_out,
        onboarding_tasks=tasks_out,
        pending_evaluations=evals_out,
        candidates=candidates_out,
    )
    log_audit(
        db,
        user=current_user,
        action="manager_dashboard_viewed",
        entity="manager_self_service",
        entity_id=None,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"team_headcount": len(team_out)},
    )
    return dashboard
