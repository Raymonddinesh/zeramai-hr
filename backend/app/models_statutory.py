import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Core Statutory Enums
# ---------------------------------------------------------------------------

class StatutoryAuthority(str, enum.Enum):
    EPFO = "epfo"
    ESIC = "esic"
    STATE_TAX = "state_tax"
    INCOME_TAX = "income_tax"
    LABOUR = "labour"


class StatutoryScheme(str, enum.Enum):
    EPF = "epf"
    ESI = "esi"
    PROFESSIONAL_TAX = "professional_tax"
    TDS = "tds"
    LABOUR_COMPLIANCE = "labour_compliance"


class FilingStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PAID = "paid"
    OVERDUE = "overdue"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    PAID = "paid"
    OVERDUE = "overdue"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TaxRegime(str, enum.Enum):
    OLD = "old"
    NEW = "new"


class TaxDeclarationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Core Statutory Models (Tenant & Legal Entity Aware)
# ---------------------------------------------------------------------------

class StatutoryRule(Base):
    """Configuration rule for statutory calculations.
    Effective-dated and scoped to tenant, legal entity, state, etc.
    """
    __tablename__ = "statutory_rules"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False, index=True)
    authority = Column(Enum(StatutoryAuthority), nullable=False)
    scheme = Column(Enum(StatutoryScheme), nullable=False)
    state = Column(String, nullable=True)  # for PT state-specific rules
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    config = Column(JSON, nullable=False)  # rates, ceilings, slabs, etc.
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")


from app.models_v11 import StatutoryRegistration


class StatutoryApplicability(Base):
    """Links statutory rules to person / engagement applicability criteria."""
    __tablename__ = "statutory_applicabilities"

    id = Column(String, primary_key=True, default=gen_uuid)
    rule_id = Column(String, ForeignKey("statutory_rules.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=True, index=True)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True, index=True)
    criteria = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rule = relationship("StatutoryRule")
    person = relationship("Person")
    engagement = relationship("Engagement")


class StatutoryPeriod(Base):
    """Payroll period for which statutory calculations are performed."""
    __tablename__ = "statutory_periods"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    payroll_run_id = Column(String, ForeignKey("payroll_runs.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")
    payroll_run = relationship("PayrollRun")


class StatutoryCalculation(Base):
    """Immutable snapshot of a statutory calculation for an employee in a payroll period."""
    __tablename__ = "statutory_calculations"

    id = Column(String, primary_key=True, default=gen_uuid)
    period_id = Column(String, ForeignKey("statutory_periods.id"), nullable=False, index=True)
    rule_id = Column(String, ForeignKey("statutory_rules.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    result_snapshot = Column(JSON, nullable=False)  # full calculation details
    rule_version = Column(String, nullable=False)  # rule.id and version string at calculation time
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    period = relationship("StatutoryPeriod")
    rule = relationship("StatutoryRule")
    person = relationship("Person")


class StatutoryContribution(Base):
    """Individual contribution records (e.g. EPF employer/employee contributions)."""
    __tablename__ = "statutory_contributions"

    id = Column(String, primary_key=True, default=gen_uuid)
    calculation_id = Column(String, ForeignKey("statutory_calculations.id"), nullable=False, index=True)
    contribution_type = Column(String, nullable=False)  # "employee", "employer", "admin_charges", "edli"
    amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    calculation = relationship("StatutoryCalculation")


class StatutoryFiling(Base):
    """Tracking of statutory filing lifecycle (ECR, ESI Return, Form 24Q, etc.)."""
    __tablename__ = "statutory_filings"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True, index=True)
    authority = Column(Enum(StatutoryAuthority), nullable=False)
    scheme = Column(Enum(StatutoryScheme), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    filed_date = Column(Date, nullable=True)
    status = Column(Enum(FilingStatus), nullable=False, default=FilingStatus.DRAFT)
    reference_number = Column(String, nullable=True)
    filing_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    responsible_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")
    filing_document = relationship("Document")
    responsible_user = relationship("User")


class StatutoryPayment(Base):
    """Tracking of statutory payments (challans, remittances)."""
    __tablename__ = "statutory_payments"

    id = Column(String, primary_key=True, default=gen_uuid)
    filing_id = Column(String, ForeignKey("statutory_filings.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    reference_number = Column(String, nullable=True)  # Challan / Bank reference
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.DRAFT)
    payment_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    filing = relationship("StatutoryFiling")
    payment_document = relationship("Document")


class TaxDeclaration(Base):
    """Employee annual tax declaration and regime choice."""
    __tablename__ = "tax_declarations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    financial_year = Column(String, nullable=False)  # "2026-2027"
    regime = Column(Enum(TaxRegime), nullable=False, default=TaxRegime.NEW)
    projected_income = Column(Numeric(12, 2), nullable=False, default=0.0)
    deductions_json = Column(JSON, nullable=True)  # [{"section": "80C", "declared_amount": 150000.0, ...}]
    documents_json = Column(JSON, nullable=True)    # proof attachments
    status = Column(Enum(TaxDeclarationStatus), nullable=False, default=TaxDeclarationStatus.DRAFT)
    verified_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    person = relationship("Person")
    verified_by = relationship("User")
