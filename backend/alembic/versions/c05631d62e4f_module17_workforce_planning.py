"""module17_workforce_planning

Revision ID: c05631d62e4f
Revises: b94520c51d3e
Create Date: 2026-09-28 15:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c05631d62e4f'
down_revision = 'b94520c51d3e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. organization_units
    op.create_table(
        'organization_units',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('legal_entity_id', sa.String(length=36), nullable=True),
        sa.Column('parent_id', sa.String(length=36), nullable=True),
        sa.Column('department_id', sa.String(length=36), nullable=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('unit_type', sa.String(length=32), nullable=False, server_default='DEPARTMENT'),
        sa.Column('leader_person_id', sa.String(length=36), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['leader_person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_org_unit_tenant_code'),
    )
    op.create_index('ix_organization_units_tenant_id', 'organization_units', ['tenant_id'])
    op.create_index('ix_org_units_tenant_active', 'organization_units', ['tenant_id', 'active'])
    op.create_index('ix_org_units_tenant_parent', 'organization_units', ['tenant_id', 'parent_id'])

    # 2. positions
    op.create_table(
        'positions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('legal_entity_id', sa.String(length=36), nullable=True),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=False),
        sa.Column('position_code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('job_family', sa.String(length=100), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True, server_default='FULL_TIME'),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PLANNED'),
        sa.Column('headcount_capacity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('filled_count', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('manager_position_id', sa.String(length=36), nullable=True),
        sa.Column('cost_center_id', sa.String(length=36), nullable=True),
        sa.Column('budgeted_cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cost_center_id'], ['cost_centers.id']),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.ForeignKeyConstraint(['manager_position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'position_code', name='uq_positions_tenant_code'),
    )
    op.create_index('ix_positions_tenant_id', 'positions', ['tenant_id'])
    op.create_index('ix_positions_tenant_status', 'positions', ['tenant_id', 'status'])
    op.create_index('ix_positions_tenant_org', 'positions', ['tenant_id', 'organization_unit_id'])

    # 3. position_assignments
    op.create_table(
        'position_assignments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('position_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('engagement_id', sa.String(length=36), nullable=True),
        sa.Column('allocation_percentage', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('assignment_type', sa.String(length=32), nullable=False, server_default='PRIMARY'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_position_assignments_tenant_id', 'position_assignments', ['tenant_id'])
    op.create_index('ix_pos_assignments_tenant_person', 'position_assignments', ['tenant_id', 'person_id'])
    op.create_index('ix_pos_assignments_tenant_pos', 'position_assignments', ['tenant_id', 'position_id'])

    # 4. headcount_plans
    op.create_table(
        'headcount_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('legal_entity_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('fiscal_year', sa.String(length=32), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_headcount_plans_tenant_id', 'headcount_plans', ['tenant_id'])
    op.create_index('ix_headcount_plans_tenant_year', 'headcount_plans', ['tenant_id', 'fiscal_year'])

    # 5. headcount_plan_lines
    op.create_table(
        'headcount_plan_lines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=False),
        sa.Column('position_id', sa.String(length=36), nullable=True),
        sa.Column('job_family', sa.String(length=100), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('month', sa.String(length=7), nullable=False),
        sa.Column('planned_headcount', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('planned_hires', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('planned_exits', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('planned_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['headcount_plans.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_headcount_plan_lines_tenant_id', 'headcount_plan_lines', ['tenant_id'])
    op.create_index('ix_headcount_plan_lines_plan_id', 'headcount_plan_lines', ['plan_id'])

    # 6. workforce_demand_plans
    op.create_table(
        'workforce_demand_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('planning_horizon', sa.String(length=50), nullable=False, server_default='1_YEAR'),
        sa.Column('methodology', sa.String(length=100), nullable=False, server_default='BOTTOM_UP'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workforce_demand_plans_tenant_id', 'workforce_demand_plans', ['tenant_id'])

    # 7. workforce_demand_lines
    op.create_table(
        'workforce_demand_lines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=False),
        sa.Column('job_family', sa.String(length=100), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('period', sa.String(length=32), nullable=False),
        sa.Column('required_headcount', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('required_skills', sa.Text(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['workforce_demand_plans.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workforce_demand_lines_tenant_id', 'workforce_demand_lines', ['tenant_id'])

    # 8. workforce_gaps
    op.create_table(
        'workforce_gaps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plan_reference', sa.String(length=100), nullable=False),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=True),
        sa.Column('job_family', sa.String(length=100), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('period', sa.String(length=32), nullable=False),
        sa.Column('demand_headcount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('supply_headcount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('gap_headcount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('estimated_cost_gap', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('gap_type', sa.String(length=32), nullable=False, server_default='BALANCED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workforce_gaps_tenant_id', 'workforce_gaps', ['tenant_id'])
    op.create_index('ix_wf_gaps_tenant_period', 'workforce_gaps', ['tenant_id', 'period'])

    # 9. skills & skill_levels
    op.create_table(
        'skills',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='TECHNICAL'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skills_tenant_id', 'skills', ['tenant_id'])

    op.create_table(
        'skill_levels',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_levels_skill_id', 'skill_levels', ['skill_id'])

    # 10. employee_skills
    op.create_table(
        'employee_skills',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('skill_level_id', sa.String(length=36), nullable=True),
        sa.Column('proficiency', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('verified_by', sa.String(length=36), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='SELF_REPORTED'),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['skill_level_id'], ['skill_levels.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_employee_skills_tenant_id', 'employee_skills', ['tenant_id'])
    op.create_index('ix_emp_skills_tenant_person', 'employee_skills', ['tenant_id', 'person_id'])

    # 11. skill_requirements & skill_gap_analyses
    op.create_table(
        'skill_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('position_id', sa.String(length=36), nullable=True),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=True),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('required_level', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('required_headcount', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('priority', sa.String(length=32), nullable=False, server_default='HIGH'),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_requirements_tenant_id', 'skill_requirements', ['tenant_id'])

    op.create_table(
        'skill_gap_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('requirement_id', sa.String(length=36), nullable=False),
        sa.Column('available_headcount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('required_headcount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('gap_headcount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('average_proficiency', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('gap_severity', sa.String(length=32), nullable=False, server_default='LOW'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['requirement_id'], ['skill_requirements.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_gap_analyses_tenant_id', 'skill_gap_analyses', ['tenant_id'])

    # 12. critical_roles
    op.create_table(
        'critical_roles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('position_id', sa.String(length=36), nullable=False),
        sa.Column('criticality', sa.String(length=32), nullable=False, server_default='HIGH'),
        sa.Column('business_impact', sa.Text(), nullable=True),
        sa.Column('replacement_difficulty', sa.String(length=32), nullable=False, server_default='HIGH'),
        sa.Column('vacancy_risk', sa.String(length=32), nullable=False, server_default='MEDIUM'),
        sa.Column('identified_by', sa.String(length=36), nullable=True),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['identified_by'], ['users.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_critical_roles_tenant_id', 'critical_roles', ['tenant_id'])

    # 13. succession_plans & succession_candidates
    op.create_table(
        'succession_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('critical_role_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['critical_role_id'], ['critical_roles.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_succession_plans_tenant_id', 'succession_plans', ['tenant_id'])

    op.create_table(
        'succession_candidates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('succession_plan_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('readiness_level', sa.String(length=32), nullable=False, server_default='READY_1_2_YEARS'),
        sa.Column('development_actions', sa.Text(), nullable=True),
        sa.Column('target_readiness_date', sa.Date(), nullable=True),
        sa.Column('nomination_status', sa.String(length=32), nullable=False, server_default='NOMINATED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['succession_plan_id'], ['succession_plans.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_succession_candidates_tenant_id', 'succession_candidates', ['tenant_id'])

    # 14. talent_pools & talent_pool_members
    op.create_table(
        'talent_pools',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('purpose', sa.String(length=100), nullable=False, server_default='LEADERSHIP_PIPELINE'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_talent_pools_tenant_id', 'talent_pools', ['tenant_id'])

    op.create_table(
        'talent_pool_members',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('talent_pool_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='HR_NOMINATION'),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['talent_pool_id'], ['talent_pools.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_talent_pool_members_tenant_id', 'talent_pool_members', ['tenant_id'])

    # 15. workforce_scenarios & workforce_scenario_lines
    op.create_table(
        'workforce_scenarios',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scenario_type', sa.String(length=32), nullable=False, server_default='BASELINE'),
        sa.Column('planning_horizon', sa.String(length=50), nullable=False, server_default='FY2026-27'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workforce_scenarios_tenant_id', 'workforce_scenarios', ['tenant_id'])

    op.create_table(
        'workforce_scenario_lines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('scenario_id', sa.String(length=36), nullable=False),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=False),
        sa.Column('job_family', sa.String(length=100), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('period', sa.String(length=32), nullable=False),
        sa.Column('headcount_delta', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('hiring_delta', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('exit_delta', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cost_delta', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['scenario_id'], ['workforce_scenarios.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workforce_scenario_lines_tenant_id', 'workforce_scenario_lines', ['tenant_id'])

    # 16. workforce_hiring_plans & hiring_plan_lines
    op.create_table(
        'workforce_hiring_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('fiscal_year', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workforce_hiring_plans_tenant_id', 'workforce_hiring_plans', ['tenant_id'])

    op.create_table(
        'hiring_plan_lines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=False),
        sa.Column('position_id', sa.String(length=36), nullable=True),
        sa.Column('job_family', sa.String(length=100), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('planned_open_date', sa.Date(), nullable=False),
        sa.Column('planned_join_date', sa.Date(), nullable=False),
        sa.Column('planned_headcount', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('recruitment_priority', sa.String(length=32), nullable=False, server_default='MEDIUM'),
        sa.Column('source_requisition_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['workforce_hiring_plans.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_hiring_plan_lines_tenant_id', 'hiring_plan_lines', ['tenant_id'])

    # 17. mobility_plans
    op.create_table(
        'mobility_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('current_position_id', sa.String(length=36), nullable=True),
        sa.Column('target_position_id', sa.String(length=36), nullable=True),
        sa.Column('mobility_type', sa.String(length=32), nullable=False, server_default='TRANSFER'),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['current_position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['target_position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mobility_plans_tenant_id', 'mobility_plans', ['tenant_id'])
    op.create_index('ix_mobility_plans_tenant_person', 'mobility_plans', ['tenant_id', 'person_id'])
    op.create_index('ix_mobility_plans_tenant_status', 'mobility_plans', ['tenant_id', 'status'])


def downgrade() -> None:
    op.drop_table('mobility_plans')
    op.drop_table('hiring_plan_lines')
    op.drop_table('workforce_hiring_plans')
    op.drop_table('workforce_scenario_lines')
    op.drop_table('workforce_scenarios')
    op.drop_table('talent_pool_members')
    op.drop_table('talent_pools')
    op.drop_table('succession_candidates')
    op.drop_table('succession_plans')
    op.drop_table('critical_roles')
    op.drop_table('skill_gap_analyses')
    op.drop_table('skill_requirements')
    op.drop_table('employee_skills')
    op.drop_table('skill_levels')
    op.drop_table('skills')
    op.drop_table('workforce_gaps')
    op.drop_table('workforce_demand_lines')
    op.drop_table('workforce_demand_plans')
    op.drop_table('headcount_plan_lines')
    op.drop_table('headcount_plans')
    op.drop_table('position_assignments')
    op.drop_table('positions')
    op.drop_table('organization_units')
