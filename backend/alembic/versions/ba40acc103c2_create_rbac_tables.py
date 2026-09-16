"""create rbac tables

Revision ID: ba40acc103c2
Revises: 
Create Date: 2026-09-05 20:41:42.175859

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ba40acc103c2'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create RBAC tables."""
    # roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
    )
    # permissions table
    op.create_table(
        "permissions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("code", sa.String, nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
    )
    # association tables
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String, sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.String, sa.ForeignKey("permissions.id"), primary_key=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.String, sa.ForeignKey("roles.id"), primary_key=True),
    )


def downgrade() -> None:
    """Drop RBAC tables."""
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
