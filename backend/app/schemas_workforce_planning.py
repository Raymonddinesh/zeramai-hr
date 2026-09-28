"""
schemas_workforce_planning.py - Pydantic Schemas for Module 17: Workforce Planning
Zeramai Enterprise HRMS
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Organization Units
# ---------------------------------------------------------------------------

class OrgUnitBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    unit_type: str = "DEPARTMENT"
    legal_entity_id: Optional[str] = None
    parent_id: Optional[str] = None
    department_id: Optional[str] = None
    leader_person_id: Optional[str] = None
    active: bool = True
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None


class OrgUnitCreate(OrgUnitBase):
    pass


class OrgUnitUpdate(BaseModel):
    name: Optional[str] = None
    unit_type: Optional[str] = None
    parent_id: Optional[str] = None
    department_id: Optional[str] = None
    leader_person_id: Optional[str] = None
    active: Optional[bool] = None
    effective_to: Optional[date] = None


class OrgUnitResponse(OrgUnitBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    leader_name: Optional[str] = None
    parent_name: Optional[str] = None
    positions_count: Optional[int] = 0

    class Config:
        from_attributes = True


class OrgUnitTreeResponse(OrgUnitResponse):
    children: List['OrgUnitTreeResponse'] = []


# ---------------------------------------------------------------------------
# 2. Position Management
# ---------------------------------------------------------------------------

class PositionBase(BaseModel):
    position_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    organization_unit_id: str
    legal_entity_id: Optional[str] = None
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    employment_type: Optional[str] = "FULL_TIME"
    location: Optional[str] = None
    status: str = "PLANNED"
    headcount_capacity: float = 1.0
    manager_position_id: Optional[str] = None
    cost_center_id: Optional[str] = None
    budgeted_cost: Optional[float] = None
    currency: str = "INR"
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    title: Optional[str] = None
    organization_unit_id: Optional[str] = None
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    headcount_capacity: Optional[float] = None
    manager_position_id: Optional[str] = None
    cost_center_id: Optional[str] = None
    budgeted_cost: Optional[float] = None
    effective_to: Optional[date] = None


class PositionResponse(PositionBase):
    id: str
    tenant_id: str
    filled_count: float
    created_at: datetime
    updated_at: datetime
    organization_unit_name: Optional[str] = None
    manager_position_title: Optional[str] = None
    active_assignees: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 3. Position Assignment
# ---------------------------------------------------------------------------

class PositionAssignmentBase(BaseModel):
    position_id: str
    person_id: str
    engagement_id: Optional[str] = None
    allocation_percentage: float = 100.0
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None
    assignment_type: str = "PRIMARY"


class PositionAssignmentCreate(PositionAssignmentBase):
    pass


class PositionAssignmentUpdate(BaseModel):
    allocation_percentage: Optional[float] = None
    effective_to: Optional[date] = None
    assignment_type: Optional[str] = None


class PositionAssignmentResponse(PositionAssignmentBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None
    position_title: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 4. Headcount Plan
# ---------------------------------------------------------------------------

class HeadcountPlanLineBase(BaseModel):
    organization_unit_id: str
    position_id: Optional[str] = None
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    month: str  # "2026-04"
    planned_headcount: float = 1.0
    planned_hires: float = 0.0
    planned_exits: float = 0.0
    planned_cost: float = 0.0
    currency: str = "INR"


class HeadcountPlanLineCreate(HeadcountPlanLineBase):
    pass


class HeadcountPlanLineResponse(HeadcountPlanLineBase):
    id: str
    tenant_id: str
    plan_id: str
    created_at: datetime
    updated_at: datetime
    organization_unit_name: Optional[str] = None

    class Config:
        from_attributes = True


class HeadcountPlanBase(BaseModel):
    name: str = Field(..., max_length=255)
    fiscal_year: str = Field(..., max_length=32)
    legal_entity_id: Optional[str] = None
    currency: str = "INR"


class HeadcountPlanCreate(HeadcountPlanBase):
    lines: List[HeadcountPlanLineCreate] = []


class HeadcountPlanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class HeadcountPlanResponse(HeadcountPlanBase):
    id: str
    tenant_id: str
    status: str
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    total_planned_headcount: Optional[float] = 0.0
    total_planned_cost: Optional[float] = 0.0
    lines: List[HeadcountPlanLineResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 5. Workforce Demand Planning
# ---------------------------------------------------------------------------

class WorkforceDemandLineBase(BaseModel):
    organization_unit_id: str
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    period: str  # "2026-Q1"
    required_headcount: float = 1.0
    required_skills: Optional[str] = None
    estimated_cost: float = 0.0
    currency: str = "INR"
    rationale: Optional[str] = None


class WorkforceDemandLineCreate(WorkforceDemandLineBase):
    pass


class WorkforceDemandLineResponse(WorkforceDemandLineBase):
    id: str
    tenant_id: str
    plan_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkforceDemandPlanBase(BaseModel):
    name: str = Field(..., max_length=255)
    planning_horizon: str = "1_YEAR"
    methodology: str = "BOTTOM_UP"


class WorkforceDemandPlanCreate(WorkforceDemandPlanBase):
    lines: List[WorkforceDemandLineCreate] = []


class WorkforceDemandPlanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class WorkforceDemandPlanResponse(WorkforceDemandPlanBase):
    id: str
    tenant_id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    total_required_headcount: Optional[float] = 0.0
    total_estimated_cost: Optional[float] = 0.0
    lines: List[WorkforceDemandLineResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 6. Workforce Supply & Gap Analysis
# ---------------------------------------------------------------------------

class WorkforceSupplySummary(BaseModel):
    period: str
    total_supply_headcount: float
    headcount_by_org_unit: Dict[str, float] = {}
    headcount_by_job_family: Dict[str, float] = {}
    headcount_by_job_level: Dict[str, float] = {}
    headcount_by_location: Dict[str, float] = {}
    known_future_hires: float = 0.0
    known_future_exits: float = 0.0


class WorkforceGapResponse(BaseModel):
    id: str
    tenant_id: str
    plan_reference: str
    organization_unit_id: Optional[str] = None
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    period: str
    demand_headcount: float
    supply_headcount: float
    gap_headcount: float
    estimated_cost_gap: float
    gap_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 7. Skills Inventory
# ---------------------------------------------------------------------------

class SkillLevelBase(BaseModel):
    code: str
    name: str
    rank: int = 1
    description: Optional[str] = None


class SkillLevelCreate(SkillLevelBase):
    pass


class SkillLevelResponse(SkillLevelBase):
    id: str
    skill_id: str

    class Config:
        from_attributes = True


class SkillBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    category: str = "TECHNICAL"
    description: Optional[str] = None
    active: bool = True


class SkillCreate(SkillBase):
    levels: List[SkillLevelCreate] = []


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class SkillResponse(SkillBase):
    id: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    levels: List[SkillLevelResponse] = []

    class Config:
        from_attributes = True


class EmployeeSkillBase(BaseModel):
    person_id: str
    skill_id: str
    skill_level_id: Optional[str] = None
    proficiency: float = Field(default=1.0, ge=1.0, le=5.0)
    source: str = "SELF_REPORTED"
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None


class EmployeeSkillCreate(EmployeeSkillBase):
    pass


class EmployeeSkillUpdate(BaseModel):
    proficiency: Optional[float] = None
    skill_level_id: Optional[str] = None
    verified: Optional[bool] = None
    effective_to: Optional[date] = None


class EmployeeSkillResponse(EmployeeSkillBase):
    id: str
    tenant_id: str
    verified: bool
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    skill_name: Optional[str] = None
    skill_code: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 8. Skill Requirements & Gap Analysis
# ---------------------------------------------------------------------------

class SkillRequirementBase(BaseModel):
    skill_id: str
    position_id: Optional[str] = None
    organization_unit_id: Optional[str] = None
    required_level: int = 3
    required_headcount: float = 1.0
    priority: str = "HIGH"
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None


class SkillRequirementCreate(SkillRequirementBase):
    pass


class SkillRequirementResponse(SkillRequirementBase):
    id: str
    tenant_id: str
    created_at: datetime
    skill_name: Optional[str] = None

    class Config:
        from_attributes = True


class SkillGapAnalysisResponse(BaseModel):
    id: str
    tenant_id: str
    requirement_id: str
    available_headcount: float
    required_headcount: float
    gap_headcount: float
    average_proficiency: float
    gap_severity: str
    created_at: datetime
    skill_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 9. Critical Roles & Succession Planning
# ---------------------------------------------------------------------------

class CriticalRoleBase(BaseModel):
    position_id: str
    criticality: str = "HIGH"
    business_impact: Optional[str] = None
    replacement_difficulty: str = "HIGH"
    vacancy_risk: str = "MEDIUM"
    review_date: Optional[date] = None
    status: str = "ACTIVE"


class CriticalRoleCreate(CriticalRoleBase):
    pass


class CriticalRoleUpdate(BaseModel):
    criticality: Optional[str] = None
    business_impact: Optional[str] = None
    replacement_difficulty: Optional[str] = None
    vacancy_risk: Optional[str] = None
    status: Optional[str] = None


class CriticalRoleResponse(CriticalRoleBase):
    id: str
    tenant_id: str
    identified_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    position_title: Optional[str] = None
    position_code: Optional[str] = None
    current_incumbent: Optional[str] = None
    succession_coverage_count: Optional[int] = 0

    class Config:
        from_attributes = True


class SuccessionCandidateBase(BaseModel):
    person_id: str
    readiness_level: str = "READY_1_2_YEARS"
    development_actions: Optional[str] = None
    target_readiness_date: Optional[date] = None
    nomination_status: str = "NOMINATED"


class SuccessionCandidateCreate(SuccessionCandidateBase):
    pass


class SuccessionCandidateUpdate(BaseModel):
    readiness_level: Optional[str] = None
    development_actions: Optional[str] = None
    target_readiness_date: Optional[date] = None
    nomination_status: Optional[str] = None


class SuccessionCandidateResponse(SuccessionCandidateBase):
    id: str
    tenant_id: str
    succession_plan_id: str
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


class SuccessionPlanBase(BaseModel):
    critical_role_id: str
    target_date: Optional[date] = None


class SuccessionPlanCreate(SuccessionPlanBase):
    candidates: List[SuccessionCandidateCreate] = []


class SuccessionPlanUpdate(BaseModel):
    status: Optional[str] = None
    target_date: Optional[date] = None


class SuccessionPlanResponse(SuccessionPlanBase):
    id: str
    tenant_id: str
    status: str
    created_by: str
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    critical_role_title: Optional[str] = None
    candidates: List[SuccessionCandidateResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 10. Talent Pools
# ---------------------------------------------------------------------------

class TalentPoolMemberCreate(BaseModel):
    person_id: str
    source: str = "HR_NOMINATION"


class TalentPoolMemberResponse(BaseModel):
    id: str
    tenant_id: str
    talent_pool_id: str
    person_id: str
    source: str
    added_at: datetime
    removed_at: Optional[datetime] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


class TalentPoolBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    purpose: str = "LEADERSHIP_PIPELINE"


class TalentPoolCreate(TalentPoolBase):
    member_person_ids: List[str] = []


class TalentPoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    status: Optional[str] = None


class TalentPoolResponse(TalentPoolBase):
    id: str
    tenant_id: str
    status: str
    owner_user_id: str
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = 0
    members: List[TalentPoolMemberResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 11. Workforce Scenarios
# ---------------------------------------------------------------------------

class WorkforceScenarioLineBase(BaseModel):
    organization_unit_id: str
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    period: str
    headcount_delta: float = 0.0
    hiring_delta: float = 0.0
    exit_delta: float = 0.0
    cost_delta: float = 0.0
    notes: Optional[str] = None


class WorkforceScenarioLineCreate(WorkforceScenarioLineBase):
    pass


class WorkforceScenarioLineResponse(WorkforceScenarioLineBase):
    id: str
    tenant_id: str
    scenario_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkforceScenarioBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    scenario_type: str = "BASELINE"
    planning_horizon: str = "FY2026-27"


class WorkforceScenarioCreate(WorkforceScenarioBase):
    lines: List[WorkforceScenarioLineCreate] = []


class WorkforceScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class WorkforceScenarioResponse(WorkforceScenarioBase):
    id: str
    tenant_id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    total_headcount_delta: Optional[float] = 0.0
    total_cost_delta: Optional[float] = 0.0
    lines: List[WorkforceScenarioLineResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 12. Hiring Plan
# ---------------------------------------------------------------------------

class HiringPlanLineBase(BaseModel):
    organization_unit_id: str
    position_id: Optional[str] = None
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    planned_open_date: date
    planned_join_date: date
    planned_headcount: float = 1.0
    estimated_cost: float = 0.0
    recruitment_priority: str = "MEDIUM"
    source_requisition_id: Optional[str] = None


class HiringPlanLineCreate(HiringPlanLineBase):
    pass


class HiringPlanLineResponse(HiringPlanLineBase):
    id: str
    tenant_id: str
    plan_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkforceHiringPlanBase(BaseModel):
    name: str = Field(..., max_length=255)
    fiscal_year: str = Field(..., max_length=32)


class WorkforceHiringPlanCreate(WorkforceHiringPlanBase):
    lines: List[HiringPlanLineCreate] = []


class WorkforceHiringPlanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class WorkforceHiringPlanResponse(WorkforceHiringPlanBase):
    id: str
    tenant_id: str
    status: str
    created_by: str
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_planned_hires: Optional[float] = 0.0
    total_estimated_hiring_cost: Optional[float] = 0.0
    lines: List[HiringPlanLineResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 13. Internal Mobility Planning
# ---------------------------------------------------------------------------

class MobilityPlanBase(BaseModel):
    person_id: str
    current_position_id: Optional[str] = None
    target_position_id: Optional[str] = None
    mobility_type: str = "TRANSFER"
    target_date: date


class MobilityPlanCreate(MobilityPlanBase):
    pass


class MobilityPlanUpdate(BaseModel):
    mobility_type: Optional[str] = None
    target_position_id: Optional[str] = None
    target_date: Optional[date] = None
    status: Optional[str] = None


class MobilityPlanResponse(MobilityPlanBase):
    id: str
    tenant_id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    person_name: Optional[str] = None
    current_position_title: Optional[str] = None
    target_position_title: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 14. Plan vs. Actual & Attrition Analysis
# ---------------------------------------------------------------------------

class PlanVsActualComparison(BaseModel):
    fiscal_year: str
    month: Optional[str] = None
    planned_headcount: float
    actual_headcount: float
    headcount_variance: float
    planned_hires: float
    actual_hires: float
    hiring_variance: float
    planned_exits: float
    actual_exits: float
    exit_variance: float
    planned_workforce_cost: float
    actual_workforce_cost: float
    cost_variance: float
    currency: str = "INR"


class AttritionScenarioImpact(BaseModel):
    scenario_name: str
    assumed_attrition_rate_pct: float
    projected_exits_count: float
    affected_positions: List[Dict[str, Any]] = []
    affected_critical_roles_count: int = 0
    estimated_replacement_cost: float = 0.0
    currency: str = "INR"
    notes: str = "SCENARIO ASSUMPTION BASED ON HISTORICAL TURNOVER"


# ---------------------------------------------------------------------------
# 15. Strategic Workforce Dashboard
# ---------------------------------------------------------------------------

class StrategicWorkforceDashboard(BaseModel):
    current_headcount: float
    planned_headcount: float
    headcount_gap: float
    open_positions_count: int
    critical_roles_count: int
    succession_coverage_pct: float
    skill_gaps_count: int
    planned_hires_ytd: float
    planned_exits_ytd: float
    total_workforce_cost: float
    workforce_cost_variance: float
    active_scenarios_count: int
    pending_mobility_plans_count: int
    talent_pools_count: int
