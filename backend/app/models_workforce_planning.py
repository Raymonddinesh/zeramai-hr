"""
models_workforce_planning.py - Module 17: Workforce Planning, Org Design & Strategic Workforce Management
Zeramai Enterprise HRMS
"""
import enum
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, backref

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OrgUnitType(str, enum.Enum):
    COMPANY = "COMPANY"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    DIVISION = "DIVISION"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    FUNCTION = "FUNCTION"
    REGION = "REGION"
    LOCATION = "LOCATION"
    PROJECT = "PROJECT"


class PositionStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class PositionAssignmentType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    ACTING = "ACTING"
    TEMPORARY = "TEMPORARY"


class HeadcountPlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"
    CLOSED = "CLOSED"


class WorkforceGapType(str, enum.Enum):
    SHORTAGE = "SHORTAGE"
    SURPLUS = "SURPLUS"
    BALANCED = "BALANCED"


class SkillGapSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RoleCriticality(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SuccessionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class ReadinessLevel(str, enum.Enum):
    READY_NOW = "READY_NOW"
    READY_1_2_YEARS = "READY_1_2_YEARS"
    READY_2_3_YEARS = "READY_2_3_YEARS"
    DEVELOPMENT_REQUIRED = "DEVELOPMENT_REQUIRED"


class TalentPoolStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class WorkforceScenarioType(str, enum.Enum):
    BASELINE = "BASELINE"
    GROWTH = "GROWTH"
    REDUCTION = "REDUCTION"
    RESTRUCTURE = "RESTRUCTURE"
    EXPANSION = "EXPANSION"
    CONSERVATIVE = "CONSERVATIVE"
    CUSTOM = "CUSTOM"


class HiringPlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MobilityType(str, enum.Enum):
    PROMOTION = "PROMOTION"
    TRANSFER = "TRANSFER"
    LATERAL = "LATERAL"
    ROTATION = "ROTATION"
    PROJECT = "PROJECT"
    TEMPORARY_ASSIGNMENT = "TEMPORARY_ASSIGNMENT"


class MobilityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# 1. Organizational Structure
# ---------------------------------------------------------------------------

class OrganizationUnit(Base):
    __tablename__ = "organization_units"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String(36), ForeignKey("legal_entities.id"), nullable=True)
    parent_id = Column(String(36), ForeignKey("organization_units.id"), nullable=True, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    unit_type = Column(String(32), default=OrgUnitType.DEPARTMENT.value, nullable=False)
    leader_person_id = Column(String(36), ForeignKey("persons.id"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_org_unit_tenant_code"),
        Index("ix_org_units_tenant_active", "tenant_id", "active"),
        Index("ix_org_units_tenant_parent", "tenant_id", "parent_id"),
    )

    children = relationship(
        "OrganizationUnit",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )
    positions = relationship("Position", back_populates="organization_unit", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 2. Position Management
# ---------------------------------------------------------------------------

class Position(Base):
    __tablename__ = "positions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String(36), ForeignKey("legal_entities.id"), nullable=True)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=False, index=True)
    position_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    job_family = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    employment_type = Column(String(50), default="FULL_TIME", nullable=True)
    location = Column(String(100), nullable=True)
    status = Column(String(32), default=PositionStatus.PLANNED.value, nullable=False)
    headcount_capacity = Column(Float, default=1.0, nullable=False)
    filled_count = Column(Float, default=0.0, nullable=False)
    manager_position_id = Column(String(36), ForeignKey("positions.id"), nullable=True, index=True)
    cost_center_id = Column(String(36), ForeignKey("cost_centers.id"), nullable=True)
    budgeted_cost = Column(Float, nullable=True)
    currency = Column(String(10), default="INR", nullable=False)
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "position_code", name="uq_positions_tenant_code"),
        Index("ix_positions_tenant_status", "tenant_id", "status"),
        Index("ix_positions_tenant_org", "tenant_id", "organization_unit_id"),
        Index("ix_positions_tenant_job_family", "tenant_id", "job_family"),
    )

    organization_unit = relationship("OrganizationUnit", back_populates="positions")
    assignments = relationship("PositionAssignment", back_populates="position", cascade="all, delete-orphan")
    subordinates = relationship(
        "Position",
        backref=backref("manager_position", remote_side=[id]),
    )


# ---------------------------------------------------------------------------
# 3. Position Assignment
# ---------------------------------------------------------------------------

class PositionAssignment(Base):
    __tablename__ = "position_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    engagement_id = Column(String(36), ForeignKey("engagements.id"), nullable=True)
    allocation_percentage = Column(Float, default=100.0, nullable=False)
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True)
    assignment_type = Column(String(32), default=PositionAssignmentType.PRIMARY.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_pos_assignments_tenant_person", "tenant_id", "person_id"),
        Index("ix_pos_assignments_tenant_pos", "tenant_id", "position_id"),
        Index("ix_pos_assignments_effective", "tenant_id", "effective_from", "effective_to"),
    )

    position = relationship("Position", back_populates="assignments")


# ---------------------------------------------------------------------------
# 4. Headcount Plan & Lines
# ---------------------------------------------------------------------------

class HeadcountPlan(Base):
    __tablename__ = "headcount_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String(36), ForeignKey("legal_entities.id"), nullable=True)
    name = Column(String(255), nullable=False)
    fiscal_year = Column(String(32), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(32), default=HeadcountPlanStatus.DRAFT.value, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_headcount_plans_tenant_year", "tenant_id", "fiscal_year"),
        Index("ix_headcount_plans_tenant_status", "tenant_id", "status"),
    )

    lines = relationship("HeadcountPlanLine", back_populates="plan", cascade="all, delete-orphan")


class HeadcountPlanLine(Base):
    __tablename__ = "headcount_plan_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("headcount_plans.id"), nullable=False, index=True)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id"), nullable=True)
    job_family = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    month = Column(String(7), nullable=False)  # "2026-04"
    planned_headcount = Column(Float, default=1.0, nullable=False)
    planned_hires = Column(Float, default=0.0, nullable=False)
    planned_exits = Column(Float, default=0.0, nullable=False)
    planned_cost = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("HeadcountPlan", back_populates="lines")


# ---------------------------------------------------------------------------
# 5. Workforce Demand Planning
# ---------------------------------------------------------------------------

class WorkforceDemandPlan(Base):
    __tablename__ = "workforce_demand_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    planning_horizon = Column(String(50), default="1_YEAR", nullable=False)
    methodology = Column(String(100), default="BOTTOM_UP", nullable=False)
    status = Column(String(32), default="DRAFT", nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("WorkforceDemandLine", back_populates="plan", cascade="all, delete-orphan")


class WorkforceDemandLine(Base):
    __tablename__ = "workforce_demand_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("workforce_demand_plans.id"), nullable=False, index=True)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=False)
    job_family = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    period = Column(String(32), nullable=False)  # "2026-Q1" or "2026-04"
    required_headcount = Column(Float, default=1.0, nullable=False)
    required_skills = Column(Text, nullable=True)  # JSON string or description
    estimated_cost = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("WorkforceDemandPlan", back_populates="lines")


# ---------------------------------------------------------------------------
# 6. Workforce Gap Analysis
# ---------------------------------------------------------------------------

class WorkforceGap(Base):
    __tablename__ = "workforce_gaps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan_reference = Column(String(100), nullable=False)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=True)
    job_family = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    period = Column(String(32), nullable=False)
    demand_headcount = Column(Float, default=0.0, nullable=False)
    supply_headcount = Column(Float, default=0.0, nullable=False)
    gap_headcount = Column(Float, default=0.0, nullable=False)
    estimated_cost_gap = Column(Float, default=0.0, nullable=False)
    gap_type = Column(String(32), default=WorkforceGapType.BALANCED.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_wf_gaps_tenant_period", "tenant_id", "period"),
        Index("ix_wf_gaps_tenant_type", "tenant_id", "gap_type"),
    )


# ---------------------------------------------------------------------------
# 7. Skills Inventory & Employee Skills
# ---------------------------------------------------------------------------

class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="TECHNICAL", nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    levels = relationship("SkillLevel", back_populates="skill", cascade="all, delete-orphan")


class SkillLevel(Base):
    __tablename__ = "skill_levels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False, index=True)
    code = Column(String(32), nullable=False)
    name = Column(String(100), nullable=False)
    rank = Column(Integer, default=1, nullable=False)
    description = Column(Text, nullable=True)

    skill = relationship("Skill", back_populates="levels")


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False, index=True)
    skill_level_id = Column(String(36), ForeignKey("skill_levels.id"), nullable=True)
    proficiency = Column(Float, default=1.0, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    source = Column(String(50), default="SELF_REPORTED", nullable=False)
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_emp_skills_tenant_person", "tenant_id", "person_id"),
        Index("ix_emp_skills_tenant_skill", "tenant_id", "skill_id"),
    )


# ---------------------------------------------------------------------------
# 8. Skill Requirements & Gap Analysis
# ---------------------------------------------------------------------------

class SkillRequirement(Base):
    __tablename__ = "skill_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id"), nullable=True, index=True)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=True, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False, index=True)
    required_level = Column(Integer, default=3, nullable=False)
    required_headcount = Column(Float, default=1.0, nullable=False)
    priority = Column(String(32), default="HIGH", nullable=False)
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SkillGapAnalysis(Base):
    __tablename__ = "skill_gap_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    requirement_id = Column(String(36), ForeignKey("skill_requirements.id"), nullable=False, index=True)
    available_headcount = Column(Float, default=0.0, nullable=False)
    required_headcount = Column(Float, default=0.0, nullable=False)
    gap_headcount = Column(Float, default=0.0, nullable=False)
    average_proficiency = Column(Float, default=0.0, nullable=False)
    gap_severity = Column(String(32), default=SkillGapSeverity.LOW.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 9. Critical Roles & Succession Planning
# ---------------------------------------------------------------------------

class CriticalRole(Base):
    __tablename__ = "critical_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id"), nullable=False, index=True)
    criticality = Column(String(32), default=RoleCriticality.HIGH.value, nullable=False)
    business_impact = Column(Text, nullable=True)
    replacement_difficulty = Column(String(32), default="HIGH", nullable=False)
    vacancy_risk = Column(String(32), default="MEDIUM", nullable=False)
    identified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    review_date = Column(Date, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    succession_plans = relationship("SuccessionPlan", back_populates="critical_role", cascade="all, delete-orphan")


class SuccessionPlan(Base):
    __tablename__ = "succession_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    critical_role_id = Column(String(36), ForeignKey("critical_roles.id"), nullable=False, index=True)
    status = Column(String(32), default=SuccessionStatus.ACTIVE.value, nullable=False)
    target_date = Column(Date, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    critical_role = relationship("CriticalRole", back_populates="succession_plans")
    candidates = relationship("SuccessionCandidate", back_populates="plan", cascade="all, delete-orphan")


class SuccessionCandidate(Base):
    __tablename__ = "succession_candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    succession_plan_id = Column(String(36), ForeignKey("succession_plans.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    readiness_level = Column(String(32), default=ReadinessLevel.READY_1_2_YEARS.value, nullable=False)
    development_actions = Column(Text, nullable=True)
    target_readiness_date = Column(Date, nullable=True)
    nomination_status = Column(String(32), default="NOMINATED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("SuccessionPlan", back_populates="candidates")


# ---------------------------------------------------------------------------
# 10. Talent Pools
# ---------------------------------------------------------------------------

class TalentPool(Base):
    __tablename__ = "talent_pools"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    purpose = Column(String(100), default="LEADERSHIP_PIPELINE", nullable=False)
    status = Column(String(32), default=TalentPoolStatus.ACTIVE.value, nullable=False)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    members = relationship("TalentPoolMember", back_populates="talent_pool", cascade="all, delete-orphan")


class TalentPoolMember(Base):
    __tablename__ = "talent_pool_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    talent_pool_id = Column(String(36), ForeignKey("talent_pools.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    source = Column(String(50), default="HR_NOMINATION", nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    removed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_pool_members_tenant_person", "tenant_id", "person_id"),
    )

    talent_pool = relationship("TalentPool", back_populates="members")


# ---------------------------------------------------------------------------
# 11. Workforce Scenarios
# ---------------------------------------------------------------------------

class WorkforceScenario(Base):
    __tablename__ = "workforce_scenarios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scenario_type = Column(String(32), default=WorkforceScenarioType.BASELINE.value, nullable=False)
    planning_horizon = Column(String(50), default="FY2026-27", nullable=False)
    status = Column(String(32), default="DRAFT", nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("WorkforceScenarioLine", back_populates="scenario", cascade="all, delete-orphan")


class WorkforceScenarioLine(Base):
    __tablename__ = "workforce_scenario_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    scenario_id = Column(String(36), ForeignKey("workforce_scenarios.id"), nullable=False, index=True)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=False)
    job_family = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    period = Column(String(32), nullable=False)
    headcount_delta = Column(Float, default=0.0, nullable=False)
    hiring_delta = Column(Float, default=0.0, nullable=False)
    exit_delta = Column(Float, default=0.0, nullable=False)
    cost_delta = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    scenario = relationship("WorkforceScenario", back_populates="lines")


# ---------------------------------------------------------------------------
# 12. Hiring Plan
# ---------------------------------------------------------------------------

class WorkforceHiringPlan(Base):
    __tablename__ = "workforce_hiring_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    fiscal_year = Column(String(32), nullable=False)
    status = Column(String(32), default=HiringPlanStatus.DRAFT.value, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("HiringPlanLine", back_populates="plan", cascade="all, delete-orphan")


class HiringPlanLine(Base):
    __tablename__ = "hiring_plan_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("workforce_hiring_plans.id"), nullable=False, index=True)
    organization_unit_id = Column(String(36), ForeignKey("organization_units.id"), nullable=False)
    position_id = Column(String(36), ForeignKey("positions.id"), nullable=True)
    job_family = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    planned_open_date = Column(Date, nullable=False)
    planned_join_date = Column(Date, nullable=False)
    planned_headcount = Column(Float, default=1.0, nullable=False)
    estimated_cost = Column(Float, default=0.0, nullable=False)
    recruitment_priority = Column(String(32), default="MEDIUM", nullable=False)
    source_requisition_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("WorkforceHiringPlan", back_populates="lines")


# ---------------------------------------------------------------------------
# 13. Internal Mobility Planning
# ---------------------------------------------------------------------------

class MobilityPlan(Base):
    __tablename__ = "mobility_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    current_position_id = Column(String(36), ForeignKey("positions.id"), nullable=True)
    target_position_id = Column(String(36), ForeignKey("positions.id"), nullable=True)
    mobility_type = Column(String(32), default=MobilityType.TRANSFER.value, nullable=False)
    target_date = Column(Date, nullable=False)
    status = Column(String(32), default=MobilityStatus.DRAFT.value, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_mobility_plans_tenant_person", "tenant_id", "person_id"),
        Index("ix_mobility_plans_tenant_status", "tenant_id", "status"),
    )
