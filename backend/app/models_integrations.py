"""
models_integrations.py - Module 14: Enterprise IAM & Integration Hub Data Models.

Canonical models for:
- EncryptedSecret
- IntegrationProvider
- IntegrationConnection
- IdentityProviderConfig
- SCIMConfiguration
- SCIMProvisioningEvent
- APIKey
- WebhookEndpoint
- WebhookDelivery
- IntegrationEvent (Transactional Outbox)
- IntegrationExecutionLog
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ProviderCategory(str, enum.Enum):
    IDENTITY = "IDENTITY"
    PAYROLL = "PAYROLL"
    ACCOUNTING = "ACCOUNTING"
    COMMUNICATION = "COMMUNICATION"
    STORAGE = "STORAGE"
    ANALYTICS = "ANALYTICS"
    HR_SERVICE = "HR_SERVICE"


class ConnectionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"
    PENDING = "PENDING"


class ConnectionEnvironment(str, enum.Enum):
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class SSOProtocol(str, enum.Enum):
    OIDC = "OIDC"
    SAML = "SAML"


class SCIMEventType(str, enum.Enum):
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DEPROVISIONED = "USER_DEPROVISIONED"
    GROUP_CREATED = "GROUP_CREATED"
    GROUP_UPDATED = "GROUP_UPDATED"
    GROUP_DELETED = "GROUP_DELETED"


class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class WebhookDeliveryStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class ExecutionDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


# ---------------------------------------------------------------------------
# 1. Encrypted Secrets Vault Model
# ---------------------------------------------------------------------------

class EncryptedSecret(Base):
    """Secure encrypted secret storage. Never stores raw plaintext secrets."""
    __tablename__ = "encrypted_secrets"

    id = Column(String, primary_key=True, default=gen_uuid)  # secret_reference
    tenant_id = Column(String, nullable=False, index=True)
    secret_type = Column(String(50), nullable=False)  # API_KEY, WEBHOOK_SECRET, CLIENT_SECRET, CERTIFICATE
    ciphertext = Column(Text, nullable=False)
    key_version = Column(Integer, default=1, nullable=False)
    description = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 2. Integration Catalog & Connections
# ---------------------------------------------------------------------------

class IntegrationProvider(Base):
    """Integration provider registry/catalog."""
    __tablename__ = "integration_providers"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=True, index=True)  # Nullable for global catalog
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g., 'entra_id', 'google_workspace', 'slack'
    category = Column(String(50), nullable=False, default=ProviderCategory.IDENTITY.value)
    provider_type = Column(String(50), nullable=False)  # SSO, SCIM, WEBHOOK, REST_API
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    connections = relationship("IntegrationConnection", back_populates="provider", cascade="all, delete-orphan")


class IntegrationConnection(Base):
    """Configured external system connection instance for a tenant."""
    __tablename__ = "integration_connections"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    provider_id = Column(String, ForeignKey("integration_providers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default=ConnectionStatus.PENDING.value, index=True)
    environment = Column(String(50), nullable=False, default=ConnectionEnvironment.PRODUCTION.value)
    configuration_json = Column(JSON, nullable=True)  # non-sensitive configuration parameters
    credential_reference = Column(String, ForeignKey("encrypted_secrets.id"), nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    provider = relationship("IntegrationProvider", back_populates="connections")
    execution_logs = relationship("IntegrationExecutionLog", back_populates="connection", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 3. Enterprise Identity Provider (SSO) Configuration
# ---------------------------------------------------------------------------

class IdentityProviderConfig(Base):
    """SAML 2.0 / OIDC Identity Provider Configuration."""
    __tablename__ = "identity_provider_configs"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    provider_name = Column(String(255), nullable=False)
    protocol = Column(String(50), nullable=False, default=SSOProtocol.OIDC.value)  # OIDC or SAML
    
    # OIDC attributes
    issuer = Column(String(500), nullable=True)
    client_id = Column(String(255), nullable=True)
    client_secret_reference = Column(String, ForeignKey("encrypted_secrets.id"), nullable=True)
    authorization_url = Column(String(500), nullable=True)
    token_url = Column(String(500), nullable=True)
    userinfo_url = Column(String(500), nullable=True)
    jwks_url = Column(String(500), nullable=True)
    metadata_url = Column(String(500), nullable=True)
    
    # SAML attributes
    saml_metadata = Column(Text, nullable=True)
    certificate_reference = Column(String, ForeignKey("encrypted_secrets.id"), nullable=True)
    
    # Behavior
    claims_mapping_json = Column(JSON, nullable=True)  # {"email": "email", "name": "display_name", "role": "roles"}
    enabled = Column(Boolean, default=True, nullable=False)
    default_provider = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 4. SCIM 2.0 Configuration & Provisioning Events
# ---------------------------------------------------------------------------

class SCIMConfiguration(Base):
    """SCIM 2.0 Provisioning configuration per tenant."""
    __tablename__ = "scim_configurations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    provider_name = Column(String(255), nullable=False)
    base_url = Column(String(500), nullable=True)
    bearer_token_reference = Column(String, ForeignKey("encrypted_secrets.id"), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    auto_provision = Column(Boolean, default=True, nullable=False)
    auto_deprovision = Column(Boolean, default=True, nullable=False)
    auto_update = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SCIMProvisioningEvent(Base):
    """Audit and execution trail of inbound SCIM 2.0 requests."""
    __tablename__ = "scim_provisioning_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # USER_CREATED, USER_UPDATED, USER_DEPROVISIONED
    external_subject = Column(String(255), nullable=False)  # externalId / userName
    person_id = Column(String, ForeignKey("persons.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    payload_hash = Column(String(128), nullable=False)
    status = Column(String(50), nullable=False, default="SUCCESS")  # SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 5. API Key Management
# ---------------------------------------------------------------------------

class APIKey(Base):
    """Hashed and scoped API keys for server-to-server integrations."""
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False, index=True)  # e.g., 'zm_live_abc1'
    key_hash = Column(String(128), nullable=False, unique=True, index=True)  # SHA-256
    scopes = Column(JSON, nullable=False)  # ["employee:read", "payroll:read"]
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# ---------------------------------------------------------------------------
# 6. Webhook Platform
# ---------------------------------------------------------------------------

class WebhookEndpoint(Base):
    """Configured external webhook subscriptions."""
    __tablename__ = "webhook_endpoints"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    secret_reference = Column(String, ForeignKey("encrypted_secrets.id"), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    subscribed_events = Column(JSON, nullable=False)  # ["employee.created", "leave.approved"]
    retry_policy = Column(JSON, nullable=True)  # {"max_retries": 3, "backoff_seconds": 60}
    last_delivery_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deliveries = relationship("WebhookDelivery", back_populates="endpoint", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Audit and delivery record of outbound webhooks."""
    __tablename__ = "webhook_deliveries"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    endpoint_id = Column(String, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    event_id = Column(String, nullable=False, index=True)
    payload_hash = Column(String(128), nullable=False)
    attempt_count = Column(Integer, default=1, nullable=False)
    status = Column(String(50), nullable=False, default=WebhookDeliveryStatus.SUCCESS.value)
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")


# ---------------------------------------------------------------------------
# 7. Transactional Outbox (Integration Events)
# ---------------------------------------------------------------------------

class IntegrationEvent(Base):
    """Transactional Outbox for reliable, asynchronous integration event delivery."""
    __tablename__ = "integration_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # employee.created, employee.offboarded
    aggregate_type = Column(String(50), nullable=False)  # Employee, Leave, Payroll, Exit
    aggregate_id = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default=OutboxStatus.PENDING.value, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    available_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# ---------------------------------------------------------------------------
# 8. Integration Execution History Logs
# ---------------------------------------------------------------------------

class IntegrationExecutionLog(Base):
    """History and performance telemetry for external integration calls."""
    __tablename__ = "integration_execution_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    connection_id = Column(String, ForeignKey("integration_connections.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False)
    direction = Column(String(50), nullable=False, default=ExecutionDirection.OUTBOUND.value)
    status = Column(String(50), nullable=False, default="SUCCESS")
    request_reference = Column(String(255), nullable=True)
    response_reference = Column(String(255), nullable=True)
    duration_ms = Column(Integer, default=0, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    connection = relationship("IntegrationConnection", back_populates="execution_logs")
