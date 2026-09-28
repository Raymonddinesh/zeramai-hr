"""module18_learning_and_career

Revision ID: d17642e81a3b
Revises: c05631d62e4f
Create Date: 2026-09-28 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd17642e81a3b'
down_revision = 'c05631d62e4f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. training_providers
    op.create_table(
        'training_providers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('contact_reference', sa.String(length=255), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_training_providers_tenant_id', 'training_providers', ['tenant_id'])

    # 2. learning_courses
    op.create_table(
        'learning_courses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=True),
        sa.Column('course_code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('learning_type', sa.String(length=50), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.String(length=36), nullable=True),
        sa.Column('delivery_mode', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['provider_id'], ['training_providers.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_courses_tenant_id', 'learning_courses', ['tenant_id'])
    op.create_index('ix_learning_courses_status', 'learning_courses', ['status'])

    # 3. learning_modules
    op.create_table(
        'learning_modules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_modules_course_id', 'learning_modules', ['course_id'])

    # 4. course_contents
    op.create_table(
        'course_contents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('module_id', sa.String(length=36), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content_reference', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['module_id'], ['learning_modules.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_course_contents_module_id', 'course_contents', ['module_id'])

    # 5. learning_paths
    op.create_table(
        'learning_paths',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('target_job_family', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_paths_tenant_id', 'learning_paths', ['tenant_id'])

    # 6. learning_path_courses
    op.create_table(
        'learning_path_courses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('learning_path_id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_path_courses_path_id', 'learning_path_courses', ['learning_path_id'])

    # 7. course_skill_mappings
    op.create_table(
        'course_skill_mappings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('target_skill_level_id', sa.String(length=36), nullable=True),
        sa.Column('proficiency_gain', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['target_skill_level_id'], ['skill_levels.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_course_skill_mappings_tenant_id', 'course_skill_mappings', ['tenant_id'])

    # 8. learning_enrollments
    op.create_table(
        'learning_enrollments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=True),
        sa.Column('learning_path_id', sa.String(length=36), nullable=True),
        sa.Column('enrollment_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('progress_percentage', sa.Float(), nullable=False),
        sa.Column('completion_score', sa.Float(), nullable=True),
        sa.Column('assigned_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id']),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_enrollments_tenant_id', 'learning_enrollments', ['tenant_id'])
    op.create_index('ix_learning_enrollments_person_id', 'learning_enrollments', ['person_id'])
    op.create_index('ix_learning_enrollments_status', 'learning_enrollments', ['status'])

    # 9. learning_progress
    op.create_table(
        'learning_progress',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('enrollment_id', sa.String(length=36), nullable=False),
        sa.Column('module_id', sa.String(length=36), nullable=False),
        sa.Column('progress_percentage', sa.Float(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('time_spent_minutes', sa.Integer(), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['enrollment_id'], ['learning_enrollments.id']),
        sa.ForeignKeyConstraint(['module_id'], ['learning_modules.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_progress_tenant_id', 'learning_progress', ['tenant_id'])

    # 10. learning_assessments
    op.create_table(
        'learning_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('passing_score', sa.Float(), nullable=False),
        sa.Column('attempts_allowed', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_assessments_tenant_id', 'learning_assessments', ['tenant_id'])

    # 11. assessment_questions
    op.create_table(
        'assessment_questions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('question_type', sa.String(length=32), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options_json', sa.Text(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('points', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['learning_assessments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assessment_questions_assessment_id', 'assessment_questions', ['assessment_id'])

    # 12. assessment_attempts
    op.create_table(
        'assessment_attempts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('enrollment_id', sa.String(length=36), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('answers_json', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['assessment_id'], ['learning_assessments.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['enrollment_id'], ['learning_enrollments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assessment_attempts_tenant_id', 'assessment_attempts', ['tenant_id'])

    # 13. certifications
    op.create_table(
        'certifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('issuing_body', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('validity_months', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_certifications_tenant_id', 'certifications', ['tenant_id'])

    # 14. employee_certifications
    op.create_table(
        'employee_certifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('certification_id', sa.String(length=36), nullable=False),
        sa.Column('credential_number', sa.String(length=100), nullable=True),
        sa.Column('issued_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('verification_status', sa.String(length=32), nullable=False),
        sa.Column('document_reference', sa.Text(), nullable=True),
        sa.Column('verified_by', sa.String(length=36), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['certification_id'], ['certifications.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_employee_certifications_tenant_id', 'employee_certifications', ['tenant_id'])
    op.create_index('ix_employee_certifications_expiry', 'employee_certifications', ['expiry_date'])

    # 15. training_requirements
    op.create_table(
        'training_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('applicability_rule', sa.String(length=255), nullable=False),
        sa.Column('due_days', sa.Integer(), nullable=False),
        sa.Column('recurrence', sa.String(length=50), nullable=False),
        sa.Column('mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('compliance_reference', sa.String(length=100), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_training_requirements_tenant_id', 'training_requirements', ['tenant_id'])

    # 16. training_assignments
    op.create_table(
        'training_assignments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('requirement_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['requirement_id'], ['training_requirements.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_training_assignments_tenant_id', 'training_assignments', ['tenant_id'])
    op.create_index('ix_training_assignments_due_at', 'training_assignments', ['due_at'])

    # 17. learning_plans
    op.create_table(
        'learning_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_plans_tenant_id', 'learning_plans', ['tenant_id'])

    # 18. learning_plan_items
    op.create_table(
        'learning_plan_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=True),
        sa.Column('learning_path_id', sa.String(length=36), nullable=True),
        sa.Column('skill_id', sa.String(length=36), nullable=True),
        sa.Column('target_skill_level_id', sa.String(length=36), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('priority', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['learning_plans.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['target_skill_level_id'], ['skill_levels.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_plan_items_tenant_id', 'learning_plan_items', ['tenant_id'])

    # 19. development_plans
    op.create_table(
        'development_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('current_role', sa.String(length=255), nullable=False),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('career_direction', sa.Text(), nullable=True),
        sa.Column('review_period', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('employee_notes', sa.Text(), nullable=True),
        sa.Column('manager_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_development_plans_tenant_id', 'development_plans', ['tenant_id'])

    # 20. development_goals
    op.create_table(
        'development_goals',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('development_plan_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('skill_id', sa.String(length=36), nullable=True),
        sa.Column('target_level_id', sa.String(length=36), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('progress_percentage', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['development_plan_id'], ['development_plans.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['target_level_id'], ['skill_levels.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_development_goals_tenant_id', 'development_goals', ['tenant_id'])

    # 21. career_frameworks
    op.create_table(
        'career_frameworks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('job_family', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_frameworks_tenant_id', 'career_frameworks', ['tenant_id'])

    # 22. career_levels
    op.create_table(
        'career_levels',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('framework_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('expected_skill_profile', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['framework_id'], ['career_frameworks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_levels_tenant_id', 'career_levels', ['tenant_id'])

    # 23. career_paths
    op.create_table(
        'career_paths',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('framework_id', sa.String(length=36), nullable=False),
        sa.Column('from_level_id', sa.String(length=36), nullable=False),
        sa.Column('to_level_id', sa.String(length=36), nullable=False),
        sa.Column('typical_requirements', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['framework_id'], ['career_frameworks.id']),
        sa.ForeignKeyConstraint(['from_level_id'], ['career_levels.id']),
        sa.ForeignKeyConstraint(['to_level_id'], ['career_levels.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_paths_tenant_id', 'career_paths', ['tenant_id'])

    # 24. career_opportunities
    op.create_table(
        'career_opportunities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('position_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required_skills', sa.Text(), nullable=True),
        sa.Column('required_level', sa.String(length=50), nullable=True),
        sa.Column('eligibility_rules', sa.Text(), nullable=True),
        sa.Column('application_deadline', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_opportunities_tenant_id', 'career_opportunities', ['tenant_id'])

    # 25. career_applications
    op.create_table(
        'career_applications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('opportunity_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=False),
        sa.Column('withdrawn_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['opportunity_id'], ['career_opportunities.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_applications_tenant_id', 'career_applications', ['tenant_id'])

    # 26. mentoring_programs
    op.create_table(
        'mentoring_programs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_months', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mentoring_programs_tenant_id', 'mentoring_programs', ['tenant_id'])

    # 27. mentoring_relationships
    op.create_table(
        'mentoring_relationships',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('program_id', sa.String(length=36), nullable=False),
        sa.Column('mentor_person_id', sa.String(length=36), nullable=False),
        sa.Column('mentee_person_id', sa.String(length=36), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['program_id'], ['mentoring_programs.id']),
        sa.ForeignKeyConstraint(['mentor_person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['mentee_person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mentoring_relationships_tenant_id', 'mentoring_relationships', ['tenant_id'])

    # 28. skill_development_actions
    op.create_table(
        'skill_development_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('skill_gap_reference', sa.String(length=100), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=True),
        sa.Column('mentoring_program_id', sa.String(length=36), nullable=True),
        sa.Column('target_level_id', sa.String(length=36), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['course_id'], ['learning_courses.id']),
        sa.ForeignKeyConstraint(['mentoring_program_id'], ['mentoring_programs.id']),
        sa.ForeignKeyConstraint(['target_level_id'], ['skill_levels.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_development_actions_tenant_id', 'skill_development_actions', ['tenant_id'])

    # 29. skill_evidence
    op.create_table(
        'skill_evidence',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('evidence_date', sa.Date(), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('verified_by', sa.String(length=36), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_evidence_tenant_id', 'skill_evidence', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('skill_evidence')
    op.drop_table('skill_development_actions')
    op.drop_table('mentoring_relationships')
    op.drop_table('mentoring_programs')
    op.drop_table('career_applications')
    op.drop_table('career_opportunities')
    op.drop_table('career_paths')
    op.drop_table('career_levels')
    op.drop_table('career_frameworks')
    op.drop_table('development_goals')
    op.drop_table('development_plans')
    op.drop_table('learning_plan_items')
    op.drop_table('learning_plans')
    op.drop_table('training_assignments')
    op.drop_table('training_requirements')
    op.drop_table('employee_certifications')
    op.drop_table('certifications')
    op.drop_table('assessment_attempts')
    op.drop_table('assessment_questions')
    op.drop_table('learning_assessments')
    op.drop_table('learning_progress')
    op.drop_table('learning_enrollments')
    op.drop_table('course_skill_mappings')
    op.drop_table('learning_path_courses')
    op.drop_table('learning_paths')
    op.drop_table('course_contents')
    op.drop_table('learning_modules')
    op.drop_table('learning_courses')
    op.drop_table('training_providers')
