"""
Pydantic schemas for Module 14: Enterprise IAM & Integration Hub.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Integration Providers & Connections
# ---------------------------------------------------------------------------

class IntegrationProviderBase(BaseModel):
    name: str
    code: str
    category: str
    provider_type: str
    description: Optional[str] = None
    enabled: bool = True
    metadata_json: Optional[Dict[str, Any]] = None


class IntegrationProviderCreate(IntegrationProviderBase):
    pass


class IntegrationProviderResponse(IntegrationProviderBase):
    id: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationConnectionCreate(BaseModel):
    provider_id: str
    legal_entity_id: Optional[str] = None
    name: str
    environment: str = "PRODUCTION"
    configuration_json: Optional[Dict[str, Any]] = None
    secret_value: Optional[str] = None  # Raw plaintext secret provided during creation; stored via SecretProvider


class IntegrationConnectionUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    environment: Optional[str] = None
    configuration_json: Optional[Dict[str, Any]] = None
    secret_value: Optional[str] = None  # If updating credential


class IntegrationConnectionResponse(BaseModel):
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    provider_id: str
    name: str
    status: str
    environment: str
    configuration_json: Optional[Dict[str, Any]] = None
    has_credentials: bool = False
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 2. SSO / Identity Provider Configs
# ---------------------------------------------------------------------------

class IdentityProviderConfigCreate(BaseModel):
    legal_entity_id: Optional[str] = None
    provider_name: str
    protocol: str = "OIDC"  # OIDC or SAML
    
    # OIDC fields
    issuer: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None  # Stored encrypted
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    jwks_url: Optional[str] = None
    metadata_url: Optional[str] = None

    # SAML fields
    saml_metadata: Optional[str] = None
    saml_certificate: Optional[str] = None  # Stored encrypted

    claims_mapping_json: Optional[Dict[str, str]] = None
    enabled: bool = True
    default_provider: bool = False


class IdentityProviderConfigUpdate(BaseModel):
    provider_name: Optional[str] = None
    protocol: Optional[str] = None
    issuer: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    jwks_url: Optional[str] = None
    metadata_url: Optional[str] = None
    saml_metadata: Optional[str] = None
    saml_certificate: Optional[str] = None
    claims_mapping_json: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None
    default_provider: Optional[bool] = None


class IdentityProviderConfigResponse(BaseModel):
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    provider_name: str
    protocol: str
    issuer: Optional[str] = None
    client_id: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    jwks_url: Optional[str] = None
    metadata_url: Optional[str] = None
    has_secret: bool = False
    has_certificate: bool = False
    claims_mapping_json: Optional[Dict[str, str]] = None
    enabled: bool
    default_provider: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 3. SCIM Configuration
# ---------------------------------------------------------------------------

class SCIMConfigurationCreate(BaseModel):
    legal_entity_id: Optional[str] = None
    provider_name: str
    base_url: Optional[str] = None
    bearer_token: Optional[str] = None  # Encrypted via SecretProvider
    enabled: bool = True
    auto_provision: bool = True
    auto_deprovision: bool = True
    auto_update: bool = True


class SCIMConfigurationUpdate(BaseModel):
    provider_name: Optional[str] = None
    base_url: Optional[str] = None
    bearer_token: Optional[str] = None
    enabled: Optional[bool] = None
    auto_provision: Optional[bool] = None
    auto_deprovision: Optional[bool] = None
    auto_update: Optional[bool] = None
    status: Optional[str] = None


class SCIMConfigurationResponse(BaseModel):
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    provider_name: str
    base_url: Optional[str] = None
    has_bearer_token: bool = False
    enabled: bool
    auto_provision: bool
    auto_deprovision: bool
    auto_update: bool
    status: str
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 4. API Keys
# ---------------------------------------------------------------------------

class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None  # None = never expires


class APIKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    raw_api_key: str  # Only returned ONCE upon creation!
    scopes: List[str]
    expires_at: Optional[datetime] = None
    created_at: datetime


class APIKeyResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    key_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyRotateResponse(BaseModel):
    id: str
    new_raw_api_key: str
    key_prefix: str
    rotated_at: datetime


# ---------------------------------------------------------------------------
# 5. Webhooks
# ---------------------------------------------------------------------------

class WebhookEndpointCreate(BaseModel):
    name: str
    url: str
    subscribed_events: List[str]
    secret: Optional[str] = None  # If not passed, generated automatically
    retry_policy: Optional[Dict[str, Any]] = None


class WebhookEndpointUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    subscribed_events: Optional[List[str]] = None
    enabled: Optional[bool] = None
    secret: Optional[str] = None
    retry_policy: Optional[Dict[str, Any]] = None


class WebhookEndpointResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    url: str
    enabled: bool
    subscribed_events: List[str]
    retry_policy: Optional[Dict[str, Any]] = None
    last_delivery_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    id: str
    tenant_id: str
    endpoint_id: str
    event_type: str
    event_id: str
    attempt_count: int
    status: str
    response_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    last_error: Optional[str] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 6. Outbox & Logs
# ---------------------------------------------------------------------------

class IntegrationEventResponse(BaseModel):
    id: str
    tenant_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    status: str
    retry_count: int
    available_at: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationExecutionLogResponse(BaseModel):
    id: str
    tenant_id: str
    connection_id: Optional[str] = None
    event_type: str
    direction: str
    status: str
    request_reference: Optional[str] = None
    response_reference: Optional[str] = None
    duration_ms: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationTestResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    latency_ms: int
    message: str
    details: Optional[Dict[str, Any]] = None
