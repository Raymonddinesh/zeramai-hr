import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Multi-Tenant & Multi-Entity Core (PRD v3.0 Section 6)
# ---------------------------------------------------------------------------

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    config_json = Column(JSON, nullable=True)  # Regional settings, default currency, enabled features
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    legal_entities = relationship("LegalEntity", back_populates="tenant")


class LegalEntity(Base):
    __tablename__ = "legal_entities"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    registration_number = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    country_code = Column(String(2), default="IN", nullable=False)  # ISO-2 (IN, US, AE, SG, UK)
    default_currency = Column(String(3), default="INR", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="legal_entities")
    locations = relationship("Location", back_populates="legal_entity")
    departments = relationship("Department", back_populates="legal_entity")


class Location(Base):
    __tablename__ = "locations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False)
    name = Column(String, nullable=False)
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country_code = Column(String(2), default="IN", nullable=False)
    timezone = Column(String, default="Asia/Kolkata", nullable=False)

    legal_entity = relationship("LegalEntity", back_populates="locations")


class Department(Base):
    __tablename__ = "departments"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False)
    name = Column(String, nullable=False)
    parent_department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    manager_id = Column(String, ForeignKey("users.id"), nullable=True)

    legal_entity = relationship("LegalEntity", back_populates="departments")


class CostCenter(Base):
    __tablename__ = "cost_centers"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    manager_person_id = Column(String, ForeignKey("persons.id"), nullable=True)
    parent_cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True)
    currency = Column(String(10), default="INR", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    effective_from = Column(Date, default=date.today, nullable=True)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Effective-Dated Employee Master & Employment History (PRD v3.0 Section 8 & 9)
# ---------------------------------------------------------------------------

class HistoryChangeType(str, enum.Enum):
    JOINING = "joining"
    PROMOTION = "promotion"
    TRANSFER = "transfer"
    COMPENSATION_REVISION = "compensation_revision"
    MANAGER_CHANGE = "manager_change"
    STATUS_CHANGE = "status_change"
    EXIT = "exit"


class EmploymentHistory(Base):
    __tablename__ = "employment_history"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    effective_date = Column(Date, nullable=False)
    change_type = Column(Enum(HistoryChangeType), nullable=False)

    designation = Column(String, nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    location_id = Column(String, ForeignKey("locations.id"), nullable=True)
    manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)

    salary_amount = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(3), default="INR")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
