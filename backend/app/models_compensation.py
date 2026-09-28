"""
models_compensation.py - Module 7: Compensation & Benefits Management Models.

Defines:
- CompensationRevision: Effective-dated salary revision proposals and lifecycle.
- BonusIncentive: One-time or recurring bonus/incentive records linked to payroll.
- BenefitPlan: Configurable corporate benefits (health, life, retirement, wellness).
- BenefitEnrollment: Employee benefit enrollments, coverage tiers, and contribution breakdown.
"""
import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Compensation Enums
# ===========================================================================

class RevisionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EFFECTIVE = "effective"


class RevisionReason(str, enum.Enum):
    ANNUAL_REVIEW = "annual_review"
    PROMOTION = "promotion"
    MARKET_ADJUSTMENT = "market_adjustment"
    RETENTION = "retention"
    PROBATION_CONFIRMATION = "probation_confirmation"
    AD_HOC = "ad_hoc"


class BonusType(str, enum.Enum):
    PERFORMANCE = "performance"
    RETENTION = "retention"
    SALES_INCENTIVE = "sales_incentive"
    SPOT_AWARD = "spot_award"
    ANNUAL = "annual"
    SIGNING = "signing"


class BonusStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class BenefitType(str, enum.Enum):
    HEALTH_INSURANCE = "health_insurance"
    LIFE_INSURANCE = "life_insurance"
    RETIREMENT = "retirement"
    WELLNESS = "wellness"
    MEAL_BENEFIT = "meal_benefit"
    TRANSPORT = "transport"
    OTHER = "other"


class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    PENDING = "pending"
    TERMINATED = "terminated"
    WAIVED = "waived"


# ===========================================================================
# Compensation Revision & Effective-Dated Records
# ===========================================================================

class CompensationRevision(Base):
    """
    Effective-dated compensation revision workflow.
    DRAFT -> SUBMITTED -> UNDER_REVIEW -> APPROVED / REJECTED -> EFFECTIVE.
    When APPROVED/EFFECTIVE, it produces/updates active SalaryStructure and EmploymentHistory.
    """
    __tablename__ = "compensation_revisions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)

    previous_salary_structure_id = Column(String, ForeignKey("salary_structures.id"), nullable=True)
    previous_ctc_annual = Column(Numeric(14, 2), nullable=True)
    
    new_ctc_annual = Column(Numeric(14, 2), nullable=False)
    new_ctc_monthly = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    components_json = Column(JSON, nullable=False)  # list of {code, name, amount, type}

    effective_date = Column(Date, nullable=False)
    reason = Column(Enum(RevisionReason), default=RevisionReason.ANNUAL_REVIEW, nullable=False)
    business_justification = Column(Text, nullable=True)
    hr_notes = Column(Text, nullable=True)  # Confidential HR notes, hidden from employees
    rejection_reason = Column(Text, nullable=True)

    status = Column(Enum(RevisionStatus), default=RevisionStatus.DRAFT, nullable=False)

    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    recommended_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    resulting_salary_structure_id = Column(String, ForeignKey("salary_structures.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    person = relationship("Person")
    created_by = relationship("User", foreign_keys=[created_by_id])
    recommended_by = relationship("User", foreign_keys=[recommended_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])


# ===========================================================================
# Bonus & Incentive Records
# ===========================================================================

class BonusIncentive(Base):
    """
    Controlled bonus and incentive records linked into payroll runs.
    """
    __tablename__ = "bonus_incentives"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)

    bonus_type = Column(Enum(BonusType), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    pay_period = Column(String(7), nullable=False)  # "YYYY-MM"
    effective_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)

    status = Column(Enum(BonusStatus), default=BonusStatus.DRAFT, nullable=False)
    payroll_status = Column(String(20), default="pending", nullable=False)  # "pending", "processed"

    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    person = relationship("Person")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])


# ===========================================================================
# Benefits Foundation Models
# ===========================================================================

class BenefitPlan(Base):
    """
    Configurable company benefit plans.
    """
    __tablename__ = "benefit_plans"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    benefit_type = Column(Enum(BenefitType), nullable=False)
    provider = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    employer_contribution = Column(Numeric(10, 2), default=0.0, nullable=False)
    employee_deduction = Column(Numeric(10, 2), default=0.0, nullable=False)
    coverage_details = Column(JSON, nullable=True)
    eligibility_criteria = Column(JSON, nullable=True)  # e.g. {"employment_type": ["full_time_employee"]}

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    enrollments = relationship("BenefitEnrollment", back_populates="benefit_plan")


class BenefitEnrollment(Base):
    """
    Per-employee enrollment into a benefit plan.
    """
    __tablename__ = "benefit_enrollments"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    benefit_plan_id = Column(String, ForeignKey("benefit_plans.id"), nullable=False)

    coverage_tier = Column(String(50), default="employee_only", nullable=False)
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED, nullable=False)

    employee_contribution = Column(Numeric(10, 2), default=0.0, nullable=False)
    employer_contribution = Column(Numeric(10, 2), default=0.0, nullable=False)

    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    enrolled_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    person = relationship("Person")
    benefit_plan = relationship("BenefitPlan", back_populates="enrollments")
    enrolled_by = relationship("User", foreign_keys=[enrolled_by_id])
