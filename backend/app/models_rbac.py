from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

from .models import gen_uuid

# ---------------------------------------------------------------------------
# Permissions and RBAC tables
# ---------------------------------------------------------------------------

class Role(Base):
    """Role definition – e.g. super_admin, hr_admin, etc."""
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, nullable=False)

    # relationships
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )
    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
    )

class Permission(Base):
    """Fine‑grained permission, identified by a code like 'candidate:create'."""
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=gen_uuid)
    code = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.id"), primary_key=True)

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
