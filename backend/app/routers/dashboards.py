"""
routers/dashboards.py - Module 13: Configurable Analytics Dashboards and Widgets.

All endpoints mounted under /api/v3/dashboards/...
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, require_permission, log_audit
from app.models import AuditResult, User, UserRole
from app.models_v3 import Tenant
from app.models_analytics import (
    AnalyticsDashboard,
    AnalyticsWidget,
    DashboardType,
    Visibility,
)
from app.schemas_analytics import (
    DashboardCreate,
    DashboardUpdate,
    DashboardOut,
    WidgetCreate,
    WidgetUpdate,
    WidgetOut,
)

router = APIRouter(prefix="/api/v3/dashboards", tags=["dashboards"])


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
# 1. Dashboards CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=List[DashboardOut])
@router.get("/", response_model=List[DashboardOut])
def list_dashboards(
    request: Request,
    dashboard_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "dashboards:view", db) or has_permission(current_user, "analytics:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view dashboards")

    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(AnalyticsDashboard).filter(AnalyticsDashboard.tenant_id == tenant_id)

    if dashboard_type:
        query = query.filter(AnalyticsDashboard.dashboard_type == dashboard_type)

    dashboards = query.order_by(AnalyticsDashboard.created_at.desc()).all()

    # Filter by visibility & owner if not super/HR admin
    if not is_hr_or_super(current_user):
        user_role_str = str(current_user.role).replace("UserRole.", "")
        dashboards = [
            d for d in dashboards
            if d.visibility == Visibility.PUBLIC.value
            or d.owner_id == current_user.id
            or (d.visibility == Visibility.ROLE_BASED.value and d.allowed_roles and user_role_str in d.allowed_roles)
        ]

    return dashboards


@router.post("", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
def create_dashboard(
    payload: DashboardCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "dashboards:manage", db) or has_permission(current_user, "analytics:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create dashboards")

    tenant_id = _resolve_tenant_id(request, db)
    dashboard = AnalyticsDashboard(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        dashboard_type=payload.dashboard_type,
        layout=payload.layout or {},
        is_default=payload.is_default,
        visibility=payload.visibility,
        owner_id=current_user.id,
        allowed_roles=payload.allowed_roles or [],
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)

    # Optional initial widgets
    if payload.widgets:
        for w in payload.widgets:
            widget = AnalyticsWidget(
                tenant_id=tenant_id,
                dashboard_id=dashboard.id,
                title=w.title,
                widget_type=w.widget_type,
                metric=w.metric,
                dimensions=w.dimensions or [],
                filters=w.filters or {},
                report_definition_id=w.report_definition_id,
                position=w.position,
            )
            db.add(widget)
        db.commit()
        db.refresh(dashboard)

    log_audit(db, user=current_user, action="create", entity="analytics_dashboard", entity_id=dashboard.id, result=AuditResult.SUCCESS, request=request)
    return dashboard


@router.get("/{id}", response_model=DashboardOut)
def get_dashboard(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    dashboard = db.query(AnalyticsDashboard).filter(
        AnalyticsDashboard.id == id,
        AnalyticsDashboard.tenant_id == tenant_id,
    ).first()
    if not dashboard:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not found")

    if not is_hr_or_super(current_user) and dashboard.owner_id != current_user.id:
        user_role_str = str(current_user.role).replace("UserRole.", "")
        if dashboard.visibility == Visibility.PRIVATE.value:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Private dashboard")
        if dashboard.visibility == Visibility.ROLE_BASED.value and (not dashboard.allowed_roles or user_role_str not in dashboard.allowed_roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Role not permitted to view this dashboard")

    return dashboard


@router.patch("/{id}", response_model=DashboardOut)
def update_dashboard(
    id: str,
    payload: DashboardUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    dashboard = db.query(AnalyticsDashboard).filter(
        AnalyticsDashboard.id == id,
        AnalyticsDashboard.tenant_id == tenant_id,
    ).first()
    if not dashboard:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not found")

    if not is_hr_or_super(current_user) and dashboard.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or an administrator can update this dashboard")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(dashboard, k, v)

    db.commit()
    db.refresh(dashboard)
    log_audit(db, user=current_user, action="update", entity="analytics_dashboard", entity_id=dashboard.id, result=AuditResult.SUCCESS, request=request)
    return dashboard


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    dashboard = db.query(AnalyticsDashboard).filter(
        AnalyticsDashboard.id == id,
        AnalyticsDashboard.tenant_id == tenant_id,
    ).first()
    if not dashboard:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not found")

    if not is_hr_or_super(current_user) and dashboard.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or an administrator can delete this dashboard")

    db.delete(dashboard)
    db.commit()
    log_audit(db, user=current_user, action="delete", entity="analytics_dashboard", entity_id=id, result=AuditResult.SUCCESS, request=request)
    return None


# ---------------------------------------------------------------------------
# 2. Widgets CRUD
# ---------------------------------------------------------------------------

@router.post("/{id}/widgets", response_model=WidgetOut, status_code=status.HTTP_201_CREATED)
def add_widget(
    id: str,
    payload: WidgetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    dashboard = db.query(AnalyticsDashboard).filter(
        AnalyticsDashboard.id == id,
        AnalyticsDashboard.tenant_id == tenant_id,
    ).first()
    if not dashboard:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not found")

    if not is_hr_or_super(current_user) and dashboard.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or an administrator can modify widgets")

    widget = AnalyticsWidget(
        tenant_id=tenant_id,
        dashboard_id=dashboard.id,
        title=payload.title,
        widget_type=payload.widget_type,
        metric=payload.metric,
        dimensions=payload.dimensions or [],
        filters=payload.filters or {},
        report_definition_id=payload.report_definition_id,
        position=payload.position,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)

    log_audit(db, user=current_user, action="create", entity="analytics_widget", entity_id=widget.id, result=AuditResult.SUCCESS, request=request)
    return widget


@router.delete("/{id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_widget(
    id: str,
    widget_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    widget = db.query(AnalyticsWidget).filter(
        AnalyticsWidget.id == widget_id,
        AnalyticsWidget.dashboard_id == id,
        AnalyticsWidget.tenant_id == tenant_id,
    ).first()
    if not widget:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Widget not found")

    dashboard = db.query(AnalyticsDashboard).filter(AnalyticsDashboard.id == id).first()
    if not is_hr_or_super(current_user) and dashboard and dashboard.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or an administrator can remove widgets")

    db.delete(widget)
    db.commit()
    log_audit(db, user=current_user, action="delete", entity="analytics_widget", entity_id=widget_id, result=AuditResult.SUCCESS, request=request)
    return None
