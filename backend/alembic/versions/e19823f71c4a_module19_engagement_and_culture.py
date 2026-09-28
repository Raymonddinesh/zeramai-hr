"""module19_engagement_and_culture

Revision ID: e19823f71c4a
Revises: d17642e81a3b
Create Date: 2026-09-28 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e19823f71c4a'
down_revision = 'd17642e81a3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. survey_templates
    op.create_table(
        'survey_templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('survey_type', sa.String(length=50), nullable=False, server_default='ENGAGEMENT'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('estimated_minutes', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('anonymous_by_default', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_templates_tenant_id'), 'survey_templates', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_survey_templates_status'), 'survey_templates', ['status'], unique=False)

    # 2. survey_questions
    op.create_table(
        'survey_questions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False, server_default='RATING'),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='GENERAL'),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('anonymous', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('scale_min', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('scale_max', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('options_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['survey_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_questions_tenant_id'), 'survey_questions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_survey_questions_template_id'), 'survey_questions', ['template_id'], unique=False)

    # 3. survey_campaigns
    op.create_table(
        'survey_campaigns',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('audience_type', sa.String(length=50), nullable=False, server_default='ALL_EMPLOYEES'),
        sa.Column('target_department_id', sa.String(length=36), nullable=True),
        sa.Column('target_organization_unit_id', sa.String(length=36), nullable=True),
        sa.Column('start_at', sa.DateTime(), nullable=False),
        sa.Column('end_at', sa.DateTime(), nullable=False),
        sa.Column('anonymous', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('minimum_anonymity_threshold', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('visibility_type', sa.String(length=50), nullable=False, server_default='ANONYMOUS'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['survey_templates.id'], ),
        sa.ForeignKeyConstraint(['target_department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_campaigns_tenant_id'), 'survey_campaigns', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_survey_campaigns_template_id'), 'survey_campaigns', ['template_id'], unique=False)
    op.create_index(op.f('ix_survey_campaigns_status'), 'survey_campaigns', ['status'], unique=False)

    # 4. survey_recipients
    op.create_table(
        'survey_recipients',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('invitation_sent_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('participation_status', sa.String(length=50), nullable=False, server_default='INVITED'),
        sa.Column('response_token_hash', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['survey_campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_recipients_tenant_id'), 'survey_recipients', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_survey_recipients_campaign_id'), 'survey_recipients', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_survey_recipients_person_id'), 'survey_recipients', ['person_id'], unique=False)
    op.create_index(op.f('ix_survey_recipients_response_token_hash'), 'survey_recipients', ['response_token_hash'], unique=False)

    # 5. survey_responses
    op.create_table(
        'survey_responses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('recipient_id', sa.String(length=36), nullable=True),
        sa.Column('anonymous_response_id', sa.String(length=64), nullable=True),
        sa.Column('department_id', sa.String(length=36), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('completion_time_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['survey_campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['survey_recipients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_responses_tenant_id'), 'survey_responses', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_survey_responses_campaign_id'), 'survey_responses', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_survey_responses_recipient_id'), 'survey_responses', ['recipient_id'], unique=False)
    op.create_index(op.f('ix_survey_responses_anonymous_response_id'), 'survey_responses', ['anonymous_response_id'], unique=False)

    # 6. survey_answers
    op.create_table(
        'survey_answers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('response_id', sa.String(length=36), nullable=False),
        sa.Column('question_id', sa.String(length=36), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('answer_numeric', sa.Float(), nullable=True),
        sa.Column('answer_option', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['response_id'], ['survey_responses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['survey_questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_answers_tenant_id'), 'survey_answers', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_survey_answers_response_id'), 'survey_answers', ['response_id'], unique=False)
    op.create_index(op.f('ix_survey_answers_question_id'), 'survey_answers', ['question_id'], unique=False)

    # 7. employee_feedbacks
    op.create_table(
        'employee_feedbacks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='GENERAL'),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('visibility', sa.String(length=50), nullable=False, server_default='PRIVATE_HR'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SUBMITTED'),
        sa.Column('is_grievance_referral', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('er_case_id', sa.String(length=36), nullable=True),
        sa.Column('grievance_case_id', sa.String(length=36), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['er_case_id'], ['employee_relations_cases.id'], ),
        sa.ForeignKeyConstraint(['grievance_case_id'], ['grievance_cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_feedbacks_tenant_id'), 'employee_feedbacks', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_employee_feedbacks_person_id'), 'employee_feedbacks', ['person_id'], unique=False)
    op.create_index(op.f('ix_employee_feedbacks_status'), 'employee_feedbacks', ['status'], unique=False)

    # 8. employee_suggestions
    op.create_table(
        'employee_suggestions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='GENERAL'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('anonymous', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SUBMITTED'),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('votes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_suggestions_tenant_id'), 'employee_suggestions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_employee_suggestions_person_id'), 'employee_suggestions', ['person_id'], unique=False)
    op.create_index(op.f('ix_employee_suggestions_status'), 'employee_suggestions', ['status'], unique=False)

    # 9. engagement_action_plans
    op.create_table(
        'engagement_action_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('campaign_id', sa.String(length=36), nullable=True),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=True),
        sa.Column('department_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['survey_campaigns.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_engagement_action_plans_tenant_id'), 'engagement_action_plans', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_engagement_action_plans_campaign_id'), 'engagement_action_plans', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_engagement_action_plans_status'), 'engagement_action_plans', ['status'], unique=False)

    # 10. engagement_action_items
    op.create_table(
        'engagement_action_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('action_plan_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['action_plan_id'], ['engagement_action_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_engagement_action_items_tenant_id'), 'engagement_action_items', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_engagement_action_items_action_plan_id'), 'engagement_action_items', ['action_plan_id'], unique=False)

    # 11. recognition_programs
    op.create_table(
        'recognition_programs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('recognition_type', sa.String(length=50), nullable=False, server_default='PEER'),
        sa.Column('points_reward', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recognition_programs_tenant_id'), 'recognition_programs', ['tenant_id'], unique=False)

    # 12. recognition_awards
    op.create_table(
        'recognition_awards',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('program_id', sa.String(length=36), nullable=False),
        sa.Column('giver_person_id', sa.String(length=36), nullable=False),
        sa.Column('recipient_person_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='VALUES'),
        sa.Column('visibility', sa.String(length=50), nullable=False, server_default='PUBLIC'),
        sa.Column('awarded_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PUBLISHED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['program_id'], ['recognition_programs.id'], ),
        sa.ForeignKeyConstraint(['giver_person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['recipient_person_id'], ['persons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recognition_awards_tenant_id'), 'recognition_awards', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_recognition_awards_giver_person_id'), 'recognition_awards', ['giver_person_id'], unique=False)
    op.create_index(op.f('ix_recognition_awards_recipient_person_id'), 'recognition_awards', ['recipient_person_id'], unique=False)

    # 13. award_definitions
    op.create_table(
        'award_definitions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('criteria', sa.Text(), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=False, server_default='ANNUAL'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_award_definitions_tenant_id'), 'award_definitions', ['tenant_id'], unique=False)

    # 14. award_nominations
    op.create_table(
        'award_nominations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('award_definition_id', sa.String(length=36), nullable=False),
        sa.Column('nominee_person_id', sa.String(length=36), nullable=False),
        sa.Column('nominated_by', sa.String(length=36), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOMINATED'),
        sa.Column('nominated_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('review_comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['award_definition_id'], ['award_definitions.id'], ),
        sa.ForeignKeyConstraint(['nominee_person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['nominated_by'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_award_nominations_tenant_id'), 'award_nominations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_award_nominations_nominee_person_id'), 'award_nominations', ['nominee_person_id'], unique=False)
    op.create_index(op.f('ix_award_nominations_status'), 'award_nominations', ['status'], unique=False)

    # 15. culture_initiatives
    op.create_table(
        'culture_initiatives',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='COMMUNITY'),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('target_participants', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_culture_initiatives_tenant_id'), 'culture_initiatives', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_culture_initiatives_status'), 'culture_initiatives', ['status'], unique=False)

    # 16. culture_participations
    op.create_table(
        'culture_participations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('initiative_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('participation_type', sa.String(length=100), nullable=False, server_default='ATTENDEE'),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('participated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['initiative_id'], ['culture_initiatives.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('initiative_id', 'person_id', name='uq_culture_initiative_person')
    )
    op.create_index(op.f('ix_culture_participations_tenant_id'), 'culture_participations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_culture_participations_person_id'), 'culture_participations', ['person_id'], unique=False)


def downgrade() -> None:
    op.drop_table('culture_participations')
    op.drop_table('culture_initiatives')
    op.drop_table('award_nominations')
    op.drop_table('award_definitions')
    op.drop_table('recognition_awards')
    op.drop_table('recognition_programs')
    op.drop_table('engagement_action_items')
    op.drop_table('engagement_action_plans')
    op.drop_table('employee_suggestions')
    op.drop_table('employee_feedbacks')
    op.drop_table('survey_answers')
    op.drop_table('survey_responses')
    op.drop_table('survey_recipients')
    op.drop_table('survey_campaigns')
    op.drop_table('survey_questions')
    op.drop_table('survey_templates')
