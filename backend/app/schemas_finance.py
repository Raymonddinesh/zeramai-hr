"""
schemas_finance.py - Pydantic schemas for Module 16: Enterprise Finance, Billing & Workforce Cost Management.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Financial Dimensions & Dimension Values
# ---------------------------------------------------------------------------

class FinancialDimensionValueBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    parent_id: Optional[str] = None
    active: bool = True


class FinancialDimensionValueCreate(FinancialDimensionValueBase):
    pass


class FinancialDimensionValueResponse(FinancialDimensionValueBase):
    id: str
    tenant_id: str
    dimension_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinancialDimensionBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    dimension_type: str = "COST_CENTER"
    description: Optional[str] = None
    active: bool = True


class FinancialDimensionCreate(FinancialDimensionBase):
    pass


class FinancialDimensionUpdate(BaseModel):
    name: Optional[str] = None
    dimension_type: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class FinancialDimensionResponse(FinancialDimensionBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    values: List[FinancialDimensionValueResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Cost Centers
# ---------------------------------------------------------------------------

class CostCenterBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    legal_entity_id: Optional[str] = None
    manager_person_id: Optional[str] = None
    parent_cost_center_id: Optional[str] = None
    currency: str = "INR"
    active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class CostCenterCreate(CostCenterBase):
    pass


class CostCenterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    legal_entity_id: Optional[str] = None
    manager_person_id: Optional[str] = None
    parent_cost_center_id: Optional[str] = None
    currency: Optional[str] = None
    active: Optional[bool] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class CostCenterResponse(CostCenterBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Employee Cost Allocations
# ---------------------------------------------------------------------------

class EmployeeCostAllocationBase(BaseModel):
    person_id: str
    cost_center_id: str
    engagement_id: Optional[str] = None
    percentage: float = Field(..., ge=0.0, le=100.0)
    effective_from: date
    effective_to: Optional[date] = None
    allocation_type: str = "PRIMARY"


class EmployeeCostAllocationCreate(EmployeeCostAllocationBase):
    pass


class EmployeeCostAllocationUpdate(BaseModel):
    percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    allocation_type: Optional[str] = None


class EmployeeCostAllocationResponse(EmployeeCostAllocationBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    cost_center_code: Optional[str] = None
    cost_center_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# General Ledger Accounts & Mappings
# ---------------------------------------------------------------------------

class GLAccountBase(BaseModel):
    code: Optional[str] = None
    account_code: Optional[str] = None
    name: Optional[str] = None
    account_name: Optional[str] = None
    account_type: str = "EXPENSE"
    normal_balance: Optional[str] = "DEBIT"
    description: Optional[str] = None
    active: bool = True


class GLAccountCreate(GLAccountBase):
    pass


class GLAccountUpdate(BaseModel):
    name: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class GLAccountResponse(GLAccountBase):
    id: str
    tenant_id: str
    code: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GLMappingBase(BaseModel):
    transaction_type: str = Field(..., max_length=50)
    source_type: Optional[str] = None
    source_code: Optional[str] = None
    debit_account_id: str
    credit_account_id: str
    effective_from: date
    effective_to: Optional[date] = None
    active: bool = True


class GLMappingCreate(GLMappingBase):
    pass


class GLMappingUpdate(BaseModel):
    transaction_type: Optional[str] = None
    source_type: Optional[str] = None
    source_code: Optional[str] = None
    debit_account_id: Optional[str] = None
    credit_account_id: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    active: Optional[bool] = None


class GLMappingResponse(GLMappingBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    debit_account_code: Optional[str] = None
    credit_account_code: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Payroll Accounting Journals
# ---------------------------------------------------------------------------

class PayrollJournalLineResponse(BaseModel):
    id: str
    tenant_id: str
    journal_id: str
    account_id: str
    cost_center_id: Optional[str] = None
    dimension_reference: Optional[str] = None
    description: Optional[str] = None
    debit: float
    credit: float
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    person_reference: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_at: datetime
    account_code: Optional[str] = None
    account_name: Optional[str] = None

    class Config:
        from_attributes = True


class PayrollJournalCreate(BaseModel):
    legal_entity_id: Optional[str] = None
    payroll_run_id: Optional[str] = None
    journal_number: Optional[str] = None
    accounting_date: date
    period_start: date
    period_end: date
    currency: str = "INR"


class PayrollJournalResponse(BaseModel):
    id: str
    tenant_id: str
    legal_entity_id: Optional[str] = None
    payroll_run_id: Optional[str] = None
    journal_number: str
    accounting_date: date
    period_start: date
    period_end: date
    currency: str
    status: str
    total_debit: float
    total_credit: float
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    lines: List[PayrollJournalLineResponse] = []

    class Config:
        from_attributes = True


class JournalGenerateRequest(BaseModel):
    payroll_run_id: str
    accounting_date: Optional[date] = None


# ---------------------------------------------------------------------------
# Normalized Workforce Cost Records
# ---------------------------------------------------------------------------

class WorkforceCostRecordResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    engagement_id: Optional[str] = None
    payroll_run_id: Optional[str] = None
    period_start: date
    period_end: date
    base_salary: float
    bonus: float
    employer_statutory_cost: float
    benefits_cost: float
    reimbursement_cost: float
    leave_cost: Optional[float] = None
    other_cost: float
    total_cost: float
    currency: str
    cost_center_id: Optional[str] = None
    cost_center_code: Optional[str] = None
    period_key: Optional[str] = None
    base_salary_amount: Optional[float] = None
    bonus_amount: Optional[float] = None
    employer_statutory_amount: Optional[float] = None
    benefits_amount: Optional[float] = None
    expense_reimbursements_amount: Optional[float] = None
    created_at: datetime
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


class WorkforceCostCalculateRequest(BaseModel):
    payroll_run_id: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


# ---------------------------------------------------------------------------
# Expense Accounting
# ---------------------------------------------------------------------------

class ExpenseAccountingEntryBase(BaseModel):
    expense_claim_id: str
    reimbursement_id: Optional[str] = None
    gl_account_id: str
    cost_center_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    accounting_date: date
    status: str = "PENDING"
    journal_id: Optional[str] = None


class ExpenseAccountingEntryCreate(ExpenseAccountingEntryBase):
    pass


class ExpenseAccountingEntryResponse(ExpenseAccountingEntryBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Accruals & Provisions
# ---------------------------------------------------------------------------

class AccrualRuleBase(BaseModel):
    name: str = Field(..., max_length=255)
    accrual_type: str = "BONUS"
    calculation_method: str = "FIXED_MONTHLY"
    frequency: str = "MONTHLY"
    account_id: str
    cost_center_id: Optional[str] = None
    active: bool = True
    effective_from: date
    effective_to: Optional[date] = None


class AccrualRuleCreate(AccrualRuleBase):
    pass


class AccrualRuleUpdate(BaseModel):
    name: Optional[str] = None
    calculation_method: Optional[str] = None
    frequency: Optional[str] = None
    account_id: Optional[str] = None
    cost_center_id: Optional[str] = None
    active: Optional[bool] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class AccrualRecordResponse(BaseModel):
    id: str
    tenant_id: str
    rule_id: str
    period: str
    amount: float
    currency: str
    status: str
    journal_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AccrualRuleResponse(AccrualRuleBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    records: List[AccrualRecordResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Workforce Budgeting & Budget vs Actual
# ---------------------------------------------------------------------------

class WorkforceBudgetLineBase(BaseModel):
    cost_center_id: str
    department_id: Optional[str] = None
    category: str = "SALARY"
    month: str  # "2026-09"
    budget_amount: float


class WorkforceBudgetLineCreate(WorkforceBudgetLineBase):
    pass


class WorkforceBudgetLineResponse(WorkforceBudgetLineBase):
    id: str
    tenant_id: str
    budget_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkforceBudgetBase(BaseModel):
    name: str = Field(..., max_length=255)
    fiscal_year: str = Field(..., max_length=20)
    legal_entity_id: Optional[str] = None
    currency: str = "INR"
    status: str = "DRAFT"
    total_budget: float = 0.0


class WorkforceBudgetCreate(WorkforceBudgetBase):
    lines: List[WorkforceBudgetLineCreate] = []


class WorkforceBudgetUpdate(BaseModel):
    name: Optional[str] = None
    fiscal_year: Optional[str] = None
    status: Optional[str] = None
    total_budget: Optional[float] = None


class WorkforceBudgetResponse(WorkforceBudgetBase):
    id: str
    tenant_id: str
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: List[WorkforceBudgetLineResponse] = []

    class Config:
        from_attributes = True


class BudgetVsActualItem(BaseModel):
    category: str
    cost_center_id: Optional[str] = None
    cost_center_code: Optional[str] = None
    month: str
    budget: float
    actual: float
    variance: float
    variance_percentage: float


class BudgetVsActualResponse(BaseModel):
    fiscal_year: Optional[str] = None
    month: Optional[str] = None
    total_budget: float
    total_actual: float
    total_variance: float
    total_variance_percentage: float
    breakdown: List[BudgetVsActualItem] = []


# ---------------------------------------------------------------------------
# Payroll Variance Analysis
# ---------------------------------------------------------------------------

class PayrollVarianceMetric(BaseModel):
    metric_name: str
    previous_value: float
    current_value: float
    absolute_change: float
    percentage_change: float
    explanation: Optional[str] = None


class PayrollVarianceResponse(BaseModel):
    previous_period: str
    current_period: str
    metrics: List[PayrollVarianceMetric] = []
    summary: str


# ---------------------------------------------------------------------------
# Vendors, Contracts & Invoices
# ---------------------------------------------------------------------------

class VendorContractBase(BaseModel):
    contract_reference: str = Field(..., max_length=100)
    start_date: date
    end_date: date
    recurring_amount: float
    currency: str = "INR"
    payment_frequency: str = "MONTHLY"
    cost_center_id: Optional[str] = None
    status: str = "ACTIVE"


class VendorContractCreate(VendorContractBase):
    pass


class VendorContractResponse(VendorContractBase):
    id: str
    tenant_id: str
    vendor_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorInvoiceBase(BaseModel):
    vendor_id: Optional[str] = None
    invoice_number: str = Field(..., max_length=100)
    invoice_date: date
    due_date: date
    amount: float
    tax_amount: float = 0.0
    total_amount: float
    currency: str = "INR"
    cost_center_id: Optional[str] = None
    status: str = "DRAFT"
    external_reference: Optional[str] = None
    payment_reference: Optional[str] = None


class VendorInvoiceCreate(VendorInvoiceBase):
    pass


class VendorInvoiceUpdate(BaseModel):
    status: Optional[str] = None
    due_date: Optional[date] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    external_reference: Optional[str] = None


class VendorInvoiceResponse(VendorInvoiceBase):
    id: str
    tenant_id: str
    vendor_id: str
    vendor_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorBase(BaseModel):
    name: str = Field(..., max_length=255)
    vendor_code: Optional[str] = None
    category: str = "STAFFING"
    tax_identifier: Optional[str] = None
    contact_reference: Optional[str] = None
    legal_entity_id: Optional[str] = None
    currency: str = "INR"
    active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    tax_identifier: Optional[str] = None
    contact_reference: Optional[str] = None
    currency: Optional[str] = None
    active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    contracts: List[VendorContractResponse] = []
    invoices: List[VendorInvoiceResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Accounting Export & Dashboard Summary
# ---------------------------------------------------------------------------

class AccountingExportRequest(BaseModel):
    journal_ids: Optional[List[str]] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    export_format: str = "JSON"  # JSON or CSV


class AccountingExportResponse(BaseModel):
    export_id: str
    generated_at: datetime
    export_format: str
    journal_count: int
    total_debit: float
    total_credit: float
    records: List[Dict[str, Any]] = []


class FinanceDashboardMetrics(BaseModel):
    monthly_payroll_cost: float
    employer_statutory_cost: float
    benefits_cost: float
    reimbursement_cost: float
    total_workforce_cost: float
    total_workforce_cost_ytd: Optional[float] = 0.0
    total_budget: float
    total_actual: float
    budget_variance: float
    pending_invoices_count: int
    pending_invoices_amount: float
    total_accruals: float
    cost_centers_count: int
    vendors_count: int
    posted_journals_count: int
