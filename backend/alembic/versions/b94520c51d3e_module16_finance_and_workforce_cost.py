"""module16 enterprise finance billing and workforce cost management models

Revision ID: b94520c51d3e
Revises: a83419b48c1f
Create Date: 2026-09-28 12:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b94520c51d3e'
down_revision: Union[str, Sequence[str], None] = 'a83419b48c1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update cost_centers with enterprise finance columns
    with op.batch_alter_table('cost_centers') as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('manager_person_id', sa.String(), sa.ForeignKey('persons.id', name='fk_cost_centers_mgr_person'), nullable=True))
        batch_op.add_column(sa.Column('parent_cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id', name='fk_cost_centers_parent_cc'), nullable=True))
        batch_op.add_column(sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False))
        batch_op.add_column(sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.add_column(sa.Column('effective_from', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('effective_to', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # 2. financial_dimensions
    op.create_table(
        'financial_dimensions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('code', sa.String(length=50), nullable=False, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('dimension_type', sa.String(length=50), server_default='COST_CENTER', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 3. financial_dimension_values
    op.create_table(
        'financial_dimension_values',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('dimension_id', sa.String(), sa.ForeignKey('financial_dimensions.id'), nullable=False, index=True),
        sa.Column('code', sa.String(length=50), nullable=False, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('parent_id', sa.String(), sa.ForeignKey('financial_dimension_values.id'), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 4. employee_cost_allocations
    op.create_table(
        'employee_cost_allocations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False, index=True),
        sa.Column('engagement_id', sa.String(), sa.ForeignKey('engagements.id'), nullable=True, index=True),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=False, index=True),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('allocation_type', sa.String(length=50), server_default='PRIMARY', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 5. gl_accounts
    op.create_table(
        'gl_accounts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('code', sa.String(length=50), nullable=False, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('account_type', sa.String(length=50), server_default='EXPENSE', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 6. gl_mappings
    op.create_table(
        'gl_mappings',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('transaction_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_code', sa.String(length=50), nullable=True),
        sa.Column('debit_account_id', sa.String(), sa.ForeignKey('gl_accounts.id'), nullable=False),
        sa.Column('credit_account_id', sa.String(), sa.ForeignKey('gl_accounts.id'), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 7. payroll_journals
    op.create_table(
        'payroll_journals',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('payroll_run_id', sa.String(), sa.ForeignKey('payroll_runs.id'), nullable=True, index=True),
        sa.Column('journal_number', sa.String(length=100), nullable=False, index=True),
        sa.Column('accounting_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='DRAFT', nullable=False, index=True),
        sa.Column('total_debit', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('total_credit', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('posted_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 8. payroll_journal_lines
    op.create_table(
        'payroll_journal_lines',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('journal_id', sa.String(), sa.ForeignKey('payroll_journals.id'), nullable=False, index=True),
        sa.Column('account_id', sa.String(), sa.ForeignKey('gl_accounts.id'), nullable=False, index=True),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True, index=True),
        sa.Column('dimension_reference', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('debit', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('credit', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('person_reference', sa.String(), sa.ForeignKey('persons.id'), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 9. workforce_cost_records
    op.create_table(
        'workforce_cost_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('person_id', sa.String(), sa.ForeignKey('persons.id'), nullable=False, index=True),
        sa.Column('engagement_id', sa.String(), sa.ForeignKey('engagements.id'), nullable=True, index=True),
        sa.Column('payroll_run_id', sa.String(), sa.ForeignKey('payroll_runs.id'), nullable=True, index=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('base_salary', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('bonus', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('employer_statutory_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('benefits_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('reimbursement_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('leave_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=True),
        sa.Column('other_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 10. expense_accounting_entries
    op.create_table(
        'expense_accounting_entries',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('expense_claim_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('reimbursement_id', sa.String(length=100), nullable=True),
        sa.Column('gl_account_id', sa.String(), sa.ForeignKey('gl_accounts.id'), nullable=False),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('accounting_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False, index=True),
        sa.Column('journal_id', sa.String(), sa.ForeignKey('payroll_journals.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 11. accrual_rules
    op.create_table(
        'accrual_rules',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('accrual_type', sa.String(length=50), server_default='BONUS', nullable=False),
        sa.Column('calculation_method', sa.String(length=50), server_default='FIXED_MONTHLY', nullable=False),
        sa.Column('frequency', sa.String(length=50), server_default='MONTHLY', nullable=False),
        sa.Column('account_id', sa.String(), sa.ForeignKey('gl_accounts.id'), nullable=False),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 12. accrual_records
    op.create_table(
        'accrual_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('rule_id', sa.String(), sa.ForeignKey('accrual_rules.id'), nullable=False, index=True),
        sa.Column('period', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('journal_id', sa.String(), sa.ForeignKey('payroll_journals.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 13. workforce_budgets
    op.create_table(
        'workforce_budgets',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('fiscal_year', sa.String(length=20), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='DRAFT', nullable=False, index=True),
        sa.Column('total_budget', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('approved_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 14. workforce_budget_lines
    op.create_table(
        'workforce_budget_lines',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('budget_id', sa.String(), sa.ForeignKey('workforce_budgets.id'), nullable=False, index=True),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=False, index=True),
        sa.Column('department_id', sa.String(), nullable=True),
        sa.Column('category', sa.String(length=50), server_default='SALARY', nullable=False),
        sa.Column('month', sa.String(length=20), nullable=False),
        sa.Column('budget_amount', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 15. vendors
    op.create_table(
        'vendors',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('legal_entity_id', sa.String(), sa.ForeignKey('legal_entities.id'), nullable=True),
        sa.Column('vendor_code', sa.String(length=50), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), server_default='STAFFING', nullable=False),
        sa.Column('tax_identifier', sa.String(length=50), nullable=True),
        sa.Column('contact_reference', sa.String(length=255), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 16. vendor_contracts
    op.create_table(
        'vendor_contracts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('vendor_id', sa.String(), sa.ForeignKey('vendors.id'), nullable=False, index=True),
        sa.Column('contract_reference', sa.String(length=100), nullable=False, index=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('recurring_amount', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('payment_frequency', sa.String(length=50), server_default='MONTHLY', nullable=False),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 17. vendor_invoices
    op.create_table(
        'vendor_invoices',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('vendor_id', sa.String(), sa.ForeignKey('vendors.id'), nullable=False, index=True),
        sa.Column('invoice_number', sa.String(length=100), nullable=False, index=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='DRAFT', nullable=False, index=True),
        sa.Column('external_reference', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('vendor_invoices')
    op.drop_table('vendor_contracts')
    op.drop_table('vendors')
    op.drop_table('workforce_budget_lines')
    op.drop_table('workforce_budgets')
    op.drop_table('accrual_records')
    op.drop_table('accrual_rules')
    op.drop_table('expense_accounting_entries')
    op.drop_table('workforce_cost_records')
    op.drop_table('payroll_journal_lines')
    op.drop_table('payroll_journals')
    op.drop_table('gl_mappings')
    op.drop_table('gl_accounts')
    op.drop_table('employee_cost_allocations')
    op.drop_table('financial_dimension_values')
    op.drop_table('financial_dimensions')

    with op.batch_alter_table('cost_centers') as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('effective_to')
        batch_op.drop_column('effective_from')
        batch_op.drop_column('active')
        batch_op.drop_column('currency')
        batch_op.drop_column('parent_cost_center_id')
        batch_op.drop_column('manager_person_id')
        batch_op.drop_column('description')
