from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, log_audit
from app.models import User, UserRole, AuditResult

router = APIRouter(prefix="/api/scim/v2", tags=["scim"])


@router.get("/Users")
def list_scim_users(
    startIndex: int = 1,
    count: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:view")),
):
    """SCIM 2.0 RFC 7644 User Listing Endpoint."""
    users = db.query(User).offset(startIndex - 1).limit(count).all()
    resources = [
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": u.id,
            "userName": u.email,
            "emails": [{"value": u.email, "primary": True}],
            "active": u.is_active,
            "meta": {"resourceType": "User", "created": u.created_at.isoformat()}
        }
        for u in users
    ]
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "startIndex": startIndex,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


@router.get("/Users/{user_id}")
def get_scim_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:view")),
):
    """SCIM 2.0 Get User Endpoint."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": u.id,
        "userName": u.email,
        "emails": [{"value": u.email, "primary": True}],
        "active": u.is_active,
        "meta": {"resourceType": "User", "created": u.created_at.isoformat()}
    }
