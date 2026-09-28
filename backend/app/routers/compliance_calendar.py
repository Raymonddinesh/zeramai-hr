from datetime import date, datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v3 import Tenant, LegalEntity
from app.models_compliance import ComplianceCalendar, ComplianceStatus, ComplianceType
from app.schemas_compliance import (
    ComplianceCalendarCreate,
    ComplianceCalendarUpdate,
    ComplianceCalendarOut,
)

router = APIRouter(prefix="/api/v3/compliance-calendar", tags=["compliance-calendar"])


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


def _resolve_legal_entity_id(tenant_id: str, db: Session, provided: Optional[str] = None) -> str:
    if provided:
        le = db.query(LegalEntity).filter(LegalEntity.id == provided).first()
        if le:
            return le.id
    le = db.query(LegalEntity).filter(LegalEntity.tenant_id == tenant_id).first()
    if not le:
        le = LegalEntity(
            tenant_id=tenant_id,
            name="Primary Legal Entity",
            country_code="IN",
            default_currency="INR",
        )
        db.add(le)
        db.commit()
    return le.id


@router.get("", response_model=List[ComplianceCalendarOut])
@router.get("/", response_model=List[ComplianceCalendarOut])
def list_calendar_entries(
    compliance_type: Optional[ComplianceType] = None,
    status_filter: Optional[ComplianceStatus] = None,
    period: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(ComplianceCalendar).filter(ComplianceCalendar.tenant_id == tenant_id)

    if compliance_type:
        query = query.filter(ComplianceCalendar.compliance_type == compliance_type)
    if status_filter:
        query = query.filter(ComplianceCalendar.status == status_filter)
    if period:
        query = query.filter(ComplianceCalendar.period == period)

    return query.order_by(ComplianceCalendar.due_date.asc()).all()


@router.post("", response_model=ComplianceCalendarOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ComplianceCalendarOut, status_code=status.HTTP_201_CREATED)
def create_calendar_entry(
    payload: ComplianceCalendarCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    legal_entity_id = _resolve_legal_entity_id(tenant_id, db, payload.legal_entity_id)

    entry = ComplianceCalendar(
        tenant_id=tenant_id,
        legal_entity_id=legal_entity_id,
        compliance_type=payload.compliance_type,
        authority=payload.authority,
        title=payload.title,
        description=payload.description,
        period=payload.period,
        due_date=payload.due_date,
        status=ComplianceStatus.OPEN,
        priority=payload.priority or 1,
        assigned_user_id=payload.assigned_user_id,
        reminder_config=payload.reminder_config,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    log_audit(
        db,
        user=current_user,
        action="compliance_calendar_created",
        entity="compliance_calendar",
        entity_id=entry.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"title": entry.title, "due_date": entry.due_date.isoformat()},
    )
    return entry


@router.get("/{entry_id}", response_model=ComplianceCalendarOut)
def get_calendar_entry(
    entry_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:view")),
):
    tenant_id = _resolve_tenant_id(request, db)
    entry = db.query(ComplianceCalendar).filter(ComplianceCalendar.id == entry_id).first()
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar entry not found")
    if entry.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")
    return entry


@router.patch("/{entry_id}", response_model=ComplianceCalendarOut)
def update_calendar_entry(
    entry_id: str,
    payload: ComplianceCalendarUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:manage")),
):
    tenant_id = _resolve_tenant_id(request, db)
    entry = db.query(ComplianceCalendar).filter(ComplianceCalendar.id == entry_id).first()
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar entry not found")
    if entry.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")

    if payload.title is not None:
        entry.title = payload.title
    if payload.description is not None:
        entry.description = payload.description
    if payload.due_date is not None:
        entry.due_date = payload.due_date
    if payload.status is not None:
        entry.status = payload.status
        if payload.status == ComplianceStatus.COMPLETED:
            entry.completed_at = datetime.utcnow()
    if payload.priority is not None:
        entry.priority = payload.priority
    if payload.assigned_user_id is not None:
        entry.assigned_user_id = payload.assigned_user_id

    db.commit()
    db.refresh(entry)

    log_audit(
        db,
        user=current_user,
        action="compliance_calendar_updated",
        entity="compliance_calendar",
        entity_id=entry.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"status": entry.status.value},
    )
    return entry
