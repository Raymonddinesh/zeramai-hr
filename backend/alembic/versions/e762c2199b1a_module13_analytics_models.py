"""module13 analytics and reporting models

Revision ID: e762c2199b1a
Revises: d541d1d4e434
Create Date: 2026-09-27 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e762c2199b1a'
down_revision: Union[str, Sequence[str], None] = 'd541d1d4e434'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. analytics_report_definitions
    op.create_table(
        'analytics_report_definitions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('dimensions', sa.JSON(), nullable=True),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('grouping', sa.JSON(), nullable=True),
        sa.Column('sorting', sa.JSON(), nullable=True),
        sa.Column('visibility', sa.String(length=50), nullable=False),
        sa.Column('owner_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('allowed_roles', sa.JSON(), nullable=True),
        sa.Column('min_aggregation_threshold', sa.Integer(), nullable=False, default=3),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 2. analytics_dashboards
    op.create_table(
        'analytics_dashboards',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dashboard_type', sa.String(length=50), nullable=False),
        sa.Column('layout', sa.JSON(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('visibility', sa.String(length=50), nullable=False),
        sa.Column('owner_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('allowed_roles', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 3. analytics_widgets
    op.create_table(
        'analytics_widgets',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('dashboard_id', sa.String(), sa.ForeignKey('analytics_dashboards.id'), nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('widget_type', sa.String(length=50), nullable=False),
        sa.Column('metric', sa.String(length=100), nullable=False),
        sa.Column('dimensions', sa.JSON(), nullable=True),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('report_definition_id', sa.String(), sa.ForeignKey('analytics_report_definitions.id'), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 4. analytics_filters
    op.create_table(
        'analytics_filters',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('filter_key', sa.String(length=100), nullable=False),
        sa.Column('filter_type', sa.String(length=50), nullable=False, default='DROPDOWN'),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('default_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 5. scheduled_reports
    op.create_table(
        'scheduled_reports',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('report_definition_id', sa.String(), sa.ForeignKey('analytics_report_definitions.id'), nullable=False, index=True),
        sa.Column('frequency', sa.String(length=50), nullable=False),
        sa.Column('recipients', sa.JSON(), nullable=False),
        sa.Column('format', sa.String(length=20), nullable=False, default='CSV'),
        sa.Column('status', sa.String(length=50), nullable=False, default='ACTIVE'),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 6. report_executions
    op.create_table(
        'report_executions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('report_definition_id', sa.String(), sa.ForeignKey('analytics_report_definitions.id'), nullable=False, index=True),
        sa.Column('scheduled_report_id', sa.String(), sa.ForeignKey('scheduled_reports.id'), nullable=True, index=True),
        sa.Column('executed_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='PENDING'),
        sa.Column('format', sa.String(length=20), nullable=False, default='CSV'),
        sa.Column('row_count', sa.Integer(), nullable=False, default=0),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 7. report_exports
    op.create_table(
        'report_exports',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('execution_id', sa.String(), sa.ForeignKey('report_executions.id'), nullable=False, index=True),
        sa.Column('export_format', sa.String(length=20), nullable=False, default='CSV'),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.String(length=50), nullable=False, default='READY'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('report_exports')
    op.drop_table('report_executions')
    op.drop_table('scheduled_reports')
    op.drop_table('analytics_filters')
    op.drop_table('analytics_widgets')
    op.drop_table('analytics_dashboards')
    op.drop_table('analytics_report_definitions')
