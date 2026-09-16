"""Phase 9 – Analytics & Reporting: live computed dashboard metrics."""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.deps import require_permission
from app.models import User, Person, Engagement, EngagementStatus, LeaveRequest, LeaveStatus, Attendance
from app.models_v6 import PayrollRun, Payslip, PayrollRunStatus
from app.models_v7 import Enrollment, EnrollmentStatus as LMSStatus
from app.models_v8 import AnalyticsSnapshot

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:view")),
):
    """Live-computed dashboard metrics."""
    total_employees = db.query(Engagement).filter(Engagement.status == EngagementStatus.ACTIVE).count()
    total_persons = db.query(Person).count()
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.PENDING).count()
    approved_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.APPROVED).count()
    active_enrollments = db.query(Enrollment).filter(Enrollment.status.in_([LMSStatus.ENROLLED, LMSStatus.IN_PROGRESS])).count()

    # Department distribution
    dept_counts = db.query(
        Engagement.department, func.count(Engagement.id)
    ).filter(Engagement.status == EngagementStatus.ACTIVE).group_by(Engagement.department).all()

    return {
        "total_persons": total_persons,
        "active_employees": total_employees,
        "pending_leave_requests": pending_leaves,
        "approved_leaves": approved_leaves,
        "active_lms_enrollments": active_enrollments,
        "department_distribution": {dept: count for dept, count in dept_counts},
        "computed_at": datetime.utcnow().isoformat(),
    }


@router.get("/headcount-trend")
def headcount_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:view")),
):
    """Stored analytics snapshots for headcount trend."""
    snapshots = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.metric_name == "headcount"
    ).order_by(AnalyticsSnapshot.period).all()
    return [
        {"period": s.period, "value": s.metric_value, "dimension": s.dimension_value}
        for s in snapshots
    ]


@router.post("/snapshot")
def create_snapshot(
    metric_name: str,
    metric_value: float,
    period: str,
    dimension: Optional[str] = None,
    dimension_value: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:export")),
):
    snap = AnalyticsSnapshot(
        metric_name=metric_name,
        metric_value=metric_value,
        period=period,
        dimension=dimension,
        dimension_value=dimension_value,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return {"id": snap.id, "metric_name": metric_name, "metric_value": metric_value}


@router.get("/payroll-summary")
def payroll_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:view")),
):
    runs = db.query(PayrollRun).filter(
        PayrollRun.status.in_([PayrollRunStatus.COMPUTED, PayrollRunStatus.APPROVED, PayrollRunStatus.DISBURSED])
    ).order_by(PayrollRun.month).all()
    return [
        {
            "month": r.month,
            "total_gross": float(r.total_gross) if r.total_gross else 0,
            "total_net": float(r.total_net) if r.total_net else 0,
            "employees": r.employee_count,
            "status": r.status,
        }
        for r in runs
    ]
