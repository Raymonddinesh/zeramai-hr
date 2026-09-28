"""module20_knowledge_and_communications

Revision ID: f20934e82b5b
Revises: e19823f71c4a
Create Date: 2026-09-28 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f20934e82b5b'
down_revision = 'e19823f71c4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. knowledge_categories
    op.create_table(
        'knowledge_categories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('parent_id', sa.String(length=36), nullable=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['knowledge_categories.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_categories_tenant_id'), 'knowledge_categories', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_categories_parent_id'), 'knowledge_categories', ['parent_id'], unique=False)
    op.create_index(op.f('ix_knowledge_categories_code'), 'knowledge_categories', ['code'], unique=False)

    # 2. knowledge_articles
    op.create_table(
        'knowledge_articles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('category_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content_reference', sa.Text(), nullable=False),
        sa.Column('article_type', sa.String(length=50), nullable=False, server_default='ARTICLE'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('visibility', sa.String(length=50), nullable=False, server_default='ALL_EMPLOYEES'),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False),
        sa.Column('review_due_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['knowledge_categories.id'], ),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_articles_tenant_id'), 'knowledge_articles', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_articles_category_id'), 'knowledge_articles', ['category_id'], unique=False)
    op.create_index(op.f('ix_knowledge_articles_slug'), 'knowledge_articles', ['slug'], unique=False)
    op.create_index(op.f('ix_knowledge_articles_status'), 'knowledge_articles', ['status'], unique=False)
    op.create_index(op.f('ix_knowledge_articles_article_type'), 'knowledge_articles', ['article_type'], unique=False)
    op.create_index(op.f('ix_knowledge_articles_published_at'), 'knowledge_articles', ['published_at'], unique=False)
    op.create_index(op.f('ix_knowledge_articles_review_due_at'), 'knowledge_articles', ['review_due_at'], unique=False)

    # 3. knowledge_article_versions
    op.create_table(
        'knowledge_article_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content_reference', sa.Text(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id', 'version_number', name='uq_article_version')
    )
    op.create_index(op.f('ix_knowledge_article_versions_tenant_id'), 'knowledge_article_versions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_article_versions_article_id'), 'knowledge_article_versions', ['article_id'], unique=False)

    # 4. knowledge_access_rules
    op.create_table(
        'knowledge_access_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('legal_entity_id', sa.String(length=36), nullable=True),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=True),
        sa.Column('department_id', sa.String(length=36), nullable=True),
        sa.Column('location_reference', sa.String(length=128), nullable=True),
        sa.Column('role_reference', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id'], ),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_access_rules_tenant_id'), 'knowledge_access_rules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_access_rules_article_id'), 'knowledge_access_rules', ['article_id'], unique=False)

    # 5. knowledge_article_relations
    op.create_table(
        'knowledge_article_relations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('related_article_id', sa.String(length=36), nullable=False),
        sa.Column('relation_type', sa.String(length=50), nullable=False, server_default='RELATED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id', 'related_article_id', 'relation_type', name='uq_article_relation')
    )
    op.create_index(op.f('ix_knowledge_article_relations_tenant_id'), 'knowledge_article_relations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_article_relations_article_id'), 'knowledge_article_relations', ['article_id'], unique=False)

    # 6. knowledge_feedbacks
    op.create_table(
        'knowledge_feedbacks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_feedbacks_tenant_id'), 'knowledge_feedbacks', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_feedbacks_article_id'), 'knowledge_feedbacks', ['article_id'], unique=False)
    op.create_index(op.f('ix_knowledge_feedbacks_person_id'), 'knowledge_feedbacks', ['person_id'], unique=False)

    # 7. knowledge_article_views
    op.create_table(
        'knowledge_article_views',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('viewed_at', sa.DateTime(), nullable=False),
        sa.Column('session_reference', sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_article_views_tenant_id'), 'knowledge_article_views', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_article_views_article_id'), 'knowledge_article_views', ['article_id'], unique=False)
    op.create_index(op.f('ix_knowledge_article_views_viewed_at'), 'knowledge_article_views', ['viewed_at'], unique=False)

    # 8. knowledge_review_tasks
    op.create_table(
        'knowledge_review_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('reviewer_user_id', sa.String(length=36), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['knowledge_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_review_tasks_tenant_id'), 'knowledge_review_tasks', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_review_tasks_article_id'), 'knowledge_review_tasks', ['article_id'], unique=False)
    op.create_index(op.f('ix_knowledge_review_tasks_status'), 'knowledge_review_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_knowledge_review_tasks_due_at'), 'knowledge_review_tasks', ['due_at'], unique=False)

    # 9. knowledge_search_events
    op.create_table(
        'knowledge_search_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=True),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category_filter', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_search_events_tenant_id'), 'knowledge_search_events', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_knowledge_search_events_query_hash'), 'knowledge_search_events', ['query_hash'], unique=False)
    op.create_index(op.f('ix_knowledge_search_events_created_at'), 'knowledge_search_events', ['created_at'], unique=False)

    # 10. employee_announcements
    op.create_table(
        'employee_announcements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content_reference', sa.Text(), nullable=False),
        sa.Column('announcement_type', sa.String(length=50), nullable=False, server_default='GENERAL'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='NORMAL'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('author_user_id', sa.String(length=36), nullable=False),
        sa.Column('publish_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledgement_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_announcements_tenant_id'), 'employee_announcements', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_employee_announcements_status'), 'employee_announcements', ['status'], unique=False)
    op.create_index(op.f('ix_employee_announcements_priority'), 'employee_announcements', ['priority'], unique=False)
    op.create_index(op.f('ix_employee_announcements_publish_at'), 'employee_announcements', ['publish_at'], unique=False)
    op.create_index(op.f('ix_employee_announcements_expires_at'), 'employee_announcements', ['expires_at'], unique=False)

    # 11. announcement_audience_rules
    op.create_table(
        'announcement_audience_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('announcement_id', sa.String(length=36), nullable=False),
        sa.Column('audience_type', sa.String(length=50), nullable=False),
        sa.Column('legal_entity_id', sa.String(length=36), nullable=True),
        sa.Column('department_id', sa.String(length=36), nullable=True),
        sa.Column('organization_unit_id', sa.String(length=36), nullable=True),
        sa.Column('location_reference', sa.String(length=128), nullable=True),
        sa.Column('role_reference', sa.String(length=128), nullable=True),
        sa.Column('employment_type', sa.String(length=64), nullable=True),
        sa.Column('manager_scope', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['announcement_id'], ['employee_announcements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id'], ),
        sa.ForeignKeyConstraint(['organization_unit_id'], ['organization_units.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_announcement_audience_rules_tenant_id'), 'announcement_audience_rules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_announcement_audience_rules_announcement_id'), 'announcement_audience_rules', ['announcement_id'], unique=False)

    # 12. announcement_read_receipts
    op.create_table(
        'announcement_read_receipts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('announcement_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['announcement_id'], ['employee_announcements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('announcement_id', 'person_id', name='uq_announcement_read')
    )
    op.create_index(op.f('ix_announcement_read_receipts_tenant_id'), 'announcement_read_receipts', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_announcement_read_receipts_announcement_id'), 'announcement_read_receipts', ['announcement_id'], unique=False)

    # 13. communication_acknowledgements
    op.create_table(
        'communication_acknowledgements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('announcement_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledgement_reference', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['announcement_id'], ['employee_announcements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('announcement_id', 'person_id', name='uq_announcement_ack')
    )
    op.create_index(op.f('ix_communication_acknowledgements_tenant_id'), 'communication_acknowledgements', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_communication_acknowledgements_announcement_id'), 'communication_acknowledgements', ['announcement_id'], unique=False)

    # 14. communication_templates
    op.create_table(
        'communication_templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('template_type', sa.String(length=50), nullable=False),
        sa.Column('subject_template', sa.String(length=255), nullable=False),
        sa.Column('body_reference', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_communication_templates_tenant_id'), 'communication_templates', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_communication_templates_template_type'), 'communication_templates', ['template_type'], unique=False)

    # 15. communication_preferences
    op.create_table(
        'communication_preferences',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('person_id', sa.String(length=36), nullable=False),
        sa.Column('communication_type', sa.String(length=50), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', 'communication_type', name='uq_person_comm_pref')
    )
    op.create_index(op.f('ix_communication_preferences_tenant_id'), 'communication_preferences', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_communication_preferences_person_id'), 'communication_preferences', ['person_id'], unique=False)


def downgrade() -> None:
    op.drop_table('communication_preferences')
    op.drop_table('communication_templates')
    op.drop_table('communication_acknowledgements')
    op.drop_table('announcement_read_receipts')
    op.drop_table('announcement_audience_rules')
    op.drop_table('employee_announcements')
    op.drop_table('knowledge_search_events')
    op.drop_table('knowledge_review_tasks')
    op.drop_table('knowledge_article_views')
    op.drop_table('knowledge_feedbacks')
    op.drop_table('knowledge_article_relations')
    op.drop_table('knowledge_access_rules')
    op.drop_table('knowledge_article_versions')
    op.drop_table('knowledge_articles')
    op.drop_table('knowledge_categories')
