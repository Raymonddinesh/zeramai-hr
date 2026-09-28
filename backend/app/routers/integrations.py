"""
routers/integrations.py - Module 14: Enterprise IAM & Integration Hub Endpoints.

All endpoints mounted under /api/v3/integrations/...
"""
import uuid
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import AuditResult, User, UserRole
from app.models_v3 import Tenant
from app.models_integrations import (
    APIKey,
    EncryptedSecret,
    IdentityProviderConfig,
    IntegrationConnection,
    IntegrationEvent,
    IntegrationExecutionLog,
    IntegrationProvider,
    OutboxStatus,
    ProviderCategory,
    SCIMConfiguration,
    SCIMProvisioningEvent,
    WebhookDelivery,
    WebhookEndpoint,
)
from app.schemas_integrations import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
    APIKeyRotateResponse,
    IdentityProviderConfigCreate,
    IdentityProviderConfigResponse,
    IdentityProviderConfigUpdate,
    IntegrationConnectionCreate,
    IntegrationConnectionResponse,
    IntegrationConnectionUpdate,
    IntegrationEventResponse,
    IntegrationExecutionLogResponse,
    IntegrationProviderCreate,
    IntegrationProviderResponse,
    IntegrationTestResponse,
    SCIMConfigurationCreate,
    SCIMConfigurationResponse,
    SCIMConfigurationUpdate,
    WebhookDeliveryResponse,
    WebhookEndpointCreate,
    WebhookEndpointResponse,
    WebhookEndpointUpdate,
)
from app.adapters.integration_adapter import get_adapter_for_provider
from app.services.secret_provider import SecretProvider
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/api/v3/integrations", tags=["integrations"])


def _resolve_tenant_id(request: Request, db: Session, user: Optional[User] = None) -> str:
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    if user and user.person and getattr(user.person, "tenant_id", None):
        return user.person.tenant_id
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def _can_read_integrations(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "integrations:read", db)
        or has_permission(user, "integrations:view", db)
    )


def _can_manage_integrations(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "integrations:manage", db)
    )


# ---------------------------------------------------------------------------
# 1. Integration Providers Catalog
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=List[IntegrationProviderResponse])
def list_providers(
    category: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view integration providers.")

    query = db.query(IntegrationProvider)
    if enabled_only:
        query = query.filter(IntegrationProvider.enabled == True)
    if category:
        query = query.filter(IntegrationProvider.category == category.upper())
    return query.order_by(IntegrationProvider.name.asc()).all()


@router.post("/providers", response_model=IntegrationProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: IntegrationProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to register integration providers.")

    existing = db.query(IntegrationProvider).filter(IntegrationProvider.code == payload.code).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Provider with code '{payload.code}' already exists.")

    provider = IntegrationProvider(
        name=payload.name,
        code=payload.code,
        category=payload.category,
        provider_type=payload.provider_type,
        description=payload.description,
        enabled=payload.enabled,
        metadata_json=payload.metadata_json,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


# ---------------------------------------------------------------------------
# 2. Integration Connections
# ---------------------------------------------------------------------------

@router.get("/connections", response_model=List[IntegrationConnectionResponse])
def list_connections(
    request: Request,
    provider_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view integration connections.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(IntegrationConnection).filter(IntegrationConnection.tenant_id == tenant_id)
    if provider_id:
        query = query.filter(IntegrationConnection.provider_id == provider_id)
    if status_filter:
        query = query.filter(IntegrationConnection.status == status_filter.upper())
    
    connections = query.order_by(IntegrationConnection.created_at.desc()).all()
    results = []
    for c in connections:
        resp = IntegrationConnectionResponse.model_validate(c)
        resp.has_credentials = bool(c.credential_reference)
        results.append(resp)
    return results


@router.post("/connections", response_model=IntegrationConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_connection(
    request: Request,
    payload: IntegrationConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create integration connections.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    provider = db.query(IntegrationProvider).filter(IntegrationProvider.id == payload.provider_id).first()
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration provider not found.")

    credential_ref = None
    if payload.secret_value:
        credential_ref = SecretProvider.store_secret(
            db=db,
            tenant_id=tenant_id,
            secret_type="CONNECTION_CREDENTIAL",
            plaintext=payload.secret_value,
            description=f"Credentials for {payload.name}",
        )

    conn = IntegrationConnection(
        tenant_id=tenant_id,
        legal_entity_id=payload.legal_entity_id,
        provider_id=payload.provider_id,
        name=payload.name,
        status="ACTIVE",
        environment=payload.environment,
        configuration_json=payload.configuration_json,
        credential_reference=credential_ref,
        created_by=current_user.id,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    log_audit(
        db,
        user=current_user,
        action="create_connection",
        entity="IntegrationConnection",
        entity_id=conn.id,
        result=AuditResult.SUCCESS,
        request=request,
    )

    resp = IntegrationConnectionResponse.model_validate(conn)
    resp.has_credentials = bool(credential_ref)
    return resp


@router.get("/connections/{connection_id}", response_model=IntegrationConnectionResponse)
def get_connection(
    request: Request,
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.id == connection_id,
        IntegrationConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration connection not found.")

    resp = IntegrationConnectionResponse.model_validate(conn)
    resp.has_credentials = bool(conn.credential_reference)
    return resp


@router.put("/connections/{connection_id}", response_model=IntegrationConnectionResponse)
def update_connection(
    request: Request,
    connection_id: str,
    payload: IntegrationConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.id == connection_id,
        IntegrationConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration connection not found.")

    if payload.name is not None:
        conn.name = payload.name
    if payload.status is not None:
        conn.status = payload.status
    if payload.environment is not None:
        conn.environment = payload.environment
    if payload.configuration_json is not None:
        conn.configuration_json = payload.configuration_json
    if payload.secret_value:
        if conn.credential_reference:
            SecretProvider.update_secret(db, tenant_id, conn.credential_reference, payload.secret_value)
        else:
            conn.credential_reference = SecretProvider.store_secret(
                db, tenant_id, "CONNECTION_CREDENTIAL", payload.secret_value, f"Credentials for {conn.name}"
            )

    conn.updated_by = current_user.id
    db.commit()
    db.refresh(conn)

    resp = IntegrationConnectionResponse.model_validate(conn)
    resp.has_credentials = bool(conn.credential_reference)
    return resp


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    request: Request,
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.id == connection_id,
        IntegrationConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration connection not found.")

    if conn.credential_reference:
        SecretProvider.delete_secret(db, tenant_id, conn.credential_reference)

    db.delete(conn)
    db.commit()
    return None


@router.post("/connections/{connection_id}/test", response_model=IntegrationTestResponse)
def test_connection_endpoint(
    request: Request,
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.id == connection_id,
        IntegrationConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration connection not found.")

    adapter = get_adapter_for_provider(conn.provider.code if conn.provider else "generic_webhook")
    secret = None
    if conn.credential_reference:
        secret = SecretProvider.get_secret(db, tenant_id, conn.credential_reference)

    res = adapter.test_connection(conn.configuration_json or {}, credential=secret)
    if res.get("success"):
        conn.last_success_at = datetime.utcnow()
    else:
        conn.last_failure_at = datetime.utcnow()
    db.commit()

    return IntegrationTestResponse(
        success=res.get("success", False),
        status_code=res.get("status_code", 200),
        latency_ms=res.get("latency_ms", 10),
        message=res.get("message", "Test completed."),
        details=res.get("details"),
    )


# ---------------------------------------------------------------------------
# 3. Enterprise Identity Providers (SSO)
# ---------------------------------------------------------------------------

@router.get("/identity/configs", response_model=List[IdentityProviderConfigResponse])
def list_idp_configs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    configs = db.query(IdentityProviderConfig).filter(IdentityProviderConfig.tenant_id == tenant_id).all()
    results = []
    for c in configs:
        resp = IdentityProviderConfigResponse.model_validate(c)
        resp.has_secret = bool(c.client_secret_reference)
        resp.has_certificate = bool(c.certificate_reference)
        results.append(resp)
    return results


@router.post("/identity/configs", response_model=IdentityProviderConfigResponse, status_code=status.HTTP_201_CREATED)
def create_idp_config(
    request: Request,
    payload: IdentityProviderConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        user_is_super := current_user.role == UserRole.SUPER_ADMIN
        or has_permission(current_user, "integrations:identity:manage", db)
        or _can_manage_integrations(current_user, db)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to manage SSO identity providers.")

    tenant_id = _resolve_tenant_id(request, db, current_user)

    secret_ref = None
    if payload.client_secret:
        secret_ref = SecretProvider.store_secret(
            db, tenant_id, "OIDC_CLIENT_SECRET", payload.client_secret, f"Client secret for {payload.provider_name}"
        )

    cert_ref = None
    if payload.saml_certificate:
        cert_ref = SecretProvider.store_secret(
            db, tenant_id, "SAML_CERTIFICATE", payload.saml_certificate, f"Certificate for {payload.provider_name}"
        )

    config = IdentityProviderConfig(
        tenant_id=tenant_id,
        legal_entity_id=payload.legal_entity_id,
        provider_name=payload.provider_name,
        protocol=payload.protocol.upper(),
        issuer=payload.issuer,
        client_id=payload.client_id,
        client_secret_reference=secret_ref,
        authorization_url=payload.authorization_url,
        token_url=payload.token_url,
        userinfo_url=payload.userinfo_url,
        jwks_url=payload.jwks_url,
        metadata_url=payload.metadata_url,
        saml_metadata=payload.saml_metadata,
        certificate_reference=cert_ref,
        claims_mapping_json=payload.claims_mapping_json,
        enabled=payload.enabled,
        default_provider=payload.default_provider,
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    log_audit(
        db,
        user=current_user,
        action="create_idp_config",
        entity="IdentityProviderConfig",
        entity_id=config.id,
        result=AuditResult.SUCCESS,
        request=request,
    )

    resp = IdentityProviderConfigResponse.model_validate(config)
    resp.has_secret = bool(secret_ref)
    resp.has_certificate = bool(cert_ref)
    return resp


@router.get("/identity/configs/{config_id}", response_model=IdentityProviderConfigResponse)
def get_idp_config(
    request: Request,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    config = db.query(IdentityProviderConfig).filter(
        IdentityProviderConfig.id == config_id,
        IdentityProviderConfig.tenant_id == tenant_id,
    ).first()
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Identity Provider config not found.")

    resp = IdentityProviderConfigResponse.model_validate(config)
    resp.has_secret = bool(config.client_secret_reference)
    resp.has_certificate = bool(config.certificate_reference)
    return resp


@router.delete("/identity/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_idp_config(
    request: Request,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    config = db.query(IdentityProviderConfig).filter(
        IdentityProviderConfig.id == config_id,
        IdentityProviderConfig.tenant_id == tenant_id,
    ).first()
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Identity Provider config not found.")

    if config.client_secret_reference:
        SecretProvider.delete_secret(db, tenant_id, config.client_secret_reference)
    if config.certificate_reference:
        SecretProvider.delete_secret(db, tenant_id, config.certificate_reference)

    db.delete(config)
    db.commit()
    return None


@router.post("/identity/configs/{config_id}/test", response_model=IntegrationTestResponse)
def test_idp_config(
    request: Request,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    config = db.query(IdentityProviderConfig).filter(
        IdentityProviderConfig.id == config_id,
        IdentityProviderConfig.tenant_id == tenant_id,
    ).first()
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Identity Provider config not found.")

    # Validation of SSO endpoints
    valid = bool(config.issuer or config.authorization_url or config.saml_metadata)
    return IntegrationTestResponse(
        success=valid,
        status_code=200 if valid else 400,
        latency_ms=12,
        message=f"SSO Identity Provider '{config.provider_name}' configuration validated successfully." if valid else "Missing endpoint configuration.",
        details={"protocol": config.protocol, "issuer": config.issuer},
    )


# ---------------------------------------------------------------------------
# 4. SCIM Configuration & Events
# ---------------------------------------------------------------------------

@router.get("/scim/config", response_model=Optional[SCIMConfigurationResponse])
def get_scim_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    scim = db.query(SCIMConfiguration).filter(SCIMConfiguration.tenant_id == tenant_id).first()
    if not scim:
        return None

    resp = SCIMConfigurationResponse.model_validate(scim)
    resp.has_bearer_token = bool(scim.bearer_token_reference)
    return resp


@router.post("/scim/config", response_model=SCIMConfigurationResponse)
def save_scim_config(
    request: Request,
    payload: SCIMConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to manage SCIM configuration.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    scim = db.query(SCIMConfiguration).filter(SCIMConfiguration.tenant_id == tenant_id).first()

    token_ref = None
    if payload.bearer_token:
        token_ref = SecretProvider.store_secret(
            db, tenant_id, "SCIM_BEARER_TOKEN", payload.bearer_token, "SCIM Inbound Bearer Token"
        )

    if not scim:
        scim = SCIMConfiguration(
            tenant_id=tenant_id,
            legal_entity_id=payload.legal_entity_id,
            provider_name=payload.provider_name,
            base_url=payload.base_url,
            bearer_token_reference=token_ref,
            enabled=payload.enabled,
            auto_provision=payload.auto_provision,
            auto_deprovision=payload.auto_deprovision,
            auto_update=payload.auto_update,
        )
        db.add(scim)
    else:
        scim.provider_name = payload.provider_name
        scim.base_url = payload.base_url
        if token_ref:
            scim.bearer_token_reference = token_ref
        scim.enabled = payload.enabled
        scim.auto_provision = payload.auto_provision
        scim.auto_deprovision = payload.auto_deprovision
        scim.auto_update = payload.auto_update

    db.commit()
    db.refresh(scim)

    resp = SCIMConfigurationResponse.model_validate(scim)
    resp.has_bearer_token = bool(scim.bearer_token_reference)
    return resp


@router.post("/scim/config/rotate-token")
def rotate_scim_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    scim = db.query(SCIMConfiguration).filter(SCIMConfiguration.tenant_id == tenant_id).first()
    if not scim:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SCIM is not configured for this tenant.")

    new_token = f"zm_scim_{secrets.token_urlsafe(32)}"
    if scim.bearer_token_reference:
        SecretProvider.update_secret(db, tenant_id, scim.bearer_token_reference, new_token)
    else:
        scim.bearer_token_reference = SecretProvider.store_secret(
            db, tenant_id, "SCIM_BEARER_TOKEN", new_token, "SCIM Inbound Bearer Token"
        )
    db.commit()

    return {
        "message": "SCIM bearer token rotated successfully. Store this token securely; it will not be shown again.",
        "bearer_token": new_token,
    }


@router.get("/scim/events")
def list_scim_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    events = (
        db.query(SCIMProvisioningEvent)
        .filter(SCIMProvisioningEvent.tenant_id == tenant_id)
        .order_by(SCIMProvisioningEvent.processed_at.desc())
        .limit(limit)
        .all()
    )
    return events


# ---------------------------------------------------------------------------
# 5. API Key Management
# ---------------------------------------------------------------------------

@router.get("/api-keys", response_model=List[APIKeyResponse])
def list_api_keys(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view API keys.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    keys = db.query(APIKey).filter(APIKey.tenant_id == tenant_id).order_by(APIKey.created_at.desc()).all()
    return keys


@router.post("/api-keys", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: Request,
    payload: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        current_user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(current_user, "integrations:api_keys:manage", db)
        or _can_manage_integrations(current_user, db)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to generate API keys.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    key_record, raw_key = IntegrationService.create_api_key(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
    )
    db.commit()

    log_audit(
        db,
        user=current_user,
        action="create_api_key",
        entity="APIKey",
        entity_id=key_record.id,
        result=AuditResult.SUCCESS,
        request=request,
    )

    return APIKeyCreatedResponse(
        id=key_record.id,
        name=key_record.name,
        key_prefix=key_record.key_prefix,
        raw_api_key=raw_key,
        scopes=key_record.scopes,
        expires_at=key_record.expires_at,
        created_at=key_record.created_at,
    )


@router.post("/api-keys/{key_id}/rotate", response_model=APIKeyRotateResponse)
def rotate_api_key(
    request: Request,
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to rotate API keys.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    try:
        key_record, new_raw_key = IntegrationService.rotate_api_key(db, tenant_id, key_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

    log_audit(
        db,
        user=current_user,
        action="rotate_api_key",
        entity="APIKey",
        entity_id=key_record.id,
        result=AuditResult.SUCCESS,
        request=request,
    )

    return APIKeyRotateResponse(
        id=key_record.id,
        new_raw_api_key=new_raw_key,
        key_prefix=key_record.key_prefix,
        rotated_at=datetime.utcnow(),
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    request: Request,
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to revoke API keys.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    revoked = IntegrationService.revoke_api_key(db, tenant_id, key_id)
    if not revoked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API Key not found.")
    db.commit()

    log_audit(
        db,
        user=current_user,
        action="revoke_api_key",
        entity="APIKey",
        entity_id=key_id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return None


# ---------------------------------------------------------------------------
# 6. Webhooks Subscriptions
# ---------------------------------------------------------------------------

@router.get("/webhooks", response_model=List[WebhookEndpointResponse])
def list_webhooks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    webhooks = db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == tenant_id).all()
    return webhooks


@router.post("/webhooks", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    request: Request,
    payload: WebhookEndpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to configure webhooks.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    secret_value = payload.secret or f"whsec_{secrets.token_hex(24)}"
    secret_ref = SecretProvider.store_secret(
        db=db,
        tenant_id=tenant_id,
        secret_type="WEBHOOK_SIGNING_SECRET",
        plaintext=secret_value,
        description=f"Signing secret for {payload.name}",
    )

    endpoint = WebhookEndpoint(
        tenant_id=tenant_id,
        name=payload.name,
        url=payload.url,
        secret_reference=secret_ref,
        enabled=True,
        subscribed_events=payload.subscribed_events,
        retry_policy=payload.retry_policy or {"max_retries": 3, "backoff_seconds": 30},
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    log_audit(
        db,
        user=current_user,
        action="create_webhook",
        entity="WebhookEndpoint",
        entity_id=endpoint.id,
        result=AuditResult.SUCCESS,
        request=request,
    )
    return endpoint


@router.get("/webhooks/{endpoint_id}", response_model=WebhookEndpointResponse)
def get_webhook(
    request: Request,
    endpoint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.tenant_id == tenant_id,
    ).first()
    if not endpoint:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook endpoint not found.")
    return endpoint


@router.put("/webhooks/{endpoint_id}", response_model=WebhookEndpointResponse)
def update_webhook(
    request: Request,
    endpoint_id: str,
    payload: WebhookEndpointUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.tenant_id == tenant_id,
    ).first()
    if not endpoint:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook endpoint not found.")

    if payload.name is not None:
        endpoint.name = payload.name
    if payload.url is not None:
        endpoint.url = payload.url
    if payload.subscribed_events is not None:
        endpoint.subscribed_events = payload.subscribed_events
    if payload.enabled is not None:
        endpoint.enabled = payload.enabled
    if payload.retry_policy is not None:
        endpoint.retry_policy = payload.retry_policy
    if payload.secret:
        SecretProvider.update_secret(db, tenant_id, endpoint.secret_reference, payload.secret)

    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.delete("/webhooks/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    request: Request,
    endpoint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.tenant_id == tenant_id,
    ).first()
    if not endpoint:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook endpoint not found.")

    if endpoint.secret_reference:
        SecretProvider.delete_secret(db, tenant_id, endpoint.secret_reference)

    db.delete(endpoint)
    db.commit()
    return None


@router.get("/webhooks/{endpoint_id}/deliveries", response_model=List[WebhookDeliveryResponse])
def list_webhook_deliveries(
    request: Request,
    endpoint_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    deliveries = (
        db.query(WebhookDelivery)
        .filter(
            WebhookDelivery.endpoint_id == endpoint_id,
            WebhookDelivery.tenant_id == tenant_id,
        )
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
        .all()
    )
    return deliveries


@router.post("/webhooks/{endpoint_id}/test", response_model=IntegrationTestResponse)
def test_webhook(
    request: Request,
    endpoint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.tenant_id == tenant_id,
    ).first()
    if not endpoint:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook endpoint not found.")

    delivery = IntegrationService.dispatch_webhook_delivery(
        db=db,
        tenant_id=tenant_id,
        endpoint=endpoint,
        event_type="test.ping",
        event_id=f"test_{uuid.uuid4().hex[:8]}",
        payload={"message": "Zeramai HR test ping", "timestamp": datetime.utcnow().isoformat()},
    )
    db.commit()

    return IntegrationTestResponse(
        success=delivery.status == "SUCCESS",
        status_code=delivery.response_status or 200,
        latency_ms=delivery.response_time_ms or 10,
        message=f"Dispatched test ping webhook to {endpoint.url}.",
        details={"delivery_id": delivery.id, "payload_hash": delivery.payload_hash},
    )


# ---------------------------------------------------------------------------
# 7. Transactional Outbox & Telemetry Execution Logs
# ---------------------------------------------------------------------------

@router.get("/outbox", response_model=List[IntegrationEventResponse])
def list_outbox_events(
    request: Request,
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(IntegrationEvent).filter(IntegrationEvent.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(IntegrationEvent.status == status_filter.upper())
    return query.order_by(IntegrationEvent.created_at.desc()).limit(limit).all()


@router.post("/outbox/process")
def process_outbox_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    result = IntegrationService.process_outbox(db, tenant_id, limit=limit)
    db.commit()
    return result


@router.get("/logs", response_model=List[IntegrationExecutionLogResponse])
def list_execution_logs(
    request: Request,
    connection_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_integrations(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(IntegrationExecutionLog).filter(IntegrationExecutionLog.tenant_id == tenant_id)
    if connection_id:
        query = query.filter(IntegrationExecutionLog.connection_id == connection_id)
    return query.order_by(IntegrationExecutionLog.created_at.desc()).limit(limit).all()
