"""module14 enterprise iam and integration hub models

Revision ID: f891d3401c2b
Revises: e762c2199b1a
Create Date: 2026-09-28 10:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f891d3401c2b'
down_revision: Union[str, Sequence[str], None] = 'e762c2199b1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. encrypted_secrets
    op.create_table(
        'encrypted_secrets',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('secret_type', sa.String(length=50), nullable=False),
        sa.Column('ciphertext', sa.Text(), nullable=False),
        sa.Column('key_version', sa.Integer(), nullable=False, default=1),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 2. integration_providers
    op.create_table(
        'integration_providers',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=True, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 3. integration_connections
    op.create_table(
        'integration_connections',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('provider_id', sa.String(), sa.ForeignKey('integration_providers.id'), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, index=True),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('configuration_json', sa.JSON(), nullable=True),
        sa.Column('credential_reference', sa.String(), sa.ForeignKey('encrypted_secrets.id'), nullable=True),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('updated_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 4. identity_provider_configs
    op.create_table(
        'identity_provider_configs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('provider_name', sa.String(length=255), nullable=False),
        sa.Column('protocol', sa.String(length=50), nullable=False),
        sa.Column('issuer', sa.String(length=500), nullable=True),
        sa.Column('client_id', sa.String(length=255), nullable=True),
        sa.Column('client_secret_reference', sa.String(), sa.ForeignKey('encrypted_secrets.id'), nullable=True),
        sa.Column('authorization_url', sa.String(length=500), nullable=True),
        sa.Column('token_url', sa.String(length=500), nullable=True),
        sa.Column('userinfo_url', sa.String(length=500), nullable=True),
        sa.Column('jwks_url', sa.String(length=500), nullable=True),
        sa.Column('metadata_url', sa.String(length=500), nullable=True),
        sa.Column('saml_metadata', sa.Text(), nullable=True),
        sa.Column('certificate_reference', sa.String(), sa.ForeignKey('encrypted_secrets.id'), nullable=True),
        sa.Column('claims_mapping_json', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('default_provider', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 5. scim_configurations
    op.create_table(
        'scim_configurations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('provider_name', sa.String(length=255), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('bearer_token_reference', sa.String(), sa.ForeignKey('encrypted_secrets.id'), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('auto_provision', sa.Boolean(), nullable=False, default=True),
        sa.Column('auto_deprovision', sa.Boolean(), nullable=False, default=True),
        sa.Column('auto_update', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 6. scim_provisioning_events
    op.create_table(
        'scim_provisioning_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('external_subject', sa.String(length=255), nullable=False),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('payload_hash', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 7. api_keys
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=False, index=True),
        sa.Column('key_hash', sa.String(length=128), nullable=False, unique=True, index=True),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )

    # 8. webhook_endpoints
    op.create_table(
        'webhook_endpoints',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('secret_reference', sa.String(), sa.ForeignKey('encrypted_secrets.id'), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('subscribed_events', sa.JSON(), nullable=False),
        sa.Column('retry_policy', sa.JSON(), nullable=True),
        sa.Column('last_delivery_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 9. webhook_deliveries
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('endpoint_id', sa.String(), sa.ForeignKey('webhook_endpoints.id'), nullable=False, index=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False, index=True),
        sa.Column('payload_hash', sa.String(length=128), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False, default=1),
        sa.Column('status', sa.String(length=50), nullable=False, default='SUCCESS'),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )

    # 10. integration_events (Transactional Outbox)
    op.create_table(
        'integration_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('event_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('aggregate_type', sa.String(length=50), nullable=False),
        sa.Column('aggregate_id', sa.String(), nullable=False, index=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, index=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('available_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )

    # 11. integration_execution_logs
    op.create_table(
        'integration_execution_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('connection_id', sa.String(), sa.ForeignKey('integration_connections.id'), nullable=True, index=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('direction', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('request_reference', sa.String(length=255), nullable=True),
        sa.Column('response_reference', sa.String(length=255), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('integration_execution_logs')
    op.drop_table('integration_events')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_endpoints')
    op.drop_table('api_keys')
    op.drop_table('scim_provisioning_events')
    op.drop_table('scim_configurations')
    op.drop_table('identity_provider_configs')
    op.drop_table('integration_connections')
    op.drop_table('integration_providers')
    op.drop_table('encrypted_secrets')
