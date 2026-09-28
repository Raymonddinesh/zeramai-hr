"""module15 data governance privacy retention and business continuity models

Revision ID: a83419b48c1f
Revises: f891d3401c2b
Create Date: 2026-09-28 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a83419b48c1f'
down_revision: Union[str, Sequence[str], None] = 'f891d3401c2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. data_classifications
    op.create_table(
        'data_classifications',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=True, index=True),
        sa.Column('code', sa.String(length=50), nullable=False, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sensitivity_level', sa.String(length=50), nullable=False, server_default='INTERNAL'),
        sa.Column('default_retention_days', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 2. retention_policies
    op.create_table(
        'retention_policies',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('record_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('retention_period_days', sa.Integer(), nullable=False),
        sa.Column('archive_after_days', sa.Integer(), nullable=False),
        sa.Column('deletion_after_days', sa.Integer(), nullable=True),
        sa.Column('legal_basis', sa.String(length=255), nullable=True),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False, server_default='IN'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 3. data_assets
    op.create_table(
        'data_assets',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=100), nullable=False),
        sa.Column('source_module', sa.String(length=100), nullable=False),
        sa.Column('classification_id', sa.String(), sa.ForeignKey('data_classifications.id'), nullable=False, index=True),
        sa.Column('contains_personal_data', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('contains_sensitive_personal_data', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('retention_policy_id', sa.String(), sa.ForeignKey('retention_policies.id'), nullable=True, index=True),
        sa.Column('data_residency', sa.String(length=100), nullable=True, server_default='IN-CENTRAL'),
        sa.Column('owner_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 4. retention_policy_assignments
    op.create_table(
        'retention_policy_assignments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('policy_id', sa.String(), sa.ForeignKey('retention_policies.id'), nullable=False, index=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_reference', sa.String(length=255), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 5. data_lifecycle_records
    op.create_table(
        'data_lifecycle_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('asset_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('asset_id', sa.String(), nullable=False, index=True),
        sa.Column('classification_id', sa.String(), sa.ForeignKey('data_classifications.id'), nullable=True),
        sa.Column('retention_policy_id', sa.String(), sa.ForeignKey('retention_policies.id'), nullable=True, index=True),
        sa.Column('lifecycle_status', sa.String(length=50), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('eligible_archive_at', sa.DateTime(), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('eligible_delete_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('anonymized_at', sa.DateTime(), nullable=True),
        sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column('last_evaluated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 6. legal_holds
    op.create_table(
        'legal_holds',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('matter_reference', sa.String(length=100), nullable=False, index=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('released_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )

    # 7. legal_hold_targets
    op.create_table(
        'legal_hold_targets',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_hold_id', sa.String(), sa.ForeignKey('legal_holds.id'), nullable=False, index=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_reference', sa.String(length=255), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 8. privacy_requests
    op.create_table(
        'privacy_requests',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=True, index=True),
        sa.Column('request_type', sa.String(length=50), nullable=False, server_default='EXPORT', index=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SUBMITTED', index=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('assigned_to', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='VERIFIED'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('export_reference', sa.String(length=255), nullable=True),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 9. backup_policies
    op.create_table(
        'backup_policies',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('frequency', sa.String(length=50), nullable=False, server_default='DAILY'),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('encryption_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('offsite_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('cross_region_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 10. backup_executions
    op.create_table(
        'backup_executions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('backup_policy_id', sa.String(), sa.ForeignKey('backup_policies.id'), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='COMPLETED', index=True),
        sa.Column('backup_reference', sa.String(length=255), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('checksum', sa.String(length=128), nullable=True),
        sa.Column('region', sa.String(length=50), nullable=False, server_default='IN-CENTRAL'),
        sa.Column('encryption_status', sa.String(length=50), nullable=False, server_default='ENCRYPTED_AES256'),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='VERIFIED'),
        sa.Column('error_message', sa.Text(), nullable=True),
    )

    # 11. dr_policies
    op.create_table(
        'dr_policies',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rpo_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('rto_minutes', sa.Integer(), nullable=False, server_default='240'),
        sa.Column('primary_region', sa.String(length=50), nullable=False, server_default='IN-SOUTH'),
        sa.Column('recovery_region', sa.String(length=50), nullable=False, server_default='IN-WEST'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='BUSINESS_CRITICAL'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 12. dr_tests
    op.create_table(
        'dr_tests',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('dr_policy_id', sa.String(), sa.ForeignKey('dr_policies.id'), nullable=False, index=True),
        sa.Column('test_type', sa.String(length=50), nullable=False, server_default='FAILOVER_SIMULATION'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PASSED', index=True),
        sa.Column('actual_rpo_minutes', sa.Integer(), nullable=True),
        sa.Column('actual_rto_minutes', sa.Integer(), nullable=True),
        sa.Column('findings', sa.Text(), nullable=True),
        sa.Column('corrective_actions', sa.Text(), nullable=True),
        sa.Column('tested_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )

    # 13. business_continuity_plans
    op.create_table(
        'business_continuity_plans',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('criticality', sa.String(length=50), nullable=False, server_default='CRITICAL'),
        sa.Column('owner_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('recovery_strategy', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('next_review_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 14. bcp_actions
    op.create_table(
        'bcp_actions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('plan_id', sa.String(), sa.ForeignKey('business_continuity_plans.id'), nullable=False, index=True),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('owner_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # 15. data_residency_policies
    op.create_table(
        'data_residency_policies',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('data_category', sa.String(length=100), nullable=False, index=True),
        sa.Column('allowed_regions', sa.JSON(), nullable=False),
        sa.Column('primary_region', sa.String(length=50), nullable=False, server_default='IN-CENTRAL'),
        sa.Column('cross_border_transfer_allowed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('transfer_basis', sa.String(length=255), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('data_residency_policies')
    op.drop_table('bcp_actions')
    op.drop_table('business_continuity_plans')
    op.drop_table('dr_tests')
    op.drop_table('dr_policies')
    op.drop_table('backup_executions')
    op.drop_table('backup_policies')
    op.drop_table('privacy_requests')
    op.drop_table('legal_hold_targets')
    op.drop_table('legal_holds')
    op.drop_table('data_lifecycle_records')
    op.drop_table('retention_policy_assignments')
    op.drop_table('data_assets')
    op.drop_table('retention_policies')
    op.drop_table('data_classifications')
