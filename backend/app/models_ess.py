"""
models_ess.py - Module 6: Employee Self-Service (ESS) Expansion Models.
Includes EmployeeAsset and ExpenseClaim.
"""
import uuid
from datetime import datetime, date

from sqlalchemy import Enum as SAEnum, Column, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, Integer
from sqlalchemy.orm import relationship

import enum

class AssetCondition(enum.Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"



from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class EmployeeAsset(Base):
    """
    Physical or digital company asset assigned to an employee.
    """
    __tablename__ = "employee_assets"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    # Link to asset catalog (optional for legacy assets without catalog entry)
    catalog_id = Column(String, ForeignKey("asset_catalog.id"), nullable=True, index=True)

    asset_name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)  # laptop, monitor, mobile, access_card, etc.
    serial_number = Column(String, nullable=True)
    assigned_date = Column(Date, default=date.today, nullable=False)
    return_status = Column(String, default="assigned", nullable=False)  # assigned, returned, damaged, lost
    # Additional fields for assignment lifecycle

    expected_return_date = Column(Date, nullable=True)
    returned_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person")
    user = relationship("User")
    # relationship to asset catalog entry
    catalog = relationship("AssetCatalog", foreign_keys=[catalog_id], back_populates="employee_assets")


class ExpenseClaim(Base):
    """
    Employee expense reimbursement claim.
    """
    __tablename__ = "expense_claims"

    id = Column(String, primary_key=True, default=gen_uuid)
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    category = Column(String, nullable=False)  # travel, meals, internet, equipment, learning, etc.
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="INR", nullable=False)
    description = Column(Text, nullable=False)
    merchant = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, approved, rejected, reimbursed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    user = relationship("User")
