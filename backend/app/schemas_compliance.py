from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from app.models_compliance import ComplianceType, ComplianceStatus


class ComplianceTaskCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    legal_entity_id: Optional[str] = None
    compliance_type: ComplianceType = ComplianceType.STATUTORY
    authority: Optional[str] = None
    title: str
    description: Optional[str] = None
    period: Optional[str] = None
    due_date: date
    priority: Optional[int] = 1
    assigned_user_id: Optional[str] = None
    evidence_document_id: Optional[str] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    reminder_config: Optional[Dict[str, Any]] = None


class ComplianceTaskUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Optional[ComplianceStatus] = None
    priority: Optional[int] = None
    assigned_user_id: Optional[str] = None
    evidence_document_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    description: Optional[str] = None


class ComplianceTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    compliance_type: ComplianceType
    authority: Optional[str] = None
    title: str
    description: Optional[str] = None
    period: Optional[str] = None
    due_date: date
    status: ComplianceStatus
    priority: Optional[int] = 1
    assigned_user_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    evidence_document_id: Optional[str] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    reminder_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ComplianceCalendarCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    legal_entity_id: Optional[str] = None
    compliance_type: ComplianceType = ComplianceType.STATUTORY
    authority: Optional[str] = None
    title: str
    description: Optional[str] = None
    period: Optional[str] = None
    due_date: date
    priority: Optional[int] = 1
    assigned_user_id: Optional[str] = None
    reminder_config: Optional[Dict[str, Any]] = None


class ComplianceCalendarUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[ComplianceStatus] = None
    priority: Optional[int] = None
    assigned_user_id: Optional[str] = None
    completed_at: Optional[datetime] = None


class ComplianceCalendarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    compliance_type: ComplianceType
    authority: Optional[str] = None
    title: str
    description: Optional[str] = None
    period: Optional[str] = None
    due_date: date
    status: ComplianceStatus
    priority: Optional[int] = 1
    assigned_user_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    evidence_document_id: Optional[str] = None
    reminder_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ComplianceDashboardOut(BaseModel):
    upcoming_deadlines_count: int
    overdue_count: int
    pending_filings_count: int
    completed_tasks_count: int
    active_registrations_count: int
    tasks: List[ComplianceTaskOut]
    calendar_events: List[ComplianceCalendarOut]
