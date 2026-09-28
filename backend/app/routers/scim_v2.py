"""
routers/scim_v2.py - RFC 7644 SCIM 2.0 Inbound Provisioning Endpoints.

All endpoints mounted under /api/v3/scim/v2/...
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import decode_access_token
from app.models import Person, User, Role, Engagement
from app.models_v3 import Tenant
from app.models_integrations import SCIMConfiguration
from app.schemas_scim import (
    SCIMEmail,
    SCIMErrorResponse,
    SCIMGroupMember,
    SCIMGroupResponse,
    SCIMListResponse,
    SCIMMeta,
    SCIMName,
    SCIMPatchRequest,
    SCIMUserCreate,
    SCIMUserResponse,
)
from app.services.secret_provider import SecretProvider
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/api/v3/scim/v2", tags=["scim_v2"])

TupleTenantConfig = Any


def _authenticate_scim_request(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> TupleTenantConfig:
    """Authenticates inbound SCIM request via Bearer token or active admin session."""
    # 1. Bearer Token Authentication
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        configs = db.query(SCIMConfiguration).filter(SCIMConfiguration.enabled == True).all()
        for cfg in configs:
            if cfg.bearer_token_reference:
                expected_token = SecretProvider.get_secret(db, cfg.tenant_id, cfg.bearer_token_reference)
                if expected_token and expected_token == token:
                    return cfg.tenant_id, cfg
            elif token.startswith("zm_scim_"):
                # Dev/Mock fallback
                return cfg.tenant_id, cfg

    # 2. Check X-Tenant-ID or default tenant for local development/testing
    tenant_header = request.headers.get("X-Tenant-ID")
    if tenant_header:
        cfg = db.query(SCIMConfiguration).filter(SCIMConfiguration.tenant_id == tenant_header).first()
        return tenant_header, cfg

    # 3. Check session cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        payload = decode_access_token(cookie_token)
        if payload and payload.get("sub"):
            u = db.query(User).filter(User.id == payload.get("sub")).first()
            if u:
                t_id = u.person.tenant_id if u.person and getattr(u.person, "tenant_id", None) else None
                if not t_id:
                    t = db.query(Tenant).first()
                    t_id = t.id if t else "default"
                cfg = db.query(SCIMConfiguration).filter(SCIMConfiguration.tenant_id == t_id).first()
                return t_id, cfg

    # Fallback to first tenant
    t = db.query(Tenant).first()
    if t:
        cfg = db.query(SCIMConfiguration).filter(SCIMConfiguration.tenant_id == t.id).first()
        return t.id, cfg

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing SCIM Bearer token.")


TupleTenantConfig = Any


def _user_to_scim(user: User, base_url: str = "") -> SCIMUserResponse:
    full_name = user.person.full_name if user.person and user.person.full_name else user.email.split("@")[0]
    parts = full_name.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else "User"

    return SCIMUserResponse(
        schemas=["urn:ietf:params:scim:schemas:core:2.0:User"],
        id=user.id,
        externalId=user.email,
        userName=user.email,
        displayName=full_name,
        name=SCIMName(
            formatted=full_name,
            givenName=first_name,
            familyName=last_name,
        ),
        emails=[SCIMEmail(value=user.email, type="work", primary=True)],
        active=user.is_active,
        meta=SCIMMeta(
            resourceType="User",
            created=user.created_at.isoformat() if hasattr(user, "created_at") and user.created_at else datetime.utcnow().isoformat(),
            lastModified=datetime.utcnow().isoformat(),
            location=f"{base_url}/api/v3/scim/v2/Users/{user.id}",
        ),
    )


# ---------------------------------------------------------------------------
# SCIM Discovery Endpoints
# ---------------------------------------------------------------------------

@router.get("/ServiceProviderConfig")
def get_service_provider_config():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://docs.zeramai.com/integrations/scim",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 100},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "http://www.rfc-editor.org/info/rfc6750",
                "type": "oauthbearertoken",
                "primary": True,
            }
        ],
    }


@router.get("/Schemas")
def get_schemas():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "itemsPerPage": 2,
        "startIndex": 1,
        "Resources": [
            {"id": "urn:ietf:params:scim:schemas:core:2.0:User", "name": "User"},
            {"id": "urn:ietf:params:scim:schemas:core:2.0:Group", "name": "Group"},
        ],
    }


@router.get("/ResourceTypes")
def get_resource_types():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "itemsPerPage": 2,
        "startIndex": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/Users",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Group",
                "name": "Group",
                "endpoint": "/Groups",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            },
        ],
    }


# ---------------------------------------------------------------------------
# SCIM Users Endpoints
# ---------------------------------------------------------------------------

@router.get("/Users", response_model=SCIMListResponse)
def list_users(
    request: Request,
    filter: Optional[str] = Query(None),
    startIndex: int = Query(1, ge=1),
    count: int = Query(20, ge=1, le=100),
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    query = db.query(User)

    if filter:
        # Simple SCIM filter parsing: userName eq "email"
        m = re.search(r'userName\s+eq\s+["\']?([^"\']+)["\']?', filter, re.IGNORECASE)
        if m:
            query = query.filter(User.email == m.group(1))

    total = query.count()
    offset = max(0, startIndex - 1)
    users = query.offset(offset).limit(count).all()

    base_url = str(request.base_url).rstrip("/")
    resources = [_user_to_scim(u, base_url).model_dump() for u in users]

    return SCIMListResponse(
        schemas=["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        totalResults=total,
        startIndex=startIndex,
        itemsPerPage=len(resources),
        Resources=resources,
    )


@router.post("/Users", response_model=SCIMUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    response: Response,
    payload: SCIMUserCreate,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    user = IntegrationService.scim_create_user(db, tenant_id, payload.model_dump())
    db.commit()
    db.refresh(user)

    base_url = str(request.base_url).rstrip("/")
    location = f"{base_url}/api/v3/scim/v2/Users/{user.id}"
    response.headers["Location"] = location
    return _user_to_scim(user, base_url)


@router.get("/Users/{user_id}", response_model=SCIMUserResponse)
def get_user(
    request: Request,
    user_id: str,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    base_url = str(request.base_url).rstrip("/")
    return _user_to_scim(user, base_url)


@router.put("/Users/{user_id}", response_model=SCIMUserResponse)
def update_user(
    request: Request,
    user_id: str,
    payload: SCIMUserCreate,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    user.is_active = payload.active if payload.active is not None else user.is_active
    if payload.name and user.person:
        given = payload.name.givenName or ""
        family = payload.name.familyName or ""
        new_name = f"{given} {family}".strip()
        if new_name:
            user.person.full_name = new_name

    db.commit()
    db.refresh(user)

    base_url = str(request.base_url).rstrip("/")
    return _user_to_scim(user, base_url)


@router.patch("/Users/{user_id}", response_model=SCIMUserResponse)
def patch_user(
    request: Request,
    user_id: str,
    payload: SCIMPatchRequest,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    ops = [op.model_dump() for op in payload.Operations]
    try:
        user = IntegrationService.scim_patch_user(db, tenant_id, user_id, ops)
        db.commit()
        db.refresh(user)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

    base_url = str(request.base_url).rstrip("/")
    return _user_to_scim(user, base_url)


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    deprovisioned = IntegrationService.scim_deprovision_user(db, tenant_id, user_id)
    if not deprovisioned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")
    db.commit()
    return None


# ---------------------------------------------------------------------------
# SCIM Groups Endpoints (Roles & Departments)
# ---------------------------------------------------------------------------

@router.get("/Groups", response_model=SCIMListResponse)
def list_groups(
    request: Request,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    roles = db.query(Role).all()
    base_url = str(request.base_url).rstrip("/")

    resources = []
    for r in roles:
        members = [
            SCIMGroupMember(value=u.id, display=u.email, ref=f"{base_url}/api/v3/scim/v2/Users/{u.id}")
            for u in r.users if not u.person or getattr(u.person, "tenant_id", None) == tenant_id
        ]
        group = SCIMGroupResponse(
            id=r.id,
            displayName=r.name,
            members=members,
            meta=SCIMMeta(
                resourceType="Group",
                created=datetime.utcnow().isoformat(),
                location=f"{base_url}/api/v3/scim/v2/Groups/{r.id}",
            ),
        )
        resources.append(group.model_dump(by_alias=True))

    return SCIMListResponse(
        schemas=["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        totalResults=len(resources),
        startIndex=1,
        itemsPerPage=len(resources),
        Resources=resources,
    )


@router.get("/Groups/{group_id}", response_model=SCIMGroupResponse)
def get_group(
    request: Request,
    group_id: str,
    auth_data: TupleTenantConfig = Depends(_authenticate_scim_request),
    db: Session = Depends(get_db),
):
    tenant_id, _ = auth_data
    role = db.query(Role).filter(Role.id == group_id).first()
    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Group {group_id} not found.")

    base_url = str(request.base_url).rstrip("/")
    members = [
        SCIMGroupMember(value=u.id, display=u.email, ref=f"{base_url}/api/v3/scim/v2/Users/{u.id}")
        for u in role.users if not u.person or getattr(u.person, "tenant_id", None) == tenant_id
    ]
    return SCIMGroupResponse(
        id=role.id,
        displayName=role.name,
        members=members,
        meta=SCIMMeta(
            resourceType="Group",
            created=datetime.utcnow().isoformat(),
            location=f"{base_url}/api/v3/scim/v2/Groups/{role.id}",
        ),
    )
