from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.database import get_db
from app.models import (
    AuditLog,
    AuditResult,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserRoleAssociation,
)

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Reads the session from an httpOnly cookie, not an Authorization header
    with a client-stored bearer token. This is a deliberate choice for an
    HR app holding PII: it keeps the token out of reach of XSS-injected JS
    and localStorage, at the cost of needing CSRF protection on state-
    changing requests (enforced via SameSite=strict cookies + a CSRF token
    on POST/PUT/DELETE — wired up in main.py).
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found or inactive")

    return user


def require_roles(*allowed_roles: UserRole):
    """Legacy enum‑based RBAC kept for backward compatibility."""
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return current_user
    return dependency


def has_permission(user: User, permission_code: str, db: Session) -> bool:
    """Check whether ``user`` has the permission identified by ``permission_code``.
    Looks up roles → permissions via the association tables.
    """
    perm = (
        db.query(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAssociation, Role.id == UserRoleAssociation.role_id)
        .filter(UserRoleAssociation.user_id == user.id, Permission.code == permission_code)
        .first()
    )
    return perm is not None


def require_permission(permission_code: str):
    """FastAPI dependency that ensures the current user has ``permission_code``.
    Raises 403 if the permission is missing. Denied attempts are audit-logged.
    """
    def dependency(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not has_permission(current_user, permission_code, db):
            entry = AuditLog(
                user_id=current_user.id,
                action=f"denied:{permission_code}",
                entity="permission",
                entity_id=None,
                result=AuditResult.DENIED,
                metadata_json={"permission": permission_code},
            )
            db.add(entry)
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return current_user
    return dependency

# ---------------------------------------------------------------------------
# Field-level visibility (endpoint-level RBAC alone is not enough — see
# whiteboard note: Hiring Manager can see an evaluation but not a bank
# proof; Finance can see a stipend amount but not an evaluation).
# ---------------------------------------------------------------------------

SENSITIVE_IDENTITY_DOCUMENT_TYPES = {"pan", "aadhaar", "bank_proof", "address_proof"}

ROLES_WITH_SENSITIVE_DOCUMENT_ACCESS = {UserRole.SUPER_ADMIN, UserRole.HR_ADMIN}


def can_access_sensitive_documents(role: UserRole) -> bool:
    return role in ROLES_WITH_SENSITIVE_DOCUMENT_ACCESS


def can_view_evaluations(role: UserRole) -> bool:
    return role in {UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER}


def can_view_stipend(role: UserRole) -> bool:
    return role in {UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.FINANCE}

# ---------------------------------------------------------------------------
# Audit logging — call this from every service method that touches
# sensitive entities, on both success and denial.
# ---------------------------------------------------------------------------

def log_audit(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity: str,
    entity_id: str | None,
    result: AuditResult,
    request: Request | None = None,
    metadata: dict | None = None,
) -> None:
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        ip_address=request.client.host if request and request.client else None,
        result=result,
        metadata_json=metadata,
    )
    db.add(entry)
    db.commit()

# Export authorization helpers from submodule
from .authorization import *
