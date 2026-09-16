"""Phase 14 - Enterprise IAM & Security Controls: Policies, Active Sessions, Revocation."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import hashlib

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v10 import SecurityPolicy, ActiveSession

router = APIRouter(prefix="/api/security", tags=["security"])


class SecurityPolicyUpdate(BaseModel):
    min_password_length: int = 8
    require_uppercase: bool = True
    require_numbers: bool = True
    require_special_char: bool = True
    session_timeout_minutes: int = 60
    max_failed_logins: int = 5
    ip_whitelist_enabled: bool = False
    ip_whitelist_json: list[str] = []


class SessionOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    user_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_revoked: bool
    created_at: datetime
    expires_at: datetime


@router.get("/policy")
def get_security_policy(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:view")),
):
    pol = db.query(SecurityPolicy).first()
    if not pol:
        pol = SecurityPolicy()
        db.add(pol)
        db.commit()
        db.refresh(pol)
    return {
        "min_password_length": pol.min_password_length,
        "require_uppercase": pol.require_uppercase,
        "require_numbers": pol.require_numbers,
        "require_special_char": pol.require_special_char,
        "session_timeout_minutes": pol.session_timeout_minutes,
        "max_failed_logins": pol.max_failed_logins,
        "ip_whitelist_enabled": pol.ip_whitelist_enabled,
        "ip_whitelist": pol.ip_whitelist_json or [],
    }


@router.put("/policy")
def update_security_policy(
    payload: SecurityPolicyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    pol = db.query(SecurityPolicy).first()
    if not pol:
        pol = SecurityPolicy()
        db.add(pol)

    pol.min_password_length = payload.min_password_length
    pol.require_uppercase = payload.require_uppercase
    pol.require_numbers = payload.require_numbers
    pol.require_special_char = payload.require_special_char
    pol.session_timeout_minutes = payload.session_timeout_minutes
    pol.max_failed_logins = payload.max_failed_logins
    pol.ip_whitelist_enabled = payload.ip_whitelist_enabled
    pol.ip_whitelist_json = payload.ip_whitelist_json

    db.commit()
    log_audit(db, user=current_user, action="security_policy_updated", entity="security_policy",
              entity_id=pol.id, result=AuditResult.SUCCESS, request=request)
    return {"message": "Security policy updated successfully"}


@router.post("/sessions/register")
def register_session(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registers an active session record for tracking & remote logout."""
    token_str = f"{current_user.id}-{datetime.utcnow().timestamp()}"
    token_hash = hashlib.sha256(token_str.encode()).hexdigest()

    session_rec = ActiveSession(
        user_id=current_user.id,
        session_token_hash=token_hash,
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "Unknown"),
        expires_at=datetime.utcnow() + timedelta(hours=8),
    )
    db.add(session_rec)
    db.commit()
    db.refresh(session_rec)
    return {"session_id": session_rec.id, "user_id": session_rec.user_id, "expires_at": session_rec.expires_at.isoformat()}


@router.get("/sessions", response_model=list[SessionOut])
def list_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id,
        ActiveSession.is_revoked == False,
    ).order_by(ActiveSession.created_at.desc()).all()


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = db.query(ActiveSession).filter(ActiveSession.id == session_id).first()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    sess.is_revoked = True
    db.commit()
    log_audit(db, user=current_user, action="session_revoked", entity="active_session",
              entity_id=session_id, result=AuditResult.SUCCESS, request=request)
    return {"session_id": session_id, "revoked": True}
