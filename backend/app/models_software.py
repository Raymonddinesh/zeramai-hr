"""
models_software.py - Software catalog and license models for Module 11.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum as SAEnum,
    Integer,
    Text,
    ForeignKey,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class SoftwareStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class Software(Base):
    """Catalog of software products that can be licensed to employees."""

    __tablename__ = "software"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    vendor = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(SoftwareStatus), default=SoftwareStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationship to licenses
    licenses = relationship("SoftwareLicense", back_populates="software", cascade="all, delete-orphan")


class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class SoftwareLicense(Base):
    """Pool of seats for a given software product.

    `seat_count` is the total number of seats purchased.
    `allocated_seats` is the number currently assigned.
    """

    __tablename__ = "software_licenses"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    software_id = Column(String, ForeignKey("software.id"), nullable=False, index=True)
    license_reference = Column(String, nullable=True)  # e.g., license key or contract ID
    seat_count = Column(Integer, nullable=False)
    allocated_seats = Column(Integer, default=0, nullable=False)
    cost = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(SAEnum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "software_id", "license_reference", name="uq_software_license_ref"),
        # Ensure allocated seats never exceed total seats – enforced in application logic
    )

    software = relationship("Software", back_populates="licenses")
    assignments = relationship("EmployeeLicenseAssignment", back_populates="license", cascade="all, delete-orphan")


class EmployeeLicenseAssignment(Base):
    """Assign a seat from a SoftwareLicense to an employee.

    The row is immutable – revocation creates a new row with status REVOKED.
    """

    __tablename__ = "employee_license_assignments"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    license_id = Column(String, ForeignKey("software_licenses.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    assigned_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    revoked_date = Column(DateTime, nullable=True)
    status = Column(SAEnum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    license = relationship("SoftwareLicense", back_populates="assignments")
    person = relationship("Person")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("tenant_id", "license_id", "person_id", name="uq_license_person"),
    )
