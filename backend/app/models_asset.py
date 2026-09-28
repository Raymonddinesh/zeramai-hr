"""
models_asset.py - Asset Catalog and Assignment History models for Module 11.
"""

import uuid
from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Enum as SAEnum,
    Integer,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class AssetStatus(str, Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    LOST = "lost"


class AssetCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"


class AssetCatalog(Base):
    """Master catalogue of all physical/digital assets owned by a tenant.

    Each row represents a unique asset item that can be assigned to employees.
    """

    __tablename__ = "asset_catalog"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    asset_tag = Column(String, nullable=False)  # unique tag per tenant (e.g., barcode)
    name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)  # laptop, monitor, phone, software_license, etc.
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    purchase_date = Column(Date, nullable=True)
    purchase_cost = Column(String, nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    vendor = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(SAEnum(AssetStatus), default=AssetStatus.AVAILABLE, nullable=False)
    condition = Column(SAEnum(AssetCondition), default=AssetCondition.NEW, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "asset_tag", name="uq_asset_tenant_tag"),
        UniqueConstraint("tenant_id", "serial_number", name="uq_asset_tenant_serial"),
    )

    # relationship to assignments (historical & current)
    employee_assets = relationship("EmployeeAsset", back_populates="catalog", cascade="all, delete-orphan")
    assignments = relationship("AssetAssignmentHistory", back_populates="asset", cascade="all, delete-orphan")


class AssetAssignmentAction(str, Enum):
    ASSIGN = "assign"
    TRANSFER = "transfer"
    RETURN = "return"


class AssetAssignmentHistory(Base):
    """Immutable log of every assignment, transfer, and return of an asset.

    No updates/deletes are allowed – audit integrity is guaranteed by the DB.
    """

    __tablename__ = "asset_assignment_history"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    asset_id = Column(String, ForeignKey("asset_catalog.id"), nullable=False, index=True)
    employee_person_id = Column(String, ForeignKey("persons.id"), nullable=True, index=True)
    employee_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(SAEnum(AssetAssignmentAction), nullable=False)
    from_status = Column(SAEnum(AssetStatus), nullable=True)
    to_status = Column(SAEnum(AssetStatus), nullable=False)
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    performed_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)

    # optional snapshot fields for audit/debugging
    previous_employee_person_id = Column(String, nullable=True)
    new_employee_person_id = Column(String, nullable=True)
    previous_location = Column(String, nullable=True)
    new_location = Column(String, nullable=True)

    asset = relationship("AssetCatalog", back_populates="assignments")
    performed_by = relationship("User", foreign_keys=[performed_by_user_id])
    employee_person = relationship("Person", foreign_keys=[employee_person_id])
    employee_user = relationship("User", foreign_keys=[employee_user_id])

    __table_args__ = (
        # Prevent accidental duplicate entries for the same asset/action at the same timestamp
        UniqueConstraint("asset_id", "action", "performed_at", name="uq_asset_action_timestamp"),
    )
