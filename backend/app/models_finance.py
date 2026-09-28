"""
models_finance.py - Module 16: Enterprise Finance, Billing & Workforce Cost Management Data Models.

Canonical models for:
- FinancialDimension & FinancialDimensionValue
- EmployeeCostAllocation
- GLAccount & GLMapping
- PayrollJournal & PayrollJournalLine
- WorkforceCostRecord
- ExpenseAccountingEntry
- AccrualRule & AccrualRecord
- WorkforceBudget & WorkforceBudgetLine
- Vendor, VendorContract, VendorInvoice
"""
import enum
import uuid
from datetime import datetime, date
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
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DimensionType(str, enum.Enum):
    COST_CENTER = "COST_CENTER"
    DEPARTMENT = "DEPARTMENT"
    LOCATION = "LOCATION"
    LEGAL_ENTITY = "LEGAL_ENTITY"
    PROJECT = "PROJECT"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    REGION = "REGION"
    CUSTOM = "CUSTOM"


class CostAllocationType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    PROJECT = "PROJECT"
    TEMPORARY = "TEMPORARY"


class GLAccountType(str, enum.Enum):
    EXPENSE = "EXPENSE"
    LIABILITY = "LIABILITY"
    ASSET = "ASSET"
    REVENUE = "REVENUE"
    EQUITY = "EQUITY"
    OTHER = "OTHER"


class GLTransactionType(str, enum.Enum):
    SALARY = "SALARY"
    BONUS = "BONUS"
    EMPLOYER_EPF = "EMPLOYER_EPF"
    EMPLOYER_ESI = "EMPLOYER_ESI"
    PROFESSIONAL_TAX = "PROFESSIONAL_TAX"
    TDS = "TDS"
    BENEFITS = "BENEFITS"
    REIMBURSEMENT = "REIMBURSEMENT"
    TRAVEL = "TRAVEL"
    LEAVE_ENCASHMENT = "LEAVE_ENCASHMENT"
    GRATUITY = "GRATUITY"
    OTHER_PAYROLL_COST = "OTHER_PAYROLL_COST"


class PayrollJournalStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    POSTED = "POSTED"
    EXPORTED = "EXPORTED"
    CANCELLED = "CANCELLED"


class ExpenseAccountingStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCOUNTED = "ACCOUNTED"
    EXPORTED = "EXPORTED"
    CANCELLED = "CANCELLED"


class AccrualType(str, enum.Enum):
    BONUS = "BONUS"
    LEAVE = "LEAVE"
    BENEFIT = "BENEFIT"
    GRATUITY = "GRATUITY"
    OTHER = "OTHER"


class AccrualStatus(str, enum.Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class BudgetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"
    CLOSED = "CLOSED"


class BudgetCategory(str, enum.Enum):
    SALARY = "SALARY"
    BONUS = "BONUS"
    BENEFITS = "BENEFITS"
    STATUTORY = "STATUTORY"
    REIMBURSEMENT = "REIMBURSEMENT"
    TRAVEL = "TRAVEL"
    TRAINING = "TRAINING"
    RECRUITMENT = "RECRUITMENT"
    OTHER = "OTHER"


class VendorCategory(str, enum.Enum):
    STAFFING = "STAFFING"
    SOFTWARE = "SOFTWARE"
    CONSULTING = "CONSULTING"
    FACILITIES = "FACILITIES"
    BENEFITS = "BENEFITS"
    OTHER = "OTHER"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# 1. Financial Dimensions
# ---------------------------------------------------------------------------

class FinancialDimension(Base):
    """Financial tracking dimension (e.g. Cost Center, Project, Business Unit)."""
    __tablename__ = "financial_dimensions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    dimension_type = Column(String(50), nullable=False, default=DimensionType.COST_CENTER.value)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    values = relationship("FinancialDimensionValue", back_populates="dimension", cascade="all, delete-orphan")


class FinancialDimensionValue(Base):
    """Hierarchical values assigned to a dimension (e.g. CC-1001 under Corporate)."""
    __tablename__ = "financial_dimension_values"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    dimension_id = Column(String, ForeignKey("financial_dimensions.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(String, ForeignKey("financial_dimension_values.id"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    dimension = relationship("FinancialDimension", back_populates="values")
    parent = relationship("FinancialDimensionValue", remote_side=[id])


# ---------------------------------------------------------------------------
# 2. Employee Cost Allocation
# ---------------------------------------------------------------------------

class EmployeeCostAllocation(Base):
    """Percentage attribution of an employee's workforce cost across cost centers."""
    __tablename__ = "employee_cost_allocations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True, index=True)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=False, index=True)
    percentage = Column(Numeric(5, 2), nullable=False)  # e.g. 50.00%
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    allocation_type = Column(String(50), nullable=False, default=CostAllocationType.PRIMARY.value)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 3. General Ledger (GL) Accounts & Mappings
# ---------------------------------------------------------------------------

class GLAccount(Base):
    """Chart of Accounts (COA) General Ledger account for payroll & workforce accounting."""
    __tablename__ = "gl_accounts"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    account_type = Column(String(50), nullable=False, default=GLAccountType.EXPENSE.value)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class GLMapping(Base):
    """Mapping rules from payroll line items / statutory deductions to debit & credit GL accounts."""
    __tablename__ = "gl_mappings"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False, index=True)  # SALARY, BONUS, EMPLOYER_EPF, etc.
    source_type = Column(String(50), nullable=True)
    source_code = Column(String(50), nullable=True)
    debit_account_id = Column(String, ForeignKey("gl_accounts.id"), nullable=False)
    credit_account_id = Column(String, ForeignKey("gl_accounts.id"), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    debit_account = relationship("GLAccount", foreign_keys=[debit_account_id])
    credit_account = relationship("GLAccount", foreign_keys=[credit_account_id])


# ---------------------------------------------------------------------------
# 4. Payroll Accounting Journals
# ---------------------------------------------------------------------------

class PayrollJournal(Base):
    """Balanced double-entry accounting journal generated from payroll runs."""
    __tablename__ = "payroll_journals"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    payroll_run_id = Column(String, ForeignKey("payroll_runs.id"), nullable=True, index=True)
    journal_number = Column(String(100), nullable=False, index=True)
    accounting_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default=PayrollJournalStatus.DRAFT.value, nullable=False, index=True)
    total_debit = Column(Numeric(15, 2), default=0.0, nullable=False)
    total_credit = Column(Numeric(15, 2), default=0.0, nullable=False)
    posted_at = Column(DateTime, nullable=True)
    posted_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("PayrollJournalLine", back_populates="journal", cascade="all, delete-orphan")


class PayrollJournalLine(Base):
    """Individual debit or credit journal entry line item."""
    __tablename__ = "payroll_journal_lines"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    journal_id = Column(String, ForeignKey("payroll_journals.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("gl_accounts.id"), nullable=False, index=True)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True, index=True)
    dimension_reference = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    debit = Column(Numeric(15, 2), default=0.0, nullable=False)
    credit = Column(Numeric(15, 2), default=0.0, nullable=False)
    person_reference = Column(String, ForeignKey("persons.id"), nullable=True)
    source_type = Column(String(50), nullable=True)  # EARNING, DEDUCTION, STATUTORY, EXPENSE
    source_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    journal = relationship("PayrollJournal", back_populates="lines")
    account = relationship("GLAccount")


# ---------------------------------------------------------------------------
# 5. Workforce Cost Records
# ---------------------------------------------------------------------------

class WorkforceCostRecord(Base):
    """Normalized workforce cost attribution combining wages, employer statutory, benefits and expenses."""
    __tablename__ = "workforce_cost_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True, index=True)
    payroll_run_id = Column(String, ForeignKey("payroll_runs.id"), nullable=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_salary = Column(Numeric(15, 2), default=0.0, nullable=False)
    bonus = Column(Numeric(15, 2), default=0.0, nullable=False)
    employer_statutory_cost = Column(Numeric(15, 2), default=0.0, nullable=False)
    benefits_cost = Column(Numeric(15, 2), default=0.0, nullable=False)
    reimbursement_cost = Column(Numeric(15, 2), default=0.0, nullable=False)
    leave_cost = Column(Numeric(15, 2), default=0.0, nullable=True)
    other_cost = Column(Numeric(15, 2), default=0.0, nullable=False)
    total_cost = Column(Numeric(15, 2), default=0.0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 6. Expense Accounting Linkage
# ---------------------------------------------------------------------------

class ExpenseAccountingEntry(Base):
    """Linkage between employee expense claims / reimbursements and finance accounting journals."""
    __tablename__ = "expense_accounting_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    expense_claim_id = Column(String(100), nullable=True, index=True)
    reimbursement_id = Column(String(100), nullable=True)
    source_type = Column(String(50), nullable=True)
    source_reference_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    gl_account_id = Column(String, ForeignKey("gl_accounts.id"), nullable=False)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    accounting_date = Column(Date, nullable=False)
    status = Column(String(50), default=ExpenseAccountingStatus.PENDING.value, nullable=False, index=True)
    journal_id = Column(String, ForeignKey("payroll_journals.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 7. Accruals & Provisions
# ---------------------------------------------------------------------------

class AccrualRule(Base):
    """Rule definition for workforce cost provisions and accruals (e.g. bonus, leave, gratuity)."""
    __tablename__ = "accrual_rules"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    accrual_type = Column(String(50), nullable=False, default=AccrualType.BONUS.value)
    calculation_method = Column(String(50), default="FIXED_MONTHLY", nullable=False)
    frequency = Column(String(50), default="MONTHLY", nullable=False)
    account_id = Column(String, ForeignKey("gl_accounts.id"), nullable=False)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    records = relationship("AccrualRecord", back_populates="rule", cascade="all, delete-orphan")


class AccrualRecord(Base):
    """Periodic accrual amount calculated per rule."""
    __tablename__ = "accrual_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, ForeignKey("accrual_rules.id"), nullable=False, index=True)
    period = Column(String(50), nullable=False)  # e.g. "2026-09"
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default=AccrualStatus.PENDING.value, nullable=False)
    journal_id = Column(String, ForeignKey("payroll_journals.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rule = relationship("AccrualRule", back_populates="records")


# ---------------------------------------------------------------------------
# 8. Workforce Budgeting
# ---------------------------------------------------------------------------

class WorkforceBudget(Base):
    """Fiscal year workforce budget allocation plan."""
    __tablename__ = "workforce_budgets"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    name = Column(String(255), nullable=False)
    fiscal_year = Column(String(20), nullable=False)  # e.g. "FY2026-27"
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default=BudgetStatus.DRAFT.value, nullable=False, index=True)
    total_budget = Column(Numeric(15, 2), default=0.0, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("WorkforceBudgetLine", back_populates="budget", cascade="all, delete-orphan")


class WorkforceBudgetLine(Base):
    """Detailed monthly budget line broken down by cost center and category."""
    __tablename__ = "workforce_budget_lines"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    budget_id = Column(String, ForeignKey("workforce_budgets.id"), nullable=False, index=True)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=False, index=True)
    department_id = Column(String, nullable=True)
    category = Column(String(50), nullable=False, default=BudgetCategory.SALARY.value)
    month = Column(String(20), nullable=False)  # e.g. "2026-09"
    budget_amount = Column(Numeric(15, 2), default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    budget = relationship("WorkforceBudget", back_populates="lines")


# ---------------------------------------------------------------------------
# 9. Vendor & Invoice Tracking
# ---------------------------------------------------------------------------

class Vendor(Base):
    """HR and workforce services vendor (contract staffing, software, benefits providers)."""
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    vendor_code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default=VendorCategory.STAFFING.value)
    tax_identifier = Column(String(50), nullable=True)
    contact_reference = Column(String(255), nullable=True)
    currency = Column(String(10), default="INR", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contracts = relationship("VendorContract", back_populates="vendor", cascade="all, delete-orphan")
    invoices = relationship("VendorInvoice", back_populates="vendor", cascade="all, delete-orphan")


class VendorContract(Base):
    """Recurring services contract associated with a vendor."""
    __tablename__ = "vendor_contracts"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    contract_reference = Column(String(100), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    recurring_amount = Column(Numeric(15, 2), default=0.0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    payment_frequency = Column(String(50), default="MONTHLY", nullable=False)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="contracts")


class VendorInvoice(Base):
    """Payable vendor invoice with cost-center attribution and multi-level approval."""
    __tablename__ = "vendor_invoices"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    invoice_number = Column(String(100), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=0.0, nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    cost_center_id = Column(String, ForeignKey("cost_centers.id"), nullable=True)
    status = Column(String(50), default=InvoiceStatus.DRAFT.value, nullable=False, index=True)
    external_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="invoices")
