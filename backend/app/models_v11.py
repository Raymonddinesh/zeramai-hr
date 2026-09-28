import enum
import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, Boolean, DateTime, Date, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class CompanyLegalProfile(Base):
    __tablename__ = "company_legal_profiles"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False, index=True)

    company_name = Column(String, nullable=False)
    trade_name = Column(String, nullable=True)
    company_type = Column(String, nullable=True)
    cin = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    tan_number = Column(String, nullable=True)
    gstin = Column(String, nullable=True)
    incorporation_date = Column(Date, nullable=True)
    financial_year_start = Column(Date, nullable=True)
    financial_year_end = Column(Date, nullable=True)
    registered_office = Column(Text, nullable=True)
    corporate_office = Column(Text, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    hr_contact = Column(String, nullable=True)
    finance_contact = Column(String, nullable=True)
    compliance_contact = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    legal_entity = relationship("LegalEntity", backref="company_legal_profiles")
    registrations = relationship("app.models_v11.StatutoryRegistration", back_populates="company_profile", cascade="all, delete-orphan")


class StatutoryRegistration(Base):
    __tablename__ = "company_statutory_registrations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    company_profile_id = Column(String, ForeignKey("company_legal_profiles.id"), nullable=True, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True, index=True)
    authority = Column(String, nullable=True)  # e.g. epfo, esic, state_tax
    registration_type = Column(String, nullable=True)  # e.g. EPFO, ESIC, etc.
    registration_number = Column(String, nullable=False)
    state = Column(String, nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="active")
    verification_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")
    company_profile = relationship("CompanyLegalProfile", back_populates="registrations")
