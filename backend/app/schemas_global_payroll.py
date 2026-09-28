"""
schemas_global_payroll.py - Module 21: Global Payroll & Multi-Country Workforce Platform Schemas
Zeramai Enterprise HRMS
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models_global_payroll import (
    CountryPayrollStatus,
    PayrollFrequency,
    PayrollCalendarStatus,
    GlobalPayComponentType,
    PayrollInputSource,
    CountryPayrollRuleType,
    GlobalPayrollResultStatus,
    FXRateSource,
    AssignmentPayrollStatus,
    PayrollAdjustmentType,
    PayrollAdjustmentStatus,
    PayrollReconciliationStatus,
    GlobalPayslipStatus,
)


# ===========================================================================
# 1. Payroll Country
# ===========================================================================

class PayrollCountryCreate(BaseModel):
    country_code: str = Field(..., max_length=3, description="ISO-3 Country Code (e.g. IND, USA, GBR)")
    country_name: str
    default_currency: str = Field(..., max_length=3, description="ISO-3 Currency Code (e.g. INR, USD, GBP)")
    timezone: str = "UTC"
    active: bool = True
    payroll_enabled: bool = True
    adapter_status: CountryPayrollStatus = CountryPayrollStatus.CONFIGURED_ONLY


class PayrollCountryUpdate(BaseModel):
    country_name: Optional[str] = None
    default_currency: Optional[str] = None
    timezone: Optional[str] = None
    active: Optional[bool] = None
    payroll_enabled: Optional[bool] = None
    adapter_status: Optional[CountryPayrollStatus] = None


class PayrollCountryResponse(BaseModel):
    id: str
    tenant_id: str
    country_code: str
    country_name: str
    default_currency: str
    timezone: str
    active: bool
    payroll_enabled: bool
    adapter_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 2. Global Payroll Configuration
# ===========================================================================

class GlobalPayrollConfigurationCreate(BaseModel):
    legal_entity_id: str
    country_id: str
    default_currency: str = Field(..., max_length=3)
    timezone: str = "UTC"
    payroll_frequency: PayrollFrequency = PayrollFrequency.MONTHLY
    payroll_day: int = Field(28, ge=1, le=31)
    cutoff_day: int = Field(20, ge=1, le=31)
    adapter_code: str = "GENERIC_INTERNATIONAL_ADAPTER"
    active: bool = True


class GlobalPayrollConfigurationUpdate(BaseModel):
    default_currency: Optional[str] = None
    timezone: Optional[str] = None
    payroll_frequency: Optional[PayrollFrequency] = None
    payroll_day: Optional[int] = None
    cutoff_day: Optional[int] = None
    adapter_code: Optional[str] = None
    active: Optional[bool] = None


class GlobalPayrollConfigurationResponse(BaseModel):
    id: str
    tenant_id: str
    legal_entity_id: str
    country_id: str
    default_currency: str
    timezone: str
    payroll_frequency: str
    payroll_day: int
    cutoff_day: int
    adapter_code: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 3. Payroll Pay Group
# ===========================================================================

class PayrollPayGroupCreate(BaseModel):
    payroll_configuration_id: str
    name: str
    code: str = Field(..., max_length=50)
    description: Optional[str] = None
    currency: str = Field(..., max_length=3)
    frequency: PayrollFrequency = PayrollFrequency.MONTHLY
    active: bool = True


class PayrollPayGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    frequency: Optional[PayrollFrequency] = None
    active: Optional[bool] = None


class PayrollPayGroupResponse(BaseModel):
    id: str
    tenant_id: str
    payroll_configuration_id: str
    name: str
    code: str
    description: Optional[str] = None
    currency: str
    frequency: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 4. Payroll Calendar (Pay Periods)
# ===========================================================================

class PayrollCalendarCreate(BaseModel):
    pay_group_id: str
    period_start: date
    period_end: date
    cutoff_date: date
    pay_date: date
    status: PayrollCalendarStatus = PayrollCalendarStatus.OPEN


class PayrollCalendarUpdate(BaseModel):
    cutoff_date: Optional[date] = None
    pay_date: Optional[date] = None
    status: Optional[PayrollCalendarStatus] = None


class PayrollCalendarResponse(BaseModel):
    id: str
    tenant_id: str
    pay_group_id: str
    period_start: date
    period_end: date
    cutoff_date: date
    pay_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 5. Global Pay Component
# ===========================================================================

class GlobalPayComponentCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    component_type: GlobalPayComponentType
    taxable: bool = True
    pensionable: bool = True
    recurring: bool = True
    country_code: Optional[str] = None
    description: Optional[str] = None
    active: bool = True


class GlobalPayComponentUpdate(BaseModel):
    name: Optional[str] = None
    taxable: Optional[bool] = None
    pensionable: Optional[bool] = None
    recurring: Optional[bool] = None
    country_code: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class GlobalPayComponentResponse(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    component_type: str
    taxable: bool
    pensionable: bool
    recurring: bool
    country_code: Optional[str] = None
    description: Optional[str] = None
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 6. Payroll Input
# ===========================================================================

class PayrollInputCreate(BaseModel):
    payroll_calendar_id: str
    person_id: str
    pay_component_id: str
    amount: Decimal = Field(..., max_digits=15, decimal_places=2)
    currency: str = Field(..., max_length=3)
    source: PayrollInputSource = PayrollInputSource.MANUAL
    reference: Optional[str] = None
    effective_date: Optional[date] = None


class PayrollInputUpdate(BaseModel):
    amount: Optional[Decimal] = None
    reference: Optional[str] = None
    effective_date: Optional[date] = None


class PayrollInputResponse(BaseModel):
    id: str
    tenant_id: str
    payroll_calendar_id: str
    person_id: str
    pay_component_id: str
    amount: Decimal
    currency: str
    source: str
    reference: Optional[str] = None
    effective_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 7. Country Payroll Rule
# ===========================================================================

class CountryPayrollRuleCreate(BaseModel):
    country_code: str = Field(..., max_length=3)
    rule_code: str = Field(..., max_length=50)
    rule_name: str
    rule_type: CountryPayrollRuleType
    configuration_reference: Optional[Dict[str, Any]] = None
    effective_from: date
    effective_to: Optional[date] = None
    active: bool = True
    version: int = 1


class CountryPayrollRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    configuration_reference: Optional[Dict[str, Any]] = None
    effective_to: Optional[date] = None
    active: Optional[bool] = None
    version: Optional[int] = None


class CountryPayrollRuleResponse(BaseModel):
    id: str
    tenant_id: str
    country_code: str
    rule_code: str
    rule_name: str
    rule_type: str
    configuration_reference: Optional[Dict[str, Any]] = None
    effective_from: date
    effective_to: Optional[date] = None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 8. Employee Payroll Assignment
# ===========================================================================

class EmployeePayrollAssignmentCreate(BaseModel):
    person_id: str
    legal_entity_id: str
    country_code: str = Field(..., max_length=3)
    pay_group_id: str
    currency: str = Field(..., max_length=3)
    effective_from: date
    effective_to: Optional[date] = None
    payroll_status: AssignmentPayrollStatus = AssignmentPayrollStatus.ACTIVE
    split_ratio: Decimal = Decimal("100.00")


class EmployeePayrollAssignmentUpdate(BaseModel):
    effective_to: Optional[date] = None
    payroll_status: Optional[AssignmentPayrollStatus] = None
    split_ratio: Optional[Decimal] = None


class EmployeePayrollAssignmentResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    legal_entity_id: str
    country_code: str
    pay_group_id: str
    currency: str
    effective_from: date
    effective_to: Optional[date] = None
    payroll_status: str
    split_ratio: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 9. Multi-Currency FX Rates
# ===========================================================================

class PayrollExchangeRateCreate(BaseModel):
    base_currency: str = Field(..., max_length=3)
    quote_currency: str = Field(..., max_length=3)
    rate: Decimal = Field(..., max_digits=14, decimal_places=6)
    effective_date: Optional[date] = None
    source: FXRateSource = FXRateSource.CONFIGURED


class PayrollExchangeRateResponse(BaseModel):
    id: str
    tenant_id: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    effective_date: date
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 10. Global Payroll Result & Calculation
# ===========================================================================

class PayrollResultComponentResponse(BaseModel):
    id: str
    payroll_result_id: str
    pay_component_id: Optional[str] = None
    component_code: str
    component_name: str
    component_type: str
    amount: Decimal
    currency: str
    calculation_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GlobalPayrollResultResponse(BaseModel):
    id: str
    tenant_id: str
    payroll_calendar_id: str
    person_id: str
    currency: str
    gross: Decimal
    taxable_gross: Decimal
    employee_deductions: Decimal
    employer_contributions: Decimal
    tax: Decimal
    adjustments: Decimal
    net_pay: Decimal
    calculation_status: str
    fx_rate_used: Decimal
    base_currency: Optional[str] = None
    base_net_pay: Optional[Decimal] = None
    calculation_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    components: Optional[List[PayrollResultComponentResponse]] = None

    class Config:
        from_attributes = True


class CalculatePayrollRequest(BaseModel):
    recalculate_existing: bool = False
    person_ids: Optional[List[str]] = None


class PayrollRunSummaryResponse(BaseModel):
    calendar_id: str
    pay_group_id: str
    pay_group_name: str
    country_code: str
    currency: str
    status: str
    period_start: date
    period_end: date
    pay_date: date
    total_employees: int
    total_gross: Decimal
    total_net_pay: Decimal
    total_employee_deductions: Decimal
    total_employer_contributions: Decimal
    total_tax: Decimal
    total_adjustments: Decimal
    is_reconciled: bool
    results: Optional[List[GlobalPayrollResultResponse]] = None


# ===========================================================================
# 11. Payroll Adjustments
# ===========================================================================

class PayrollAdjustmentCreate(BaseModel):
    person_id: str
    original_payroll_result_id: Optional[str] = None
    adjustment_type: PayrollAdjustmentType
    amount: Decimal = Field(..., max_digits=15, decimal_places=2)
    currency: str = Field(..., max_length=3)
    reason: str
    effective_period: str = Field(..., description="e.g. 2026-10")


class PayrollAdjustmentResponse(BaseModel):
    id: str
    tenant_id: str
    person_id: str
    original_payroll_result_id: Optional[str] = None
    adjustment_type: str
    amount: Decimal
    currency: str
    reason: str
    effective_period: str
    status: str
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 12. Payroll Reconciliation
# ===========================================================================

class PayrollReconciliationResponse(BaseModel):
    id: str
    tenant_id: str
    payroll_calendar_id: str
    expected_total: Decimal
    calculated_total: Decimal
    variance: Decimal
    currency: str
    status: str
    reconciliation_reference: Optional[str] = None
    finance_journal_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 13. Global Payslip
# ===========================================================================

class GlobalPayslipRecordResponse(BaseModel):
    id: str
    tenant_id: str
    payroll_result_id: str
    person_id: str
    document_reference: Optional[str] = None
    generated_at: datetime
    currency: str
    status: str
    gross: Optional[Decimal] = None
    net_pay: Optional[Decimal] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    pay_group_name: Optional[str] = None

    class Config:
        from_attributes = True


# ===========================================================================
# 14. International Provider Integration
# ===========================================================================

class ProviderPayrollSubmissionRequest(BaseModel):
    provider_code: str
    calendar_id: str
    environment: str = "SANDBOX"


class ProviderPayrollSubmissionResponse(BaseModel):
    batch_reference: str
    provider_code: str
    status: str  # SUBMITTED, IN_REVIEW, COMPLETED, REJECTED
    message: str
    submitted_at: datetime
    records_count: int


# ===========================================================================
# 15. Dashboard & Analytics
# ===========================================================================

class PayrollCostByCountryItem(BaseModel):
    country_code: str
    country_name: str
    currency: str
    employee_count: int
    total_gross: Decimal
    total_net: Decimal
    total_employer_cost: Decimal


class PayrollExceptionItem(BaseModel):
    calendar_id: str
    pay_group_name: str
    country_code: str
    issue_type: str
    description: str
    severity: str  # HIGH, MEDIUM, LOW


class GlobalPayrollDashboardResponse(BaseModel):
    total_countries: int
    active_countries: int
    total_pay_groups: int
    open_calendars: int
    pending_approvals: int
    total_active_assignments: int
    total_global_workforce_cost_usd: Decimal
    cost_by_country: List[PayrollCostByCountryItem]
    exceptions: List[PayrollExceptionItem]
