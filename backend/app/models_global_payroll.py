"""
models_global_payroll.py - Module 21: Global Payroll & Multi-Country Workforce Platform Data Models
Zeramai Enterprise HRMS

Canonical models for:
- PayrollCountry
- GlobalPayrollConfiguration
- PayrollPayGroup
- PayrollCalendar
- GlobalPayComponent
- PayrollInput
- CountryPayrollRule
- GlobalPayrollResult
- PayrollResultComponent
- PayrollExchangeRate
- EmployeePayrollAssignment
- PayrollAdjustment
- PayrollReconciliation
- GlobalPayslipRecord
"""
import enum
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ===========================================================================
# Enums
# ===========================================================================

class CountryPayrollStatus(str, enum.Enum):
    CONFIGURED_ONLY = "CONFIGURED_ONLY"
    FRAMEWORK_READY = "FRAMEWORK_READY"
    RULE_ENGINE_AVAILABLE = "RULE_ENGINE_AVAILABLE"
    PROVIDER_INTEGRATED = "PROVIDER_INTEGRATED"
    PRODUCTION_VALIDATED = "PRODUCTION_VALIDATED"


class PayrollFrequency(str, enum.Enum):
    MONTHLY = "MONTHLY"
    BIWEEKLY = "BIWEEKLY"
    WEEKLY = "WEEKLY"
    SEMIMONTHLY = "SEMIMONTHLY"
    CUSTOM = "CUSTOM"


class PayrollCalendarStatus(str, enum.Enum):
    OPEN = "OPEN"
    INPUT_CUTOFF = "INPUT_CUTOFF"
    PROCESSING = "PROCESSING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class GlobalPayComponentType(str, enum.Enum):
    EARNING = "EARNING"
    DEDUCTION = "DEDUCTION"
    EMPLOYER_CONTRIBUTION = "EMPLOYER_CONTRIBUTION"
    REIMBURSEMENT = "REIMBURSEMENT"
    ADJUSTMENT = "ADJUSTMENT"
    TAX = "TAX"
    BENEFIT = "BENEFIT"


class PayrollInputSource(str, enum.Enum):
    SALARY = "SALARY"
    COMPENSATION = "COMPENSATION"
    BONUS = "BONUS"
    BENEFIT = "BENEFIT"
    EXPENSE = "EXPENSE"
    TIME = "TIME"
    LEAVE = "LEAVE"
    MANUAL = "MANUAL"
    INTEGRATION = "INTEGRATION"
    STATUTORY = "STATUTORY"
    ADJUSTMENT = "ADJUSTMENT"


class CountryPayrollRuleType(str, enum.Enum):
    TAX = "TAX"
    STATUTORY_PENSION = "STATUTORY_PENSION"
    SOCIAL_SECURITY = "SOCIAL_SECURITY"
    OVERTIME = "OVERTIME"
    MINIMUM_WAGE = "MINIMUM_WAGE"
    SEVERANCE = "SEVERANCE"
    PRORATION = "PRORATION"


class GlobalPayrollResultStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"
    REVERSED = "REVERSED"


class FXRateSource(str, enum.Enum):
    CONFIGURED = "CONFIGURED"
    PROVIDER = "PROVIDER"
    MANUAL = "MANUAL"


class AssignmentPayrollStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class PayrollAdjustmentType(str, enum.Enum):
    UNDERPAYMENT = "UNDERPAYMENT"
    OVERPAYMENT = "OVERPAYMENT"
    RETROACTIVE = "RETROACTIVE"
    BONUS = "BONUS"
    DEDUCTION_CORRECTION = "DEDUCTION_CORRECTION"
    FX_CORRECTION = "FX_CORRECTION"
    STATUTORY_CORRECTION = "STATUTORY_CORRECTION"
    OTHER = "OTHER"


class PayrollAdjustmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSED = "PROCESSED"


class PayrollReconciliationStatus(str, enum.Enum):
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    VARIANCE = "VARIANCE"
    RESOLVED = "RESOLVED"


class GlobalPayslipStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    AVAILABLE = "AVAILABLE"
    REVOKED = "REVOKED"


# ===========================================================================
# 1. Payroll Country
# ===========================================================================

class PayrollCountry(Base):
    """Country payroll configuration registry."""
    __tablename__ = "payroll_countries"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    country_code = Column(String(3), nullable=False, index=True)  # ISO-3 (IND, USA, GBR, etc.)
    country_name = Column(String(100), nullable=False)
    default_currency = Column(String(3), nullable=False)           # ISO-3 (INR, USD, GBP, etc.)
    timezone = Column(String(50), nullable=False, default="UTC")
    active = Column(Boolean, default=True, nullable=False)
    payroll_enabled = Column(Boolean, default=True, nullable=False)
    adapter_status = Column(
        String(50),
        default=CountryPayrollStatus.CONFIGURED_ONLY.value,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    configurations = relationship("GlobalPayrollConfiguration", back_populates="country", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "country_code", name="uq_payroll_country_tenant_code"),
    )


# ===========================================================================
# 2. Global Payroll Configuration
# ===========================================================================

class GlobalPayrollConfiguration(Base):
    """Payroll configuration linking legal entities to country settings."""
    __tablename__ = "global_payroll_configurations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False, index=True)
    country_id = Column(String, ForeignKey("payroll_countries.id"), nullable=False, index=True)
    default_currency = Column(String(3), nullable=False)
    timezone = Column(String(50), nullable=False, default="UTC")
    payroll_frequency = Column(String(30), default=PayrollFrequency.MONTHLY.value, nullable=False)
    payroll_day = Column(Integer, default=28, nullable=False)
    cutoff_day = Column(Integer, default=20, nullable=False)
    adapter_code = Column(String(100), default="GENERIC_INTERNATIONAL_ADAPTER", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    country = relationship("PayrollCountry", back_populates="configurations")
    pay_groups = relationship("PayrollPayGroup", back_populates="configuration", cascade="all, delete-orphan")


# ===========================================================================
# 3. Payroll Pay Group
# ===========================================================================

class PayrollPayGroup(Base):
    """Logical grouping of employees processed together in a payroll cycle."""
    __tablename__ = "payroll_pay_groups"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    payroll_configuration_id = Column(String, ForeignKey("global_payroll_configurations.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    currency = Column(String(3), nullable=False)
    frequency = Column(String(30), default=PayrollFrequency.MONTHLY.value, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    configuration = relationship("GlobalPayrollConfiguration", back_populates="pay_groups")
    calendars = relationship("PayrollCalendar", back_populates="pay_group", cascade="all, delete-orphan")
    assignments = relationship("EmployeePayrollAssignment", back_populates="pay_group")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_payroll_pay_group_tenant_code"),
    )


# ===========================================================================
# 4. Payroll Calendar (Pay Periods)
# ===========================================================================

class PayrollCalendar(Base):
    """Specific payroll processing cycle/period for a pay group."""
    __tablename__ = "payroll_calendars"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    pay_group_id = Column(String, ForeignKey("payroll_pay_groups.id"), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    cutoff_date = Column(Date, nullable=False)
    pay_date = Column(Date, nullable=False)
    status = Column(String(30), default=PayrollCalendarStatus.OPEN.value, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pay_group = relationship("PayrollPayGroup", back_populates="calendars")
    inputs = relationship("PayrollInput", back_populates="calendar", cascade="all, delete-orphan")
    results = relationship("GlobalPayrollResult", back_populates="calendar", cascade="all, delete-orphan")
    reconciliation = relationship("PayrollReconciliation", back_populates="calendar", uselist=False, cascade="all, delete-orphan")


# ===========================================================================
# 5. Global Pay Component
# ===========================================================================

class GlobalPayComponent(Base):
    """Catalog of enterprise earnings, deductions, and employer contributions."""
    __tablename__ = "global_pay_components"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    component_type = Column(String(30), nullable=False)
    taxable = Column(Boolean, default=True, nullable=False)
    pensionable = Column(Boolean, default=True, nullable=False)
    recurring = Column(Boolean, default=True, nullable=False)
    country_code = Column(String(3), nullable=True, index=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ===========================================================================
# 6. Payroll Input
# ===========================================================================

class PayrollInput(Base):
    """Traceable raw input item for an employee in a payroll calendar cycle."""
    __tablename__ = "payroll_inputs"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    payroll_calendar_id = Column(String, ForeignKey("payroll_calendars.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    pay_component_id = Column(String, ForeignKey("global_pay_components.id"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)  # Decimal
    currency = Column(String(3), nullable=False)
    source = Column(String(30), default=PayrollInputSource.MANUAL.value, nullable=False)
    reference = Column(String(100), nullable=True)   # Source entity ID or transaction ref
    effective_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    calendar = relationship("PayrollCalendar", back_populates="inputs")
    component = relationship("GlobalPayComponent")


# ===========================================================================
# 7. Country Payroll Rule
# ===========================================================================

class CountryPayrollRule(Base):
    """Effective-dated statutory and country rule configurations."""
    __tablename__ = "country_payroll_rules"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    country_code = Column(String(3), nullable=False, index=True)
    rule_code = Column(String(50), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(String(30), nullable=False)
    configuration_reference = Column(JSON, nullable=True)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=True, index=True)
    active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ===========================================================================
# 8. Global Payroll Result & Calculation Components
# ===========================================================================

class GlobalPayrollResult(Base):
    """Finalized and snapshot gross-to-net payroll outcome for an employee."""
    __tablename__ = "global_payroll_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    payroll_calendar_id = Column(String, ForeignKey("payroll_calendars.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False)
    gross = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    taxable_gross = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    employee_deductions = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    employer_contributions = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    adjustments = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    net_pay = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    calculation_status = Column(
        String(30),
        default=GlobalPayrollResultStatus.CALCULATED.value,
        nullable=False,
        index=True,
    )
    fx_rate_used = Column(Numeric(14, 6), default=Decimal("1.000000"), nullable=False)
    base_currency = Column(String(3), nullable=True)
    base_net_pay = Column(Numeric(15, 2), nullable=True)
    calculation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    calendar = relationship("PayrollCalendar", back_populates="results")
    components = relationship("PayrollResultComponent", back_populates="payroll_result", cascade="all, delete-orphan")
    payslip = relationship("GlobalPayslipRecord", back_populates="payroll_result", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "payroll_calendar_id", "person_id", name="uq_payroll_result_cycle_person"),
    )


class PayrollResultComponent(Base):
    """Detailed breakdown line item for gross-to-net explainability."""
    __tablename__ = "payroll_result_components"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    payroll_result_id = Column(String, ForeignKey("global_payroll_results.id"), nullable=False, index=True)
    pay_component_id = Column(String, ForeignKey("global_pay_components.id"), nullable=True, index=True)
    component_code = Column(String(50), nullable=False)
    component_name = Column(String(100), nullable=False)
    component_type = Column(String(30), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    calculation_reference = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payroll_result = relationship("GlobalPayrollResult", back_populates="components")


# ===========================================================================
# 9. Multi-Currency FX Rates
# ===========================================================================

class PayrollExchangeRate(Base):
    """Snapshot FX exchange rates for multi-currency payroll calculations."""
    __tablename__ = "payroll_exchange_rates"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    base_currency = Column(String(3), nullable=False, index=True)
    quote_currency = Column(String(3), nullable=False, index=True)
    rate = Column(Numeric(14, 6), nullable=False)  # Decimal
    effective_date = Column(Date, default=date.today, nullable=False, index=True)
    source = Column(String(30), default=FXRateSource.CONFIGURED.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "base_currency", "quote_currency", "effective_date", name="uq_payroll_fx_rate"),
    )


# ===========================================================================
# 10. Employee Payroll Assignment & Split Payroll
# ===========================================================================

class EmployeePayrollAssignment(Base):
    """Employee membership in a pay group and jurisdiction."""
    __tablename__ = "employee_payroll_assignments"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=False, index=True)
    country_code = Column(String(3), nullable=False, index=True)
    pay_group_id = Column(String, ForeignKey("payroll_pay_groups.id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=True, index=True)
    payroll_status = Column(String(30), default=AssignmentPayrollStatus.ACTIVE.value, nullable=False)
    split_ratio = Column(Numeric(5, 2), default=Decimal("100.00"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pay_group = relationship("PayrollPayGroup", back_populates="assignments")


# ===========================================================================
# 11. Payroll Adjustments
# ===========================================================================

class PayrollAdjustment(Base):
    """Non-destructive retro or correction adjustment applied to payroll."""
    __tablename__ = "payroll_adjustments"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    original_payroll_result_id = Column(String, ForeignKey("global_payroll_results.id"), nullable=True, index=True)
    adjustment_type = Column(String(50), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)  # Decimal, can be negative
    currency = Column(String(3), nullable=False)
    reason = Column(Text, nullable=False)
    effective_period = Column(String(20), nullable=False)  # e.g. "2026-10"
    status = Column(String(30), default=PayrollAdjustmentStatus.PENDING.value, nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ===========================================================================
# 12. Payroll Reconciliation
# ===========================================================================

class PayrollReconciliation(Base):
    """Reconciliation record verifying run totals against expected figures."""
    __tablename__ = "payroll_reconciliations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    payroll_calendar_id = Column(String, ForeignKey("payroll_calendars.id"), nullable=False, unique=True, index=True)
    expected_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    calculated_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    variance = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(30), default=PayrollReconciliationStatus.PENDING.value, nullable=False)
    reconciliation_reference = Column(Text, nullable=True)
    finance_journal_id = Column(String, ForeignKey("payroll_journals.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    calendar = relationship("PayrollCalendar", back_populates="reconciliation")


# ===========================================================================
# 13. Global Payslip Record
# ===========================================================================

class GlobalPayslipRecord(Base):
    """Employee access record for generated global payslips."""
    __tablename__ = "global_payslip_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    payroll_result_id = Column(String, ForeignKey("global_payroll_results.id"), nullable=False, unique=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    document_reference = Column(String(255), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(30), default=GlobalPayslipStatus.AVAILABLE.value, nullable=False)

    payroll_result = relationship("GlobalPayrollResult", back_populates="payslip")
