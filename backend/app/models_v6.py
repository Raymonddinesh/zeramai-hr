"""
models_v6.py – Phase 5 (Leave Engine) + Phase 6 (Payroll Engine)

Phase 5: LeavePolicy, LeaveBalance, LeaveAccrual, CompOffRequest
Phase 6: PayrollComponent, SalaryStructure, PayrollRun, Payslip
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Phase 5 — Leave Engine
# ===========================================================================

class AccrualFrequency(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    NONE = "none"  # Fixed grant at start


class LeavePolicy(Base):
    """Configurable leave policy per leave type."""
    __tablename__ = "leave_policies"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)  # e.g. "Casual Leave India 2026"
    leave_type = Column(String, nullable=False)          # casual, sick, earned, etc.
    annual_quota = Column(Float, nullable=False)          # Total days per year
    accrual_frequency = Column(Enum(AccrualFrequency), default=AccrualFrequency.MONTHLY)
    max_carry_forward = Column(Float, default=0)
    max_consecutive_days = Column(Integer, default=30)
    requires_attachment = Column(Boolean, default=False)  # e.g. sick leave > 2 days
    attachment_after_days = Column(Integer, default=2)
    applicable_from = Column(Date, nullable=True)
    applicable_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LeaveBalance(Base):
    """Per-person, per-leave-type balance tracking."""
    __tablename__ = "leave_balances"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    leave_policy_id = Column(String, ForeignKey("leave_policies.id"), nullable=False)
    year = Column(Integer, nullable=False)  # e.g. 2026
    total_entitled = Column(Float, nullable=False, default=0)
    used = Column(Float, nullable=False, default=0)
    carry_forward = Column(Float, nullable=False, default=0)
    remaining = Column(Float, nullable=False, default=0)  # computed
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompOffStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CompOffRequest(Base):
    """Compensatory off request for working on holidays/weekends."""
    __tablename__ = "comp_off_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    worked_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    comp_off_date = Column(Date, nullable=True)  # When they want to take off
    status = Column(Enum(CompOffStatus), default=CompOffStatus.PENDING, nullable=False)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    expiry_date = Column(Date, nullable=True)    # Comp-offs expire after X days
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ===========================================================================
# Phase 6 — Payroll Engine
# ===========================================================================

class ComponentType(str, enum.Enum):
    EARNING = "earning"
    DEDUCTION = "deduction"
    EMPLOYER_CONTRIBUTION = "employer_contribution"


class PayrollComponent(Base):
    """Payroll component definition (e.g. Basic, HRA, PF, Tax)."""
    __tablename__ = "payroll_components"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=False, unique=True)  # e.g. "BASIC", "HRA", "PF"
    component_type = Column(Enum(ComponentType), nullable=False)
    is_taxable = Column(Boolean, default=True)
    is_statutory = Column(Boolean, default=False)     # PF, ESI, etc.
    calculation_type = Column(String, default="fixed") # fixed, percentage, formula
    percentage_of = Column(String, nullable=True)     # "BASIC" if calc is percentage
    default_value = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SalaryStructure(Base):
    """Salary structure assignment for a person."""
    __tablename__ = "salary_structures"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    name = Column(String, nullable=False)         # e.g. "CTC 2026"
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    ctc_annual = Column(Numeric(14, 2), nullable=False)
    ctc_monthly = Column(Numeric(12, 2), nullable=False)
    components_json = Column(JSON, nullable=False)  # [{"code":"BASIC","amount":50000},...]
    currency = Column(String, default="INR")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPUTED = "computed"
    APPROVED = "approved"
    DISBURSED = "disbursed"
    REVERSED = "reversed"


class PayrollRun(Base):
    """Monthly payroll run."""
    __tablename__ = "payroll_runs"

    id = Column(String, primary_key=True, default=gen_uuid)
    month = Column(String, nullable=False)     # "2026-09"
    status = Column(Enum(PayrollRunStatus), default=PayrollRunStatus.DRAFT, nullable=False)
    total_gross = Column(Numeric(14, 2), default=0)
    total_deductions = Column(Numeric(14, 2), default=0)
    total_net = Column(Numeric(14, 2), default=0)
    employee_count = Column(Integer, default=0)
    processed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payslip(Base):
    """Individual payslip per employee per run."""
    __tablename__ = "payslips"

    id = Column(String, primary_key=True, default=gen_uuid)
    payroll_run_id = Column(String, ForeignKey("payroll_runs.id"), nullable=False)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    month = Column(String, nullable=False)
    gross_salary = Column(Numeric(12, 2), nullable=False)
    total_deductions = Column(Numeric(12, 2), nullable=False)
    net_salary = Column(Numeric(12, 2), nullable=False)
    earnings_json = Column(JSON, nullable=True)      # [{"code":"BASIC","amount":50000},...]
    deductions_json = Column(JSON, nullable=True)     # [{"code":"PF","amount":6000},...]
    working_days = Column(Integer, nullable=True)
    days_paid = Column(Integer, nullable=True)
    lop_days = Column(Float, default=0)               # Loss of pay
    currency = Column(String, default="INR")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person")
