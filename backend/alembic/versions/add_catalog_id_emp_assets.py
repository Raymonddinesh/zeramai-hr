"""add catalog_id to employee_assets

Revision ID: add_catalog_id_emp_assets
Revises: d541d1d4e434
Create Date: 2026-09-27 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_catalog_id_emp_assets'
down_revision = 'd541d1d4e434'
branch_labels = None
depends_on = None

def upgrade():
    # Column already added manually; no operation needed.
    pass

def downgrade():
    op.drop_constraint('fk_employee_assets_catalog_id_asset_catalog', 'employee_assets', type_='foreignkey')
    op.drop_column('employee_assets', 'catalog_id')
