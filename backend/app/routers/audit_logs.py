from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.deps import require_permission
from app.models import AuditLog, AuditResult, User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


class AuditLogOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    timestamp: datetime
    user_id: Optional[str]
    action: str
    entity: str
    entity_id: Optional[str]
    result: AuditResult


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    entity: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:view")),
):
    q = db.query(AuditLog)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if action:
        q = q.filter(AuditLog.action == action)
    return q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
