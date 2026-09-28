"""
routers/reports.py - Module 13: Report Builder, Scheduled Reports & Execution Endpoints.

All endpoints mounted under /api/v3/reports/...
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, require_permission, log_audit
from app.models import AuditResult, User, UserRole
from app.models_v3 import Tenant
from app.models_analytics import (
    AnalyticsReportDefinition,
    ScheduledReport,
    ReportExecution,
    ReportExport,
    ExecutionStatus,
    ExportFormat,
    Visibility,
)
from app.adapters.analytics_engine import AnalyticsEngine
from app.schemas_analytics import (
    ReportDefinitionCreate,
    ReportDefinitionUpdate,
    ReportDefinitionOut,
    ScheduledReportCreate,
    ScheduledReportUpdate,
    ScheduledReportOut,
    ReportExecutionCreate,
    ReportExecutionOut,
    ReportExportOut,
)

router = APIRouter(prefix="/api/v3/reports", tags=["reports"])


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
# 1. Scheduled Reports (Must be registered before /{id} to avoid collision)
# ---------------------------------------------------------------------------

@router.get("/scheduled", response_model=List[ScheduledReportOut])
def list_scheduled_reports(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:schedule", db) or has_permission(current_user, "reports:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view scheduled reports")

    tenant_id = _resolve_tenant_id(request, db)
    schedules = db.query(ScheduledReport).filter(ScheduledReport.tenant_id == tenant_id).all()
    return schedules


@router.post("/scheduled", response_model=ScheduledReportOut, status_code=status.HTTP_201_CREATED)
def create_scheduled_report(
    payload: ScheduledReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:schedule", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to schedule reports")

    tenant_id = _resolve_tenant_id(request, db)
    report_def = db.query(AnalyticsReportDefinition).filter(
        AnalyticsReportDefinition.id == payload.report_definition_id,
        AnalyticsReportDefinition.tenant_id == tenant_id,
    ).first()
    if not report_def:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report definition not found")

    next_run = payload.next_run_at or (datetime.utcnow() + timedelta(days=30))

    sched = ScheduledReport(
        tenant_id=tenant_id,
        report_definition_id=payload.report_definition_id,
        frequency=payload.frequency,
        recipients=payload.recipients,
        format=payload.format,
        status=payload.status,
        next_run_at=next_run,
        created_by=current_user.id,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)

    log_audit(db, user=current_user, action="create", entity="scheduled_report", entity_id=sched.id, result=AuditResult.SUCCESS, request=request)
    return sched


@router.patch("/scheduled/{id}", response_model=ScheduledReportOut)
def update_scheduled_report(
    id: str,
    payload: ScheduledReportUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:schedule", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to update scheduled report")

    tenant_id = _resolve_tenant_id(request, db)
    sched = db.query(ScheduledReport).filter(
        ScheduledReport.id == id,
        ScheduledReport.tenant_id == tenant_id,
    ).first()
    if not sched:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheduled report not found")

    if payload.frequency is not None:
        sched.frequency = payload.frequency
    if payload.recipients is not None:
        sched.recipients = payload.recipients
    if payload.format is not None:
        sched.format = payload.format
    if payload.status is not None:
        sched.status = payload.status
    if payload.next_run_at is not None:
        sched.next_run_at = payload.next_run_at

    db.commit()
    db.refresh(sched)
    return sched


# ---------------------------------------------------------------------------
# 2. Report Definitions CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ReportDefinitionOut])
@router.get("/", response_model=List[ReportDefinitionOut])
def list_reports(
    request: Request,
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "reports:view", db) or has_permission(current_user, "analytics:view", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view reports")

    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(AnalyticsReportDefinition).filter(AnalyticsReportDefinition.tenant_id == tenant_id)

    if report_type:
        query = query.filter(AnalyticsReportDefinition.report_type == report_type)

    reports = query.order_by(AnalyticsReportDefinition.created_at.desc()).all()

    # Filter by visibility & owner if not super/HR admin
    if not is_hr_or_super(current_user):
        user_role_str = str(current_user.role).replace("UserRole.", "")
        reports = [
            r for r in reports
            if r.visibility == Visibility.PUBLIC.value
            or r.owner_id == current_user.id
            or (r.visibility == Visibility.ROLE_BASED.value and r.allowed_roles and user_role_str in r.allowed_roles)
        ]

    return reports


@router.post("", response_model=ReportDefinitionOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ReportDefinitionOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportDefinitionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create reports")

    tenant_id = _resolve_tenant_id(request, db)
    report = AnalyticsReportDefinition(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        report_type=payload.report_type,
        metrics=payload.metrics or [],
        dimensions=payload.dimensions or [],
        filters=payload.filters or {},
        grouping=payload.grouping or [],
        sorting=payload.sorting or [],
        visibility=payload.visibility,
        owner_id=current_user.id,
        allowed_roles=payload.allowed_roles or [],
        min_aggregation_threshold=payload.min_aggregation_threshold,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    log_audit(db, user=current_user, action="create", entity="analytics_report_definition", entity_id=report.id, result=AuditResult.SUCCESS, request=request)
    return report


@router.get("/{id}", response_model=ReportDefinitionOut)
def get_report(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    report = db.query(AnalyticsReportDefinition).filter(
        AnalyticsReportDefinition.id == id,
        AnalyticsReportDefinition.tenant_id == tenant_id,
    ).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report definition not found")

    # Visibility check
    if not is_hr_or_super(current_user) and report.owner_id != current_user.id:
        user_role_str = str(current_user.role).replace("UserRole.", "")
        if report.visibility == Visibility.PRIVATE.value:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Private report definition")
        if report.visibility == Visibility.ROLE_BASED.value and (not report.allowed_roles or user_role_str not in report.allowed_roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Role not permitted to view this report")

    return report


@router.patch("/{id}", response_model=ReportDefinitionOut)
def update_report(
    id: str,
    payload: ReportDefinitionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    report = db.query(AnalyticsReportDefinition).filter(
        AnalyticsReportDefinition.id == id,
        AnalyticsReportDefinition.tenant_id == tenant_id,
    ).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report definition not found")

    if not is_hr_or_super(current_user) and report.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or an administrator can modify this report")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(report, k, v)

    db.commit()
    db.refresh(report)
    log_audit(db, user=current_user, action="update", entity="analytics_report_definition", entity_id=report.id, result=AuditResult.SUCCESS, request=request)
    return report


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    report = db.query(AnalyticsReportDefinition).filter(
        AnalyticsReportDefinition.id == id,
        AnalyticsReportDefinition.tenant_id == tenant_id,
    ).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report definition not found")

    if not is_hr_or_super(current_user) and report.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or an administrator can delete this report")

    db.delete(report)
    db.commit()
    log_audit(db, user=current_user, action="delete", entity="analytics_report_definition", entity_id=id, result=AuditResult.SUCCESS, request=request)
    return None


# ---------------------------------------------------------------------------
# 3. Report Execution & Export Endpoints
# ---------------------------------------------------------------------------

@router.post("/{id}/execute", response_model=ReportExecutionOut)
def execute_report(
    id: str,
    request: Request,
    payload: Optional[ReportExecutionCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db)
    report = db.query(AnalyticsReportDefinition).filter(
        AnalyticsReportDefinition.id == id,
        AnalyticsReportDefinition.tenant_id == tenant_id,
    ).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report definition not found")

    engine = AnalyticsEngine(db, tenant_id, current_user)
    params = payload.parameters if payload else {}
    execution = engine.execute_report(report, params)

    log_audit(db, user=current_user, action="execute", entity="analytics_report", entity_id=report.id, result=AuditResult.SUCCESS, request=request)
    return execution


@router.post("/{id}/export")
def export_report(
    id: str,
    request: Request,
    format: str = Query("CSV", pattern="^(CSV|JSON)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (is_hr_or_super(current_user) or has_permission(current_user, "analytics:export", db) or has_permission(current_user, "reports:export", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to export reports")

    tenant_id = _resolve_tenant_id(request, db)
    report = db.query(AnalyticsReportDefinition).filter(
        AnalyticsReportDefinition.id == id,
        AnalyticsReportDefinition.tenant_id == tenant_id,
    ).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report definition not found")

    engine = AnalyticsEngine(db, tenant_id, current_user)
    execution = engine.execute_report(report, {})

    if format.upper() == "CSV":
        csv_data = engine.generate_csv_export(report, {})
        filename = f"{report.name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M')}.csv"
        
        # Create ReportExport record
        export_record = ReportExport(
            tenant_id=tenant_id,
            execution_id=execution.id,
            export_format=ExportFormat.CSV.value,
            file_name=filename,
            file_size=len(csv_data),
            status="READY",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(export_record)
        db.commit()

        log_audit(db, user=current_user, action="export", entity="analytics_report", entity_id=report.id, result=AuditResult.SUCCESS, request=request)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        log_audit(db, user=current_user, action="export", entity="analytics_report", entity_id=report.id, result=AuditResult.SUCCESS, request=request)
        return {"report_id": report.id, "name": report.name, "status": "COMPLETED", "execution_id": execution.id}
