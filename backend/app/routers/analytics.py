"""
routers/analytics.py - Module 13: Enterprise HR Analytics & Workforce Intelligence Endpoints.

All endpoints mounted under /api/v3/analytics/...
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, require_permission, log_audit
from app.models import AuditResult, User, UserRole
from app.models_v3 import Tenant
from app.adapters.analytics_engine import AnalyticsEngine
from app.schemas_analytics import (
    HeadcountMetricOut,
    AttritionMetricOut,
    AttendanceMetricOut,
    LeaveMetricOut,
    RecruitmentMetricOut,
    CompensationMetricOut,
    PayrollMetricOut,
    PerformanceMetricOut,
    LearningMetricOut,
    ComplianceMetricOut,
    WorkforceCostMetricOut,
    ExecutiveDashboardOut,
)

router = APIRouter(prefix="/api/v3/analytics", tags=["analytics"])


def _resolve_tenant_id(request: Request, db: Session) -> str:
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def is_hr_or_super(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


# ---------------------------------------------------------------------------
# 1. Workforce & Headcount Endpoints
# ---------------------------------------------------------------------------

@router.get("/headcount", response_model=HeadcountMetricOut)
@router.get("/workforce", response_model=HeadcountMetricOut)
def get_workforce_headcount(
    request: Request,
    department: Optional[str] = Query(None),
    work_location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:view", db) or has_permission(current_user, "analytics:workforce", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view workforce analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    filters = {}
    if department:
        filters["department"] = department
    if work_location:
        filters["work_location"] = work_location

    return engine.get_headcount_analytics(filters)


# ---------------------------------------------------------------------------
# 2. Attrition Endpoints
# ---------------------------------------------------------------------------

@router.get("/attrition", response_model=AttritionMetricOut)
def get_attrition_analytics(
    request: Request,
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:view", db) or has_permission(current_user, "analytics:workforce", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view attrition analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_attrition_analytics({"department": department} if department else None)


# ---------------------------------------------------------------------------
# 3. Attendance & Leave Endpoints
# ---------------------------------------------------------------------------

@router.get("/attendance", response_model=AttendanceMetricOut)
def get_attendance_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:attendance", db) or has_permission(current_user, "analytics:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view attendance analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_attendance_analytics()


@router.get("/leave", response_model=LeaveMetricOut)
def get_leave_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:leave", db) or has_permission(current_user, "analytics:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view leave analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_leave_analytics()


# ---------------------------------------------------------------------------
# 4. Recruitment Endpoints
# ---------------------------------------------------------------------------

@router.get("/recruitment", response_model=RecruitmentMetricOut)
def get_recruitment_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:recruitment", db) or has_permission(current_user, "candidates:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view recruitment analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_recruitment_analytics()


# ---------------------------------------------------------------------------
# 5. Compensation & Payroll Endpoints (Strict RBAC & Privacy)
# ---------------------------------------------------------------------------

@router.get("/compensation", response_model=CompensationMetricOut)
def get_compensation_analytics(
    request: Request,
    min_threshold: int = Query(3, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_perm = (
        is_hr_or_super(current_user)
        or current_user.role == UserRole.FINANCE
        or has_permission(current_user, "analytics:compensation", db)
        or has_permission(current_user, "compensation:view", db)
        or current_user.role == UserRole.HIRING_MANAGER
    )
    if not has_perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to compensation analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_compensation_analytics(min_threshold=min_threshold)


@router.get("/payroll", response_model=PayrollMetricOut)
def get_payroll_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_perm = (
        is_hr_or_super(current_user)
        or current_user.role == UserRole.FINANCE
        or has_permission(current_user, "analytics:payroll", db)
        or has_permission(current_user, "stipends:view", db)
    )
    if not has_perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to payroll analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_payroll_analytics()


# ---------------------------------------------------------------------------
# 6. Performance & Learning Endpoints
# ---------------------------------------------------------------------------

@router.get("/performance", response_model=PerformanceMetricOut)
def get_performance_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:performance", db) or has_permission(current_user, "evaluations:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view performance analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_performance_analytics()


@router.get("/learning", response_model=LearningMetricOut)
def get_learning_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:learning", db) or has_permission(current_user, "analytics:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view learning analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_learning_analytics()


# ---------------------------------------------------------------------------
# 7. Compliance Analytics Endpoints (Module 12 Integration)
# ---------------------------------------------------------------------------

@router.get("/compliance", response_model=ComplianceMetricOut)
def get_compliance_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:compliance", db) or has_permission(current_user, "compliance:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view compliance analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_compliance_analytics()


# ---------------------------------------------------------------------------
# 8. Workforce Cost Endpoints
# ---------------------------------------------------------------------------

@router.get("/workforce-cost", response_model=WorkforceCostMetricOut)
def get_workforce_cost_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_perm = (
        is_hr_or_super(current_user)
        or current_user.role == UserRole.FINANCE
        or has_permission(current_user, "analytics:compensation", db)
        or has_permission(current_user, "analytics:payroll", db)
    )
    if not has_perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to workforce cost analytics")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_workforce_cost_analytics()


# ---------------------------------------------------------------------------
# 9. Unified Executive Dashboard Endpoint
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=ExecutiveDashboardOut)
@router.get("/executive-dashboard", response_model=ExecutiveDashboardOut)
def get_executive_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "dashboards:view", db) or has_permission(current_user, "analytics:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view executive dashboard")

    tenant_id = _resolve_tenant_id(request, db)
    engine = AnalyticsEngine(db, tenant_id, current_user)
    return engine.get_executive_dashboard()
