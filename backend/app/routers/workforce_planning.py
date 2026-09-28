"""
workforce_planning.py - Module 17 API Router: Strategic Workforce Planning & Org Design
Zeramai Enterprise HRMS
"""
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import User, UserRole, Person, Tenant
from app.models_workforce_planning import (
    OrganizationUnit,
    Position,
    PositionAssignment,
    HeadcountPlan,
    HeadcountPlanLine,
    WorkforceDemandPlan,
    WorkforceDemandLine,
    WorkforceGap,
    Skill,
    SkillLevel,
    EmployeeSkill,
    SkillRequirement,
    SkillGapAnalysis,
    CriticalRole,
    SuccessionPlan,
    SuccessionCandidate,
    TalentPool,
    TalentPoolMember,
    WorkforceScenario,
    WorkforceScenarioLine,
    WorkforceHiringPlan,
    HiringPlanLine,
    MobilityPlan,
    OrgUnitType,
    PositionStatus,
    PositionAssignmentType,
    HeadcountPlanStatus,
    WorkforceGapType,
    SkillGapSeverity,
    RoleCriticality,
    SuccessionStatus,
    ReadinessLevel,
    TalentPoolStatus,
    WorkforceScenarioType,
    HiringPlanStatus,
    MobilityType,
    MobilityStatus,
)
from app.schemas_workforce_planning import (
    OrgUnitCreate,
    OrgUnitUpdate,
    OrgUnitResponse,
    OrgUnitTreeResponse,
    PositionCreate,
    PositionUpdate,
    PositionResponse,
    PositionAssignmentCreate,
    PositionAssignmentUpdate,
    PositionAssignmentResponse,
    HeadcountPlanCreate,
    HeadcountPlanUpdate,
    HeadcountPlanResponse,
    WorkforceDemandPlanCreate,
    WorkforceDemandPlanUpdate,
    WorkforceDemandPlanResponse,
    WorkforceSupplySummary,
    WorkforceGapResponse,
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    EmployeeSkillCreate,
    EmployeeSkillUpdate,
    EmployeeSkillResponse,
    SkillRequirementCreate,
    SkillRequirementResponse,
    SkillGapAnalysisResponse,
    CriticalRoleCreate,
    CriticalRoleUpdate,
    CriticalRoleResponse,
    SuccessionPlanCreate,
    SuccessionPlanUpdate,
    SuccessionPlanResponse,
    SuccessionCandidateCreate,
    SuccessionCandidateResponse,
    TalentPoolCreate,
    TalentPoolUpdate,
    TalentPoolResponse,
    TalentPoolMemberCreate,
    TalentPoolMemberResponse,
    WorkforceScenarioCreate,
    WorkforceScenarioUpdate,
    WorkforceScenarioResponse,
    WorkforceHiringPlanCreate,
    WorkforceHiringPlanUpdate,
    WorkforceHiringPlanResponse,
    MobilityPlanCreate,
    MobilityPlanUpdate,
    MobilityPlanResponse,
    PlanVsActualComparison,
    AttritionScenarioImpact,
    StrategicWorkforceDashboard,
)
from app.services.workforce_planning_service import (
    validate_no_org_unit_cycles,
    build_org_unit_tree,
    recalculate_position_fill_count,
    validate_position_assignment,
    calculate_workforce_supply,
    generate_workforce_gap_analysis,
    evaluate_skill_gap_analysis,
    calculate_plan_vs_actual,
    analyze_attrition_scenario_impact,
    get_strategic_workforce_dashboard,
)

router = APIRouter(prefix="/api/v3/workforce-planning", tags=["Module 17 - Strategic Workforce Planning"])


# ---------------------------------------------------------------------------
# Helper Security & Tenant Isolation Functions
# ---------------------------------------------------------------------------

def _resolve_tenant_id(request: Request, db: Session, current_user: Optional[User] = None) -> str:
    """
    Enforces tenant isolation using headers, user profile, or default fallback.
    """
    header_tenant = request.headers.get("X-Tenant-ID")
    if header_tenant:
        return header_tenant

    if current_user and getattr(current_user, "person", None) and getattr(current_user.person, "tenant_id", None):
        return current_user.person.tenant_id

    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def _can_read_wf(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.FINANCE)
        or has_permission(user, "workforce_planning:read", db)
        or has_permission(user, "workforce_planning.read", db)
    )


def _can_manage_wf(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "workforce_planning:manage", db)
        or has_permission(user, "workforce_planning.manage", db)
    )


def _can_view_salary(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.FINANCE, UserRole.HR_ADMIN)
        or has_permission(user, "finance:read", db)
        or has_permission(user, "compensation:read", db)
        or has_permission(user, "workforce_planning:manage", db)
    )


# ---------------------------------------------------------------------------
# 1. Strategic Workforce Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=StrategicWorkforceDashboard)
def get_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return get_strategic_workforce_dashboard(db, tenant_id)


# ---------------------------------------------------------------------------
# 2. Organization Units (Org Design)
# ---------------------------------------------------------------------------

@router.get("/organization-units")
def list_org_units(
    request: Request,
    tree: bool = Query(False),
    unit_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if tree:
        return build_org_unit_tree(db, tenant_id)

    query = db.query(OrganizationUnit).filter(OrganizationUnit.tenant_id == tenant_id)
    if unit_type:
        query = query.filter(OrganizationUnit.unit_type == unit_type)

    units = query.all()
    resp = []
    for u in units:
        r = OrgUnitResponse.from_orm(u)
        r.positions_count = len(u.positions)
        if u.parent:
            r.parent_name = u.parent.name
        resp.append(r)
    return resp


@router.post("/organization-units", response_model=OrgUnitResponse, status_code=status.HTTP_201_CREATED)
def create_org_unit(
    payload: OrgUnitCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Check unique code
    existing = db.query(OrganizationUnit).filter(
        OrganizationUnit.tenant_id == tenant_id,
        OrganizationUnit.code == payload.code,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Organization unit code {payload.code} already exists")

    # Validate parent if specified
    if payload.parent_id:
        parent = db.query(OrganizationUnit).filter(
            OrganizationUnit.id == payload.parent_id,
            OrganizationUnit.tenant_id == tenant_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent organization unit not found")

    unit = OrganizationUnit(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        unit_type=payload.unit_type,
        legal_entity_id=payload.legal_entity_id,
        parent_id=payload.parent_id,
        department_id=payload.department_id,
        leader_person_id=payload.leader_person_id,
        active=payload.active,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    r = OrgUnitResponse.from_orm(unit)
    r.positions_count = 0
    return r


@router.get("/organization-units/{unit_id}", response_model=OrgUnitResponse)
def get_org_unit(
    unit_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    u = db.query(OrganizationUnit).filter(OrganizationUnit.id == unit_id, OrganizationUnit.tenant_id == tenant_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization unit not found")

    r = OrgUnitResponse.from_orm(u)
    r.positions_count = len(u.positions)
    if u.parent:
        r.parent_name = u.parent.name
    return r


@router.put("/organization-units/{unit_id}", response_model=OrgUnitResponse)
def update_org_unit(
    unit_id: str,
    payload: OrgUnitUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    u = db.query(OrganizationUnit).filter(OrganizationUnit.id == unit_id, OrganizationUnit.tenant_id == tenant_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization unit not found")

    if payload.parent_id is not None:
        try:
            validate_no_org_unit_cycles(db, unit_id, payload.parent_id)
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        u.parent_id = payload.parent_id

    for k, v in payload.dict(exclude_unset=True).items():
        if k != "parent_id":
            setattr(u, k, v)

    db.commit()
    db.refresh(u)
    r = OrgUnitResponse.from_orm(u)
    r.positions_count = len(u.positions)
    return r


# ---------------------------------------------------------------------------
# 3. Position Management
# ---------------------------------------------------------------------------

@router.get("/positions", response_model=List[PositionResponse])
def list_positions(
    request: Request,
    org_unit_id: Optional[str] = Query(None),
    pos_status: Optional[str] = Query(None, alias="status"),
    job_family: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(Position).filter(Position.tenant_id == tenant_id)
    if org_unit_id:
        query = query.filter(Position.organization_unit_id == org_unit_id)
    if pos_status:
        query = query.filter(Position.status == pos_status)
    if job_family:
        query = query.filter(Position.job_family == job_family)

    positions = query.all()
    can_salary = _can_view_salary(current_user, db)

    resp = []
    for p in positions:
        r = PositionResponse.from_orm(p)
        if not can_salary:
            r.budgeted_cost = None
        if p.organization_unit:
            r.organization_unit_name = p.organization_unit.name
        if p.manager_position:
            r.manager_position_title = p.manager_position.title
        resp.append(r)
    return resp


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: PositionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:positions:manage", db)
        or has_permission(current_user, "workforce_planning.positions.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Position manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Check unique position code
    existing = db.query(Position).filter(
        Position.tenant_id == tenant_id,
        Position.position_code == payload.position_code,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Position code {payload.position_code} already exists")

    # Validate org unit exists
    ou = db.query(OrganizationUnit).filter(
        OrganizationUnit.id == payload.organization_unit_id,
        OrganizationUnit.tenant_id == tenant_id,
    ).first()
    if not ou:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization unit not found")

    pos = Position(
        tenant_id=tenant_id,
        position_code=payload.position_code,
        title=payload.title,
        organization_unit_id=payload.organization_unit_id,
        legal_entity_id=payload.legal_entity_id,
        job_family=payload.job_family,
        job_level=payload.job_level,
        employment_type=payload.employment_type,
        location=payload.location,
        status=payload.status,
        headcount_capacity=payload.headcount_capacity,
        filled_count=0.0,
        manager_position_id=payload.manager_position_id,
        cost_center_id=payload.cost_center_id,
        budgeted_cost=payload.budgeted_cost,
        currency=payload.currency,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)

    r = PositionResponse.from_orm(pos)
    r.organization_unit_name = ou.name
    return r


@router.get("/positions/{position_id}", response_model=PositionResponse)
def get_position(
    position_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    p = db.query(Position).filter(Position.id == position_id, Position.tenant_id == tenant_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    r = PositionResponse.from_orm(p)
    if not _can_view_salary(current_user, db):
        r.budgeted_cost = None
    if p.organization_unit:
        r.organization_unit_name = p.organization_unit.name
    if p.manager_position:
        r.manager_position_title = p.manager_position.title

    r.active_assignees = [
        {
            "id": a.id,
            "person_id": a.person_id,
            "allocation_percentage": a.allocation_percentage,
            "assignment_type": a.assignment_type,
            "effective_from": a.effective_from.isoformat(),
        }
        for a in p.assignments
        if not a.effective_to or a.effective_to >= date.today()
    ]
    return r


@router.put("/positions/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: str,
    payload: PositionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:positions:manage", db)
        or has_permission(current_user, "workforce_planning.positions.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Position manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    p = db.query(Position).filter(Position.id == position_id, Position.tenant_id == tenant_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(p, k, v)

    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# 4. Position Assignment & Capacity Validation
# ---------------------------------------------------------------------------

@router.post("/positions/{position_id}/assign", response_model=PositionAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_person_to_position(
    position_id: str,
    payload: PositionAssignmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:positions:manage", db)
        or has_permission(current_user, "workforce_planning.positions.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Position manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Validate person
    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    try:
        validate_position_assignment(
            db=db,
            tenant_id=tenant_id,
            position_id=position_id,
            person_id=payload.person_id,
            allocation_percentage=payload.allocation_percentage,
            assignment_type=payload.assignment_type,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    assign = PositionAssignment(
        tenant_id=tenant_id,
        position_id=position_id,
        person_id=payload.person_id,
        engagement_id=payload.engagement_id,
        allocation_percentage=payload.allocation_percentage,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        assignment_type=payload.assignment_type,
    )
    db.add(assign)
    db.flush()

    recalculate_position_fill_count(db, position_id)
    db.commit()
    db.refresh(assign)

    r = PositionAssignmentResponse.from_orm(assign)
    r.person_name = getattr(person, "full_name", None) or "Employee"
    return r


@router.get("/position-assignments", response_model=List[PositionAssignmentResponse])
def list_position_assignments(
    request: Request,
    position_id: Optional[str] = Query(None),
    person_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(PositionAssignment).filter(PositionAssignment.tenant_id == tenant_id)
    if position_id:
        query = query.filter(PositionAssignment.position_id == position_id)
    if person_id:
        query = query.filter(PositionAssignment.person_id == person_id)

    assignments = query.all()
    resp = []
    for a in assignments:
        r = PositionAssignmentResponse.from_orm(a)
        p = db.query(Person).filter(Person.id == a.person_id).first()
        if p:
            r.person_name = getattr(p, "full_name", None) or "Employee"
        resp.append(r)
    return resp


@router.delete("/position-assignments/{assignment_id}")
def delete_position_assignment(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    a = db.query(PositionAssignment).filter(PositionAssignment.id == assignment_id, PositionAssignment.tenant_id == tenant_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position assignment not found")

    pos_id = a.position_id
    db.delete(a)
    db.flush()
    recalculate_position_fill_count(db, pos_id)
    db.commit()
    return {"status": "success", "message": "Assignment deleted"}


# ---------------------------------------------------------------------------
# 5. Headcount Plan & Lines
# ---------------------------------------------------------------------------

@router.get("/headcount-plans", response_model=List[HeadcountPlanResponse])
def list_headcount_plans(
    request: Request,
    fiscal_year: Optional[str] = Query(None),
    plan_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(HeadcountPlan).filter(HeadcountPlan.tenant_id == tenant_id)
    if fiscal_year:
        query = query.filter(HeadcountPlan.fiscal_year == fiscal_year)
    if plan_status:
        query = query.filter(HeadcountPlan.status == plan_status)

    plans = query.all()
    can_salary = _can_view_salary(current_user, db)

    resp = []
    for pl in plans:
        r = HeadcountPlanResponse.from_orm(pl)
        r.total_planned_headcount = sum(float(l.planned_headcount) for l in pl.lines)
        r.total_planned_cost = sum(float(l.planned_cost) for l in pl.lines) if can_salary else None
        resp.append(r)
    return resp


@router.post("/headcount-plans", response_model=HeadcountPlanResponse, status_code=status.HTTP_201_CREATED)
def create_headcount_plan(
    payload: HeadcountPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:headcount:manage", db)
        or has_permission(current_user, "workforce_planning.headcount.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Headcount manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = HeadcountPlan(
        tenant_id=tenant_id,
        name=payload.name,
        fiscal_year=payload.fiscal_year,
        legal_entity_id=payload.legal_entity_id,
        currency=payload.currency,
        status=HeadcountPlanStatus.DRAFT.value,
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()

    for l in payload.lines:
        line = HeadcountPlanLine(
            tenant_id=tenant_id,
            plan_id=plan.id,
            organization_unit_id=l.organization_unit_id,
            position_id=l.position_id,
            job_family=l.job_family,
            job_level=l.job_level,
            month=l.month,
            planned_headcount=l.planned_headcount,
            planned_hires=l.planned_hires,
            planned_exits=l.planned_exits,
            planned_cost=l.planned_cost,
            currency=l.currency,
        )
        db.add(line)

    db.commit()
    db.refresh(plan)

    r = HeadcountPlanResponse.from_orm(plan)
    r.total_planned_headcount = sum(float(l.planned_headcount) for l in plan.lines)
    r.total_planned_cost = sum(float(l.planned_cost) for l in plan.lines)
    return r


@router.get("/headcount-plans/{plan_id}", response_model=HeadcountPlanResponse)
def get_headcount_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    pl = db.query(HeadcountPlan).filter(HeadcountPlan.id == plan_id, HeadcountPlan.tenant_id == tenant_id).first()
    if not pl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Headcount plan not found")

    can_salary = _can_view_salary(current_user, db)
    r = HeadcountPlanResponse.from_orm(pl)
    r.total_planned_headcount = sum(float(l.planned_headcount) for l in pl.lines)
    r.total_planned_cost = sum(float(l.planned_cost) for l in pl.lines) if can_salary else None
    return r


@router.post("/headcount-plans/{plan_id}/approve", response_model=HeadcountPlanResponse)
def approve_headcount_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    pl = db.query(HeadcountPlan).filter(HeadcountPlan.id == plan_id, HeadcountPlan.tenant_id == tenant_id).first()
    if not pl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Headcount plan not found")

    pl.status = HeadcountPlanStatus.APPROVED.value
    pl.approved_by = current_user.id
    pl.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(pl)

    r = HeadcountPlanResponse.from_orm(pl)
    r.total_planned_headcount = sum(float(l.planned_headcount) for l in pl.lines)
    return r


# ---------------------------------------------------------------------------
# 6. Demand Planning & Supply Analysis
# ---------------------------------------------------------------------------

@router.get("/demand-plans", response_model=List[WorkforceDemandPlanResponse])
def list_demand_plans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plans = db.query(WorkforceDemandPlan).filter(WorkforceDemandPlan.tenant_id == tenant_id).all()
    resp = []
    for p in plans:
        r = WorkforceDemandPlanResponse.from_orm(p)
        r.total_required_headcount = sum(float(l.required_headcount) for l in p.lines)
        r.total_estimated_cost = sum(float(l.estimated_cost) for l in p.lines)
        resp.append(r)
    return resp


@router.post("/demand-plans", response_model=WorkforceDemandPlanResponse, status_code=status.HTTP_201_CREATED)
def create_demand_plan(
    payload: WorkforceDemandPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = WorkforceDemandPlan(
        tenant_id=tenant_id,
        name=payload.name,
        planning_horizon=payload.planning_horizon,
        methodology=payload.methodology,
        status="APPROVED",
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()

    for l in payload.lines:
        line = WorkforceDemandLine(
            tenant_id=tenant_id,
            plan_id=plan.id,
            organization_unit_id=l.organization_unit_id,
            job_family=l.job_family,
            job_level=l.job_level,
            period=l.period,
            required_headcount=l.required_headcount,
            required_skills=l.required_skills,
            estimated_cost=l.estimated_cost,
            currency=l.currency,
            rationale=l.rationale,
        )
        db.add(line)

    db.commit()
    db.refresh(plan)

    r = WorkforceDemandPlanResponse.from_orm(plan)
    r.total_required_headcount = sum(float(l.required_headcount) for l in plan.lines)
    return r


@router.get("/demand-plans/{plan_id}", response_model=WorkforceDemandPlanResponse)
def get_demand_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = db.query(WorkforceDemandPlan).filter(WorkforceDemandPlan.id == plan_id, WorkforceDemandPlan.tenant_id == tenant_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demand plan not found")

    r = WorkforceDemandPlanResponse.from_orm(plan)
    r.total_required_headcount = sum(float(l.required_headcount) for l in plan.lines)
    return r


@router.get("/supply", response_model=WorkforceSupplySummary)
def get_workforce_supply(
    request: Request,
    period: str = Query("CURRENT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return calculate_workforce_supply(db, tenant_id, period)


# ---------------------------------------------------------------------------
# 7. Workforce Gap Analysis
# ---------------------------------------------------------------------------

@router.get("/gaps", response_model=List[WorkforceGapResponse])
def list_workforce_gaps(
    request: Request,
    plan_reference: Optional[str] = Query(None),
    gap_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(WorkforceGap).filter(WorkforceGap.tenant_id == tenant_id)
    if plan_reference:
        query = query.filter(WorkforceGap.plan_reference == plan_reference)
    if gap_type:
        query = query.filter(WorkforceGap.gap_type == gap_type)

    return query.all()


@router.post("/gaps/calculate", response_model=List[WorkforceGapResponse])
def calculate_workforce_gaps(
    demand_plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    try:
        gaps = generate_workforce_gap_analysis(db, tenant_id, demand_plan_id)
        return gaps
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


# ---------------------------------------------------------------------------
# 8. Skills Inventory & Employee Skills
# ---------------------------------------------------------------------------

@router.get("/skills", response_model=List[SkillResponse])
def list_skills(
    request: Request,
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(Skill).filter(or_(Skill.tenant_id == tenant_id, Skill.tenant_id.is_(None)))
    if category:
        query = query.filter(Skill.category == category)

    return query.all()


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:skills:manage", db)
        or has_permission(current_user, "workforce_planning.skills.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Skills manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    skill = Skill(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        active=payload.active,
    )
    db.add(skill)
    db.flush()

    # Add levels or default levels (L1-L5)
    levels_to_add = payload.levels
    if not levels_to_add:
        levels_to_add = [
            {"code": "L1", "name": "Novice", "rank": 1},
            {"code": "L2", "name": "Intermediate", "rank": 2},
            {"code": "L3", "name": "Advanced", "rank": 3},
            {"code": "L4", "name": "Expert", "rank": 4},
        ]
        for l in levels_to_add:
            sl = SkillLevel(
                skill_id=skill.id,
                code=l["code"],
                name=l["name"],
                rank=l["rank"],
            )
            db.add(sl)
    else:
        for l in levels_to_add:
            sl = SkillLevel(
                skill_id=skill.id,
                code=l.code,
                name=l.name,
                rank=l.rank,
                description=l.description,
            )
            db.add(sl)

    db.commit()
    db.refresh(skill)
    return skill


@router.get("/skills/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    s = db.query(Skill).filter(Skill.id == skill_id, or_(Skill.tenant_id == tenant_id, Skill.tenant_id.is_(None))).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return s


@router.get("/employee-skills", response_model=List[EmployeeSkillResponse])
def list_employee_skills(
    request: Request,
    person_id: Optional[str] = Query(None),
    skill_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(EmployeeSkill).filter(EmployeeSkill.tenant_id == tenant_id)
    if person_id:
        query = query.filter(EmployeeSkill.person_id == person_id)
    if skill_id:
        query = query.filter(EmployeeSkill.skill_id == skill_id)

    emp_skills = query.all()
    resp = []
    for es in emp_skills:
        r = EmployeeSkillResponse.from_orm(es)
        sk = db.query(Skill).filter(Skill.id == es.skill_id).first()
        if sk:
            r.skill_name = sk.name
            r.skill_code = sk.code
        p = db.query(Person).filter(Person.id == es.person_id).first()
        if p:
            r.person_name = getattr(p, "full_name", None) or "Employee"
        resp.append(r)
    return resp


@router.post("/employee-skills", response_model=EmployeeSkillResponse, status_code=status.HTTP_201_CREATED)
def record_employee_skill(
    payload: EmployeeSkillCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Permission check: employee can record self skill, manager/admin can record for any
    if not _can_manage_wf(current_user, db):
        if current_user.person_id != payload.person_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot record skills for other employees")

    es = EmployeeSkill(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        skill_id=payload.skill_id,
        skill_level_id=payload.skill_level_id,
        proficiency=payload.proficiency,
        source=payload.source,
        verified=False,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(es)
    db.commit()
    db.refresh(es)
    return es


@router.post("/employee-skills/{emp_skill_id}/verify", response_model=EmployeeSkillResponse)
def verify_employee_skill(
    emp_skill_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required to verify skills")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    es = db.query(EmployeeSkill).filter(EmployeeSkill.id == emp_skill_id, EmployeeSkill.tenant_id == tenant_id).first()
    if not es:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee skill record not found")

    es.verified = True
    es.verified_by = current_user.id
    es.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(es)
    return es


# ---------------------------------------------------------------------------
# 9. Skill Requirements & Gap Analysis
# ---------------------------------------------------------------------------

@router.get("/skill-requirements", response_model=List[SkillRequirementResponse])
def list_skill_requirements(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    reqs = db.query(SkillRequirement).filter(SkillRequirement.tenant_id == tenant_id).all()
    resp = []
    for r in reqs:
        resp_obj = SkillRequirementResponse.from_orm(r)
        sk = db.query(Skill).filter(Skill.id == r.skill_id).first()
        if sk:
            resp_obj.skill_name = sk.name
        resp.append(resp_obj)
    return resp


@router.post("/skill-requirements", response_model=SkillRequirementResponse, status_code=status.HTTP_201_CREATED)
def create_skill_requirement(
    payload: SkillRequirementCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    req = SkillRequirement(
        tenant_id=tenant_id,
        skill_id=payload.skill_id,
        position_id=payload.position_id,
        organization_unit_id=payload.organization_unit_id,
        required_level=payload.required_level,
        required_headcount=payload.required_headcount,
        priority=payload.priority,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/skill-gaps", response_model=List[SkillGapAnalysisResponse])
def get_skill_gaps(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    analyses = evaluate_skill_gap_analysis(db, tenant_id)
    resp = []
    for a in analyses:
        r = SkillGapAnalysisResponse.from_orm(a)
        req = db.query(SkillRequirement).filter(SkillRequirement.id == a.requirement_id).first()
        if req:
            sk = db.query(Skill).filter(Skill.id == req.skill_id).first()
            if sk:
                r.skill_name = sk.name
        resp.append(r)
    return resp


# ---------------------------------------------------------------------------
# 10. Critical Roles & Succession Planning
# ---------------------------------------------------------------------------

@router.get("/critical-roles", response_model=List[CriticalRoleResponse])
def list_critical_roles(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    roles = db.query(CriticalRole).filter(CriticalRole.tenant_id == tenant_id).all()
    resp = []
    for cr in roles:
        r = CriticalRoleResponse.from_orm(cr)
        pos = db.query(Position).filter(Position.id == cr.position_id).first()
        if pos:
            r.position_title = pos.title
            r.position_code = pos.position_code
            if pos.assignments:
                primary = [a for a in pos.assignments if a.assignment_type == PositionAssignmentType.PRIMARY.value]
                if primary:
                    person = db.query(Person).filter(Person.id == primary[0].person_id).first()
                    if person:
                        r.current_incumbent = getattr(person, "full_name", None) or "Employee"

        coverage = sum(len(sp.candidates) for sp in cr.succession_plans)
        r.succession_coverage_count = coverage
        resp.append(r)
    return resp


@router.post("/critical-roles", response_model=CriticalRoleResponse, status_code=status.HTTP_201_CREATED)
def create_critical_role(
    payload: CriticalRoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:succession:manage", db)
        or has_permission(current_user, "workforce_planning.succession.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Succession manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Check position exists in tenant
    pos = db.query(Position).filter(Position.id == payload.position_id, Position.tenant_id == tenant_id).first()
    if not pos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    cr = CriticalRole(
        tenant_id=tenant_id,
        position_id=payload.position_id,
        criticality=payload.criticality,
        business_impact=payload.business_impact,
        replacement_difficulty=payload.replacement_difficulty,
        vacancy_risk=payload.vacancy_risk,
        identified_by=current_user.id,
        review_date=payload.review_date,
        status=payload.status,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)

    r = CriticalRoleResponse.from_orm(cr)
    r.position_title = pos.title
    r.position_code = pos.position_code
    return r


@router.get("/critical-roles/{cr_id}", response_model=CriticalRoleResponse)
def get_critical_role(
    cr_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cr = db.query(CriticalRole).filter(CriticalRole.id == cr_id, CriticalRole.tenant_id == tenant_id).first()
    if not cr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critical role not found")

    r = CriticalRoleResponse.from_orm(cr)
    pos = db.query(Position).filter(Position.id == cr.position_id).first()
    if pos:
        r.position_title = pos.title
        r.position_code = pos.position_code
    return r


@router.get("/succession-plans", response_model=List[SuccessionPlanResponse])
def list_succession_plans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plans = db.query(SuccessionPlan).filter(SuccessionPlan.tenant_id == tenant_id).all()
    resp = []
    for sp in plans:
        r = SuccessionPlanResponse.from_orm(sp)
        if sp.critical_role and sp.critical_role.position_id:
            pos = db.query(Position).filter(Position.id == sp.critical_role.position_id).first()
            if pos:
                r.critical_role_title = pos.title

        r.candidates = []
        for c in sp.candidates:
            c_resp = SuccessionCandidateResponse.from_orm(c)
            p = db.query(Person).filter(Person.id == c.person_id).first()
            if p:
                c_resp.person_name = getattr(p, "full_name", None) or "Employee"
            r.candidates.append(c_resp)

        resp.append(r)
    return resp


@router.post("/succession-plans", response_model=SuccessionPlanResponse, status_code=status.HTTP_201_CREATED)
def create_succession_plan(
    payload: SuccessionPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:succession:manage", db)
        or has_permission(current_user, "workforce_planning.succession.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Succession manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cr = db.query(CriticalRole).filter(CriticalRole.id == payload.critical_role_id, CriticalRole.tenant_id == tenant_id).first()
    if not cr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critical role not found")

    sp = SuccessionPlan(
        tenant_id=tenant_id,
        critical_role_id=payload.critical_role_id,
        target_date=payload.target_date,
        status=SuccessionStatus.ACTIVE.value,
        created_by=current_user.id,
    )
    db.add(sp)
    db.flush()

    for c in payload.candidates:
        cand = SuccessionCandidate(
            tenant_id=tenant_id,
            succession_plan_id=sp.id,
            person_id=c.person_id,
            readiness_level=c.readiness_level,
            development_actions=c.development_actions,
            target_readiness_date=c.target_readiness_date,
            nomination_status=c.nomination_status,
        )
        db.add(cand)

    db.commit()
    db.refresh(sp)
    return sp


@router.get("/succession-plans/{plan_id}", response_model=SuccessionPlanResponse)
def get_succession_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    sp = db.query(SuccessionPlan).filter(SuccessionPlan.id == plan_id, SuccessionPlan.tenant_id == tenant_id).first()
    if not sp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Succession plan not found")

    r = SuccessionPlanResponse.from_orm(sp)
    if sp.critical_role and sp.critical_role.position_id:
        pos = db.query(Position).filter(Position.id == sp.critical_role.position_id).first()
        if pos:
            r.critical_role_title = pos.title

    r.candidates = []
    for c in sp.candidates:
        c_resp = SuccessionCandidateResponse.from_orm(c)
        p = db.query(Person).filter(Person.id == c.person_id).first()
        if p:
            c_resp.person_name = getattr(p, "full_name", None) or "Employee"
        r.candidates.append(c_resp)

    return r


@router.post("/succession-plans/{plan_id}/candidates", response_model=SuccessionCandidateResponse, status_code=status.HTTP_201_CREATED)
def add_succession_candidate(
    plan_id: str,
    payload: SuccessionCandidateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    sp = db.query(SuccessionPlan).filter(SuccessionPlan.id == plan_id, SuccessionPlan.tenant_id == tenant_id).first()
    if not sp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Succession plan not found")

    cand = SuccessionCandidate(
        tenant_id=tenant_id,
        succession_plan_id=plan_id,
        person_id=payload.person_id,
        readiness_level=payload.readiness_level,
        development_actions=payload.development_actions,
        target_readiness_date=payload.target_readiness_date,
        nomination_status=payload.nomination_status,
    )
    db.add(cand)
    db.commit()
    db.refresh(cand)

    r = SuccessionCandidateResponse.from_orm(cand)
    p = db.query(Person).filter(Person.id == cand.person_id).first()
    if p:
        r.person_name = getattr(p, "full_name", None) or "Employee"
    return r


# ---------------------------------------------------------------------------
# 11. Talent Pools
# ---------------------------------------------------------------------------

@router.get("/talent-pools", response_model=List[TalentPoolResponse])
def list_talent_pools(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    pools = db.query(TalentPool).filter(TalentPool.tenant_id == tenant_id).all()
    resp = []
    for tp in pools:
        r = TalentPoolResponse.from_orm(tp)
        r.member_count = len(tp.members)
        resp.append(r)
    return resp


@router.post("/talent-pools", response_model=TalentPoolResponse, status_code=status.HTTP_201_CREATED)
def create_talent_pool(
    payload: TalentPoolCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:talent:manage", db)
        or has_permission(current_user, "workforce_planning.talent.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Talent manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    tp = TalentPool(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        purpose=payload.purpose,
        status=TalentPoolStatus.ACTIVE.value,
        owner_user_id=current_user.id,
    )
    db.add(tp)
    db.flush()

    for pid in payload.member_person_ids:
        mem = TalentPoolMember(
            tenant_id=tenant_id,
            talent_pool_id=tp.id,
            person_id=pid,
            source="HR_NOMINATION",
        )
        db.add(mem)

    db.commit()
    db.refresh(tp)

    r = TalentPoolResponse.from_orm(tp)
    r.member_count = len(payload.member_person_ids)
    return r


@router.get("/talent-pools/{pool_id}", response_model=TalentPoolResponse)
def get_talent_pool(
    pool_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    tp = db.query(TalentPool).filter(TalentPool.id == pool_id, TalentPool.tenant_id == tenant_id).first()
    if not tp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Talent pool not found")

    r = TalentPoolResponse.from_orm(tp)
    r.member_count = len(tp.members)
    r.members = []
    for m in tp.members:
        m_resp = TalentPoolMemberResponse.from_orm(m)
        p = db.query(Person).filter(Person.id == m.person_id).first()
        if p:
            m_resp.person_name = getattr(p, "full_name", None) or "Employee"
        r.members.append(m_resp)
    return r


@router.post("/talent-pools/{pool_id}/members", response_model=TalentPoolMemberResponse, status_code=status.HTTP_201_CREATED)
def add_talent_pool_member(
    pool_id: str,
    payload: TalentPoolMemberCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    tp = db.query(TalentPool).filter(TalentPool.id == pool_id, TalentPool.tenant_id == tenant_id).first()
    if not tp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Talent pool not found")

    mem = TalentPoolMember(
        tenant_id=tenant_id,
        talent_pool_id=pool_id,
        person_id=payload.person_id,
        source=payload.source,
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)

    r = TalentPoolMemberResponse.from_orm(mem)
    p = db.query(Person).filter(Person.id == mem.person_id).first()
    if p:
        r.person_name = getattr(p, "full_name", None) or "Employee"
    return r


# ---------------------------------------------------------------------------
# 12. Workforce Scenarios
# ---------------------------------------------------------------------------

@router.get("/scenarios", response_model=List[WorkforceScenarioResponse])
def list_scenarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    scenarios = db.query(WorkforceScenario).filter(WorkforceScenario.tenant_id == tenant_id).all()
    resp = []
    for s in scenarios:
        r = WorkforceScenarioResponse.from_orm(s)
        r.total_headcount_delta = sum(float(l.headcount_delta) for l in s.lines)
        r.total_cost_delta = sum(float(l.cost_delta) for l in s.lines)
        resp.append(r)
    return resp


@router.post("/scenarios", response_model=WorkforceScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: WorkforceScenarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:scenarios:manage", db)
        or has_permission(current_user, "workforce_planning.scenarios.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scenarios manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    scenario = WorkforceScenario(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        scenario_type=payload.scenario_type,
        planning_horizon=payload.planning_horizon,
        status="ACTIVE",
        created_by=current_user.id,
    )
    db.add(scenario)
    db.flush()

    for l in payload.lines:
        line = WorkforceScenarioLine(
            tenant_id=tenant_id,
            scenario_id=scenario.id,
            organization_unit_id=l.organization_unit_id,
            job_family=l.job_family,
            job_level=l.job_level,
            period=l.period,
            headcount_delta=l.headcount_delta,
            hiring_delta=l.hiring_delta,
            exit_delta=l.exit_delta,
            cost_delta=l.cost_delta,
            notes=l.notes,
        )
        db.add(line)

    db.commit()
    db.refresh(scenario)

    r = WorkforceScenarioResponse.from_orm(scenario)
    r.total_headcount_delta = sum(float(l.headcount_delta) for l in scenario.lines)
    r.total_cost_delta = sum(float(l.cost_delta) for l in scenario.lines)
    return r


@router.get("/scenarios/{scenario_id}", response_model=WorkforceScenarioResponse)
def get_scenario(
    scenario_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    s = db.query(WorkforceScenario).filter(WorkforceScenario.id == scenario_id, WorkforceScenario.tenant_id == tenant_id).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce scenario not found")

    r = WorkforceScenarioResponse.from_orm(s)
    r.total_headcount_delta = sum(float(l.headcount_delta) for l in s.lines)
    r.total_cost_delta = sum(float(l.cost_delta) for l in s.lines)
    return r


# ---------------------------------------------------------------------------
# 13. Hiring Plan & Lines
# ---------------------------------------------------------------------------

@router.get("/hiring-plans", response_model=List[WorkforceHiringPlanResponse])
def list_hiring_plans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plans = db.query(WorkforceHiringPlan).filter(WorkforceHiringPlan.tenant_id == tenant_id).all()
    resp = []
    for p in plans:
        r = WorkforceHiringPlanResponse.from_orm(p)
        r.total_planned_hires = sum(float(l.planned_headcount) for l in p.lines)
        r.total_estimated_hiring_cost = sum(float(l.estimated_cost) for l in p.lines)
        resp.append(r)
    return resp


@router.post("/hiring-plans", response_model=WorkforceHiringPlanResponse, status_code=status.HTTP_201_CREATED)
def create_hiring_plan(
    payload: WorkforceHiringPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:hiring:manage", db)
        or has_permission(current_user, "workforce_planning.hiring.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hiring manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = WorkforceHiringPlan(
        tenant_id=tenant_id,
        name=payload.name,
        fiscal_year=payload.fiscal_year,
        status=HiringPlanStatus.DRAFT.value,
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()

    for l in payload.lines:
        line = HiringPlanLine(
            tenant_id=tenant_id,
            plan_id=plan.id,
            organization_unit_id=l.organization_unit_id,
            position_id=l.position_id,
            job_family=l.job_family,
            job_level=l.job_level,
            planned_open_date=l.planned_open_date,
            planned_join_date=l.planned_join_date,
            planned_headcount=l.planned_headcount,
            estimated_cost=l.estimated_cost,
            recruitment_priority=l.recruitment_priority,
            source_requisition_id=l.source_requisition_id,
        )
        db.add(line)

    db.commit()
    db.refresh(plan)

    r = WorkforceHiringPlanResponse.from_orm(plan)
    r.total_planned_hires = sum(float(l.planned_headcount) for l in plan.lines)
    return r


@router.get("/hiring-plans/{plan_id}", response_model=WorkforceHiringPlanResponse)
def get_hiring_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    p = db.query(WorkforceHiringPlan).filter(WorkforceHiringPlan.id == plan_id, WorkforceHiringPlan.tenant_id == tenant_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hiring plan not found")

    r = WorkforceHiringPlanResponse.from_orm(p)
    r.total_planned_hires = sum(float(l.planned_headcount) for l in p.lines)
    return r


# ---------------------------------------------------------------------------
# 14. Internal Mobility Planning
# ---------------------------------------------------------------------------

@router.get("/mobility-plans", response_model=List[MobilityPlanResponse])
def list_mobility_plans(
    request: Request,
    plan_status: Optional[str] = Query(None, alias="status"),
    person_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(MobilityPlan).filter(MobilityPlan.tenant_id == tenant_id)
    if plan_status:
        query = query.filter(MobilityPlan.status == plan_status)
    if person_id:
        query = query.filter(MobilityPlan.person_id == person_id)

    plans = query.all()
    resp = []
    for mp in plans:
        r = MobilityPlanResponse.from_orm(mp)
        p = db.query(Person).filter(Person.id == mp.person_id).first()
        if p:
            r.person_name = getattr(p, "full_name", None) or "Employee"
        if mp.current_position_id:
            c_pos = db.query(Position).filter(Position.id == mp.current_position_id).first()
            if c_pos:
                r.current_position_title = c_pos.title
        if mp.target_position_id:
            t_pos = db.query(Position).filter(Position.id == mp.target_position_id).first()
            if t_pos:
                r.target_position_title = t_pos.title
        resp.append(r)
    return resp


@router.post("/mobility-plans", response_model=MobilityPlanResponse, status_code=status.HTTP_201_CREATED)
def create_mobility_plan(
    payload: MobilityPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_wf(current_user, db)
        or has_permission(current_user, "workforce_planning:mobility:manage", db)
        or has_permission(current_user, "workforce_planning.mobility.manage", db)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mobility manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    mp = MobilityPlan(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        current_position_id=payload.current_position_id,
        target_position_id=payload.target_position_id,
        mobility_type=payload.mobility_type,
        target_date=payload.target_date,
        status=MobilityStatus.DRAFT.value,
        created_by=current_user.id,
    )
    db.add(mp)
    db.commit()
    db.refresh(mp)

    r = MobilityPlanResponse.from_orm(mp)
    p = db.query(Person).filter(Person.id == mp.person_id).first()
    if p:
        r.person_name = getattr(p, "full_name", None) or "Employee"
    return r


@router.put("/mobility-plans/{plan_id}", response_model=MobilityPlanResponse)
def update_mobility_plan(
    plan_id: str,
    payload: MobilityPlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning manage permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    mp = db.query(MobilityPlan).filter(MobilityPlan.id == plan_id, MobilityPlan.tenant_id == tenant_id).first()
    if not mp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobility plan not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(mp, k, v)

    db.commit()
    db.refresh(mp)
    return mp


# ---------------------------------------------------------------------------
# 15. Attrition Impact Analysis & Plan vs. Actual
# ---------------------------------------------------------------------------

@router.get("/attrition-impact", response_model=AttritionScenarioImpact)
def get_attrition_impact(
    request: Request,
    scenario_name: str = Query("Standard Turnover Baseline"),
    assumed_rate: float = Query(12.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return analyze_attrition_scenario_impact(db, tenant_id, scenario_name, assumed_rate)


@router.get("/plan-vs-actual", response_model=PlanVsActualComparison)
def get_plan_vs_actual(
    request: Request,
    fiscal_year: str = Query("2026-2027"),
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_wf(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workforce planning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return calculate_plan_vs_actual(db, tenant_id, fiscal_year, month)
