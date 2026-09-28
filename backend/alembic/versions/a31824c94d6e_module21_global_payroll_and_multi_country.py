"""Module 21: Global Payroll & Multi-Country Workforce Platform

Revision ID: a31824c94d6e
Revises: f20934e82b5b
Create Date: 2026-09-28 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'a31824c94d6e'
down_revision = 'f20934e82b5b'
branch_labels = None
depends_on = None


def upgrade():
    # 1. payroll_countries
    op.create_table(
        'payroll_countries',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('country_name', sa.String(length=100), nullable=False),
        sa.Column('default_currency', sa.String(length=3), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('payroll_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('adapter_status', sa.String(length=50), nullable=False, server_default='CONFIGURED_ONLY'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'country_code', name='uq_payroll_country_tenant_code'),
    )
    op.create_index('ix_payroll_countries_tenant_id', 'payroll_countries', ['tenant_id'])
    op.create_index('ix_payroll_countries_country_code', 'payroll_countries', ['country_code'])

    # 2. global_payroll_configurations
    op.create_table(
        'global_payroll_configurations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=False),
        sa.Column('country_id', sa.String(), sa.ForeignKey('payroll_countries.id'), nullable=False),
        sa.Column('default_currency', sa.String(length=3), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('payroll_frequency', sa.String(length=30), nullable=False, server_default='MONTHLY'),
        sa.Column('payroll_day', sa.Integer(), nullable=False, server_default='28'),
        sa.Column('cutoff_day', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('adapter_code', sa.String(length=100), nullable=False, server_default='GENERIC_INTERNATIONAL_ADAPTER'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_global_payroll_configurations_tenant_id', 'global_payroll_configurations', ['tenant_id'])
    op.create_index('ix_global_payroll_configurations_legal_entity_id', 'global_payroll_configurations', ['legal_entity_id'])
    op.create_index('ix_global_payroll_configurations_country_id', 'global_payroll_configurations', ['country_id'])

    # 3. payroll_pay_groups
    op.create_table(
        'payroll_pay_groups',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('payroll_configuration_id', sa.String(), sa.ForeignKey('global_payroll_configurations.id'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('frequency', sa.String(length=30), nullable=False, server_default='MONTHLY'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_payroll_pay_group_tenant_code'),
    )
    op.create_index('ix_payroll_pay_groups_tenant_id', 'payroll_pay_groups', ['tenant_id'])
    op.create_index('ix_payroll_pay_groups_config_id', 'payroll_pay_groups', ['payroll_configuration_id'])
    op.create_index('ix_payroll_pay_groups_code', 'payroll_pay_groups', ['code'])

    # 4. payroll_calendars
    op.create_table(
        'payroll_calendars',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('pay_group_id', sa.String(), sa.ForeignKey('payroll_pay_groups.id'), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('cutoff_date', sa.Date(), nullable=False),
        sa.Column('pay_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_payroll_calendars_tenant_id', 'payroll_calendars', ['tenant_id'])
    op.create_index('ix_payroll_calendars_pay_group_id', 'payroll_calendars', ['pay_group_id'])
    op.create_index('ix_payroll_calendars_period_start', 'payroll_calendars', ['period_start'])
    op.create_index('ix_payroll_calendars_period_end', 'payroll_calendars', ['period_end'])
    op.create_index('ix_payroll_calendars_status', 'payroll_calendars', ['status'])

    # 5. global_pay_components
    op.create_table(
        'global_pay_components',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('component_type', sa.String(length=30), nullable=False),
        sa.Column('taxable', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('pensionable', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('recurring', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('country_code', sa.String(length=3), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_global_pay_components_tenant_id', 'global_pay_components', ['tenant_id'])
    op.create_index('ix_global_pay_components_code', 'global_pay_components', ['code'])
    op.create_index('ix_global_pay_components_country_code', 'global_pay_components', ['country_code'])

    # 6. payroll_inputs
    op.create_table(
        'payroll_inputs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('payroll_calendar_id', sa.String(), sa.ForeignKey('payroll_calendars.id'), nullable=False),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('pay_component_id', sa.String(), sa.ForeignKey('global_pay_components.id'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False, server_default='MANUAL'),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_payroll_inputs_tenant_id', 'payroll_inputs', ['tenant_id'])
    op.create_index('ix_payroll_inputs_calendar_id', 'payroll_inputs', ['payroll_calendar_id'])
    op.create_index('ix_payroll_inputs_person_id', 'payroll_inputs', ['person_id'])
    op.create_index('ix_payroll_inputs_pay_component_id', 'payroll_inputs', ['pay_component_id'])

    # 7. country_payroll_rules
    op.create_table(
        'country_payroll_rules',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('rule_code', sa.String(length=50), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.String(length=30), nullable=False),
        sa.Column('configuration_reference', sa.JSON(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_country_payroll_rules_tenant_id', 'country_payroll_rules', ['tenant_id'])
    op.create_index('ix_country_payroll_rules_country_code', 'country_payroll_rules', ['country_code'])
    op.create_index('ix_country_payroll_rules_rule_code', 'country_payroll_rules', ['rule_code'])
    op.create_index('ix_country_payroll_rules_effective_from', 'country_payroll_rules', ['effective_from'])

    # 8. global_payroll_results
    op.create_table(
        'global_payroll_results',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('payroll_calendar_id', sa.String(), sa.ForeignKey('payroll_calendars.id'), nullable=False),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('gross', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('taxable_gross', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('employee_deductions', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('employer_contributions', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('tax', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('adjustments', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('net_pay', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('calculation_status', sa.String(length=30), nullable=False, server_default='CALCULATED'),
        sa.Column('fx_rate_used', sa.Numeric(precision=14, scale=6), nullable=False, server_default='1.000000'),
        sa.Column('base_currency', sa.String(length=3), nullable=True),
        sa.Column('base_net_pay', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('calculation_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'payroll_calendar_id', 'person_id', name='uq_payroll_result_cycle_person'),
    )
    op.create_index('ix_global_payroll_results_tenant_id', 'global_payroll_results', ['tenant_id'])
    op.create_index('ix_global_payroll_results_calendar_id', 'global_payroll_results', ['payroll_calendar_id'])
    op.create_index('ix_global_payroll_results_person_id', 'global_payroll_results', ['person_id'])
    op.create_index('ix_global_payroll_results_status', 'global_payroll_results', ['calculation_status'])

    # 9. payroll_result_components
    op.create_table(
        'payroll_result_components',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('payroll_result_id', sa.String(), sa.ForeignKey('global_payroll_results.id'), nullable=False),
        sa.Column('pay_component_id', sa.String(), sa.ForeignKey('global_pay_components.id'), nullable=True),
        sa.Column('component_code', sa.String(length=50), nullable=False),
        sa.Column('component_name', sa.String(length=100), nullable=False),
        sa.Column('component_type', sa.String(length=30), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('calculation_reference', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_payroll_result_components_tenant_id', 'payroll_result_components', ['tenant_id'])
    op.create_index('ix_payroll_result_components_result_id', 'payroll_result_components', ['payroll_result_id'])

    # 10. payroll_exchange_rates
    op.create_table(
        'payroll_exchange_rates',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('base_currency', sa.String(length=3), nullable=False),
        sa.Column('quote_currency', sa.String(length=3), nullable=False),
        sa.Column('rate', sa.Numeric(precision=14, scale=6), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False, server_default='CONFIGURED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'base_currency', 'quote_currency', 'effective_date', name='uq_payroll_fx_rate'),
    )
    op.create_index('ix_payroll_exchange_rates_tenant_id', 'payroll_exchange_rates', ['tenant_id'])
    op.create_index('ix_payroll_exchange_rates_base', 'payroll_exchange_rates', ['base_currency'])
    op.create_index('ix_payroll_exchange_rates_quote', 'payroll_exchange_rates', ['quote_currency'])

    # 11. employee_payroll_assignments
    op.create_table(
        'employee_payroll_assignments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('pay_group_id', sa.String(), sa.ForeignKey('payroll_pay_groups.id'), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('payroll_status', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('split_ratio', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100.00'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_employee_payroll_assignments_tenant_id', 'employee_payroll_assignments', ['tenant_id'])
    op.create_index('ix_employee_payroll_assignments_person_id', 'employee_payroll_assignments', ['person_id'])
    op.create_index('ix_employee_payroll_assignments_legal_entity_id', 'employee_payroll_assignments', ['legal_entity_id'])
    op.create_index('ix_employee_payroll_assignments_pay_group_id', 'employee_payroll_assignments', ['pay_group_id'])

    # 12. payroll_adjustments
    op.create_table(
        'payroll_adjustments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('original_payroll_result_id', sa.String(), sa.ForeignKey('global_payroll_results.id'), nullable=True),
        sa.Column('adjustment_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('effective_period', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_payroll_adjustments_tenant_id', 'payroll_adjustments', ['tenant_id'])
    op.create_index('ix_payroll_adjustments_person_id', 'payroll_adjustments', ['person_id'])
    op.create_index('ix_payroll_adjustments_status', 'payroll_adjustments', ['status'])

    # 13. payroll_reconciliations
    op.create_table(
        'payroll_reconciliations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('payroll_calendar_id', sa.String(), sa.ForeignKey('payroll_calendars.id'), nullable=False),
        sa.Column('expected_total', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('calculated_total', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('variance', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('reconciliation_reference', sa.Text(), nullable=True),
        sa.Column('finance_journal_id', sa.String(), sa.ForeignKey('payroll_journals.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('payroll_calendar_id', name='uq_payroll_reconciliation_calendar'),
    )
    op.create_index('ix_payroll_reconciliations_tenant_id', 'payroll_reconciliations', ['tenant_id'])

    # 14. global_payslip_records
    op.create_table(
        'global_payslip_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('payroll_result_id', sa.String(), sa.ForeignKey('global_payroll_results.id'), nullable=False),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('document_reference', sa.String(length=255), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='AVAILABLE'),
        sa.UniqueConstraint('payroll_result_id', name='uq_global_payslip_result'),
    )
    op.create_index('ix_global_payslip_records_tenant_id', 'global_payslip_records', ['tenant_id'])
    op.create_index('ix_global_payslip_records_person_id', 'global_payslip_records', ['person_id'])


def downgrade():
    op.drop_table('global_payslip_records')
    op.drop_table('payroll_reconciliations')
    op.drop_table('payroll_adjustments')
    op.drop_table('employee_payroll_assignments')
    op.drop_table('payroll_exchange_rates')
    op.drop_table('payroll_result_components')
    op.drop_table('global_payroll_results')
    op.drop_table('country_payroll_rules')
    op.drop_table('payroll_inputs')
    op.drop_table('global_pay_components')
    op.drop_table('payroll_calendars')
    op.drop_table('payroll_pay_groups')
    op.drop_table('global_payroll_configurations')
    op.drop_table('payroll_countries')
