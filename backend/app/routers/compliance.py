from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit, has_permission
from app.models import AuditResult, User, UserRole
from app.models_v3 import Tenant, LegalEntity
from app.models_statutory import StatutoryRegistration, StatutoryFiling, FilingStatus
from app.models_compliance import ComplianceTask, ComplianceCalendar, ComplianceType, ComplianceStatus
from app.schemas_compliance import (
    ComplianceTaskCreate,
    ComplianceTaskUpdate,
    ComplianceTaskOut,
    ComplianceDashboardOut,
    ComplianceCalendarOut,
)

router = APIRouter(prefix="/api/v3/compliance", tags=["compliance"])


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
# 1. Compliance Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=ComplianceDashboardOut)
def get_compliance_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    today = date.today()

    tasks_query = db.query(ComplianceTask).filter(ComplianceTask.tenant_id == tenant_id)
    cal_query = db.query(ComplianceCalendar).filter(ComplianceCalendar.tenant_id == tenant_id)

    # Automatically mark overdue tasks whose due date has passed
    overdue_tasks = tasks_query.filter(
        ComplianceTask.due_date < today,
        ComplianceTask.status.notin_([ComplianceStatus.COMPLETED, ComplianceStatus.CANCELLED, ComplianceStatus.WAIVED]),
    ).all()
    for t in overdue_tasks:
        t.status = ComplianceStatus.OVERDUE
    if overdue_tasks:
        db.commit()

    total_tasks = tasks_query.all()
    overdue_count = sum(1 for t in total_tasks if t.status == ComplianceStatus.OVERDUE)
    completed_count = sum(1 for t in total_tasks if t.status == ComplianceStatus.COMPLETED)
    upcoming_count = sum(1 for t in total_tasks if t.status in (ComplianceStatus.OPEN, ComplianceStatus.IN_PROGRESS, ComplianceStatus.DUE_SOON))

    pending_filings = db.query(StatutoryFiling).filter(
        StatutoryFiling.tenant_id == tenant_id,
        StatutoryFiling.status.in_([FilingStatus.DRAFT, FilingStatus.READY]),
    ).count()

    active_regs = db.query(StatutoryRegistration).filter(
        StatutoryRegistration.tenant_id == tenant_id,
        StatutoryRegistration.status == "active",
    ).count()

    events = cal_query.order_by(ComplianceCalendar.due_date.asc()).limit(20).all()

    return ComplianceDashboardOut(
        upcoming_deadlines_count=upcoming_count,
        overdue_count=overdue_count,
        pending_filings_count=pending_filings,
        completed_tasks_count=completed_count,
        active_registrations_count=active_regs,
        tasks=[ComplianceTaskOut.model_validate(t) for t in total_tasks[:20]],
        calendar_events=[ComplianceCalendarOut.model_validate(e) for e in events],
    )


# ---------------------------------------------------------------------------
# 2. Compliance Tasks
# ---------------------------------------------------------------------------

@router.get("/tasks", response_model=List[ComplianceTaskOut])
def list_compliance_tasks(
    compliance_type: Optional[ComplianceType] = None,
    status_filter: Optional[ComplianceStatus] = None,
    assigned_to_me: bool = False,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(ComplianceTask).filter(ComplianceTask.tenant_id == tenant_id)

    if compliance_type:
        query = query.filter(ComplianceTask.compliance_type == compliance_type)
    if status_filter:
        query = query.filter(ComplianceTask.status == status_filter)
    if assigned_to_me:
        query = query.filter(ComplianceTask.assigned_user_id == current_user.id)

    return query.order_by(ComplianceTask.due_date.asc()).all()


@router.post("/tasks", response_model=ComplianceTaskOut, status_code=status.HTTP_201_CREATED)
def create_compliance_task(
    payload: ComplianceTaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)

    task = ComplianceTask(
        tenant_id=tenant_id,
        legal_entity_id=payload.legal_entity_id,
        compliance_type=payload.compliance_type,
        authority=payload.authority,
        title=payload.title,
        description=payload.description,
        period=payload.period,
        due_date=payload.due_date,
        status=ComplianceStatus.OPEN,
        priority=payload.priority or 1,
        assigned_user_id=payload.assigned_user_id,
        evidence_document_id=payload.evidence_document_id,
        source_entity_type=payload.source_entity_type,
        source_entity_id=payload.source_entity_id,
        reminder_config=payload.reminder_config,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_audit(
        db,
        user=current_user,
        action="compliance_task_created",
        entity="compliance_task",
        entity_id=task.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"title": task.title, "type": task.compliance_type.value},
    )
    return task


@router.get("/tasks/{task_id}", response_model=ComplianceTaskOut)
def get_compliance_task(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    task = db.query(ComplianceTask).filter(ComplianceTask.id == task_id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compliance task not found")
    if task.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant task access forbidden")
    return task


@router.patch("/tasks/{task_id}", response_model=ComplianceTaskOut)
def update_compliance_task(
    task_id: str,
    payload: ComplianceTaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update task status or assignment. Authorized for compliance managers or assigned task owners."""
    tenant_id = _resolve_tenant_id(request, db)
    task = db.query(ComplianceTask).filter(ComplianceTask.id == task_id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compliance task not found")
    if task.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant task access forbidden")

    is_manager = is_hr_or_super(current_user) or has_permission(current_user, "compliance:manage", db)
    is_assigned = task.assigned_user_id and str(task.assigned_user_id) == str(current_user.id)
    has_complete_perm = has_permission(current_user, "compliance:complete", db)

    if not (is_manager or is_assigned or has_complete_perm):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized to update this compliance task")

    if payload.status:
        task.status = payload.status
        if payload.status == ComplianceStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
    if payload.priority is not None and is_manager:
        task.priority = payload.priority
    if payload.assigned_user_id is not None and is_manager:
        task.assigned_user_id = payload.assigned_user_id
    if payload.evidence_document_id is not None:
        task.evidence_document_id = payload.evidence_document_id
    if payload.description is not None:
        task.description = payload.description

    db.commit()
    db.refresh(task)

    log_audit(
        db,
        user=current_user,
        action="compliance_task_updated",
        entity="compliance_task",
        entity_id=task.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"status": task.status.value},
    )
    return task
