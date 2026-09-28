"""
learning.py - Module 18 API Router: Enterprise Learning, Skills & Career Development
Zeramai Enterprise HRMS
"""
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import User, UserRole, Person, Tenant
from app.models_workforce_planning import (
    Skill, SkillLevel, EmployeeSkill, SkillGapAnalysis, Position
)
from app.models_learning import (
    TrainingProvider, LearningCourse, LearningModule, CourseContent,
    LearningPath, LearningPathCourse, CourseSkillMapping,
    LearningEnrollment, LearningProgress, LearningAssessment,
    AssessmentQuestion, AssessmentAttempt, Certification,
    EmployeeCertification, TrainingRequirement, TrainingAssignment,
    LearningPlan, LearningPlanItem, DevelopmentPlan, DevelopmentGoal,
    CareerFramework, CareerLevel, CareerPath,
    CareerOpportunity, CareerApplication,
    MentoringProgram, MentoringRelationship,
    SkillDevelopmentAction, SkillEvidence,
    CourseLifecycleStatus, LearningEnrollmentStatus,
    CertificationVerificationStatus, OpportunityStatus,
    CareerApplicationStatus, MentoringStatus,
)
from app.schemas_learning import (
    TrainingProviderCreate, TrainingProviderUpdate, TrainingProviderResponse,
    LearningCourseCreate, LearningCourseUpdate, LearningCourseResponse,
    LearningModuleCreate, LearningModuleResponse,
    LearningPathCreate, LearningPathUpdate, LearningPathResponse, LearningPathCourseResponse,
    CourseSkillMappingCreate, CourseSkillMappingResponse,
    LearningEnrollmentCreate, LearningEnrollmentUpdate, LearningEnrollmentResponse,
    LearningProgressUpdate, LearningProgressResponse,
    LearningAssessmentCreate, LearningAssessmentResponse, AssessmentQuestionResponse,
    AssessmentAttemptCreate, AssessmentAttemptResponse,
    CertificationCreate, CertificationResponse,
    EmployeeCertificationCreate, EmployeeCertificationVerify, EmployeeCertificationResponse,
    TrainingRequirementCreate, TrainingRequirementResponse,
    TrainingAssignmentCreate, TrainingAssignmentResponse,
    LearningPlanCreate, LearningPlanResponse,
    DevelopmentPlanCreate, DevelopmentPlanResponse,
    DevelopmentGoalCreate, DevelopmentGoalResponse,
    CareerFrameworkCreate, CareerFrameworkResponse,
    CareerLevelCreate, CareerLevelResponse,
    CareerPathCreate, CareerPathResponse,
    CareerOpportunityCreate, CareerOpportunityResponse,
    CareerApplicationCreate, CareerApplicationResponse,
    MentoringProgramCreate, MentoringProgramResponse,
    MentoringRelationshipCreate, MentoringRelationshipResponse,
    SkillDevelopmentActionCreate, SkillDevelopmentActionResponse,
    SkillEvidenceCreate, SkillEvidenceResponse,
    LearningAnalyticsResponse, EmployeeLearningDashboard, ManagerTeamLearningDashboard,
)
from app.services.learning_service import (
    validate_mentoring_relationship,
    evaluate_assessment_attempt,
    get_learning_analytics,
    get_employee_dashboard_data,
    get_manager_team_dashboard_data,
)

router = APIRouter(prefix="/api/v3/learning", tags=["Module 18 - Enterprise Learning & Career Development"])


# ---------------------------------------------------------------------------
# Security & Tenant Isolation Helpers
# ---------------------------------------------------------------------------

def _resolve_tenant_id(request: Request, db: Session, current_user: Optional[User] = None) -> str:
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


def _can_read_learning(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER, UserRole.EMPLOYEE, UserRole.FINANCE)
        or has_permission(user, "learning:read", db)
        or has_permission(user, "learning.read", db)
    )


def _can_manage_learning(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "learning:manage", db)
        or has_permission(user, "learning.manage", db)
    )


def _can_manage_catalog(user: User, db: Session) -> bool:
    return (
        _can_manage_learning(user, db)
        or has_permission(user, "learning:catalog:manage", db)
        or has_permission(user, "learning.catalog.manage", db)
    )


def _can_manage_enrollment(user: User, db: Session) -> bool:
    return (
        _can_manage_learning(user, db)
        or has_permission(user, "learning:enrollment:manage", db)
        or has_permission(user, "learning.enrollment.manage", db)
    )


def _can_manage_assessment(user: User, db: Session) -> bool:
    return (
        _can_manage_learning(user, db)
        or has_permission(user, "learning:assessment:manage", db)
        or has_permission(user, "learning.assessment.manage", db)
    )


def _can_manage_certification(user: User, db: Session) -> bool:
    return (
        _can_manage_learning(user, db)
        or has_permission(user, "learning:certification:manage", db)
        or has_permission(user, "learning.certification.manage", db)
    )


def _can_manage_mentoring(user: User, db: Session) -> bool:
    return (
        _can_manage_learning(user, db)
        or has_permission(user, "learning:mentoring:manage", db)
        or has_permission(user, "learning.mentoring.manage", db)
    )


def _can_manage_career(user: User, db: Session) -> bool:
    return (
        _can_manage_learning(user, db)
        or has_permission(user, "learning:career:manage", db)
        or has_permission(user, "learning.career.manage", db)
    )


# ---------------------------------------------------------------------------
# 1. Dashboards & Analytics
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=EmployeeLearningDashboard)
def get_employee_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id
    data = get_employee_dashboard_data(db, tenant_id, person_id)
    return EmployeeLearningDashboard(**data)


@router.get("/dashboard/team", response_model=ManagerTeamLearningDashboard)
def get_manager_team_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        current_user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(current_user, "learning:manage", db)
        or has_permission(current_user, "learning.manage", db)
    ):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Manager or HR permission required for team learning dashboard")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    manager_person_id = current_user.person_id or current_user.id
    data = get_manager_team_dashboard_data(db, tenant_id, manager_person_id)
    return ManagerTeamLearningDashboard(**data)


@router.get("/analytics", response_model=LearningAnalyticsResponse)
def get_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_learning(current_user, db)
        or has_permission(current_user, "learning:analytics:read", db)
        or has_permission(current_user, "learning.analytics.read", db)
    ):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning analytics permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    data = get_learning_analytics(db, tenant_id)
    return LearningAnalyticsResponse(**data)


# ---------------------------------------------------------------------------
# 2. Training Providers
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=List[TrainingProviderResponse])
def list_providers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    providers = db.query(TrainingProvider).filter(TrainingProvider.tenant_id == tenant_id).all()
    return providers


@router.post("/providers", response_model=TrainingProviderResponse, status_code=http_status.HTTP_201_CREATED)
def create_provider(
    payload: TrainingProviderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    provider = TrainingProvider(
        tenant_id=tenant_id,
        name=payload.name,
        provider_type=payload.provider_type,
        website=payload.website,
        contact_reference=payload.contact_reference,
        active=payload.active,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


# ---------------------------------------------------------------------------
# 3. Learning Catalog Courses & Modules
# ---------------------------------------------------------------------------

@router.get("/courses", response_model=List[LearningCourseResponse])
def list_courses(
    request: Request,
    category: Optional[str] = Query(None),
    course_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(LearningCourse).filter(
        or_(LearningCourse.tenant_id == tenant_id, LearningCourse.tenant_id.is_(None))
    )
    if category:
        query = query.filter(LearningCourse.category == category)
    if course_status:
        query = query.filter(LearningCourse.status == course_status)
    else:
        # Non-managers only see published courses unless explicitly searching
        if not _can_manage_catalog(current_user, db):
            query = query.filter(LearningCourse.status == CourseLifecycleStatus.PUBLISHED.value)

    courses = query.all()
    resp = []
    for c in courses:
        r = LearningCourseResponse.from_orm(c)
        r.module_count = len(c.modules)
        if c.provider:
            r.provider_name = c.provider.name
        resp.append(r)
    return resp


@router.post("/courses", response_model=LearningCourseResponse, status_code=http_status.HTTP_201_CREATED)
def create_course(
    payload: LearningCourseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Check unique course code per tenant
    existing = db.query(LearningCourse).filter(
        LearningCourse.tenant_id == tenant_id,
        LearningCourse.course_code == payload.course_code,
    ).first()
    if existing:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Course code {payload.course_code} already exists")

    course = LearningCourse(
        tenant_id=tenant_id,
        course_code=payload.course_code,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        learning_type=payload.learning_type,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        provider_id=payload.provider_id,
        delivery_mode=payload.delivery_mode,
        language=payload.language,
        status=payload.status,
        created_by=current_user.id,
    )
    db.add(course)
    db.flush()

    if payload.modules:
        for idx, m_data in enumerate(payload.modules):
            mod = LearningModule(
                course_id=course.id,
                title=m_data.title,
                description=m_data.description,
                sequence=m_data.sequence or (idx + 1),
                duration_minutes=m_data.duration_minutes,
                mandatory=m_data.mandatory,
            )
            db.add(mod)

    db.commit()
    db.refresh(course)

    r = LearningCourseResponse.from_orm(course)
    r.module_count = len(course.modules)
    return r


@router.get("/courses/{course_id}", response_model=LearningCourseResponse)
def get_course(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    course = db.query(LearningCourse).filter(
        LearningCourse.id == course_id,
        or_(LearningCourse.tenant_id == tenant_id, LearningCourse.tenant_id.is_(None)),
    ).first()
    if not course:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    r = LearningCourseResponse.from_orm(course)
    r.module_count = len(course.modules)
    if course.provider:
        r.provider_name = course.provider.name
    return r


@router.put("/courses/{course_id}", response_model=LearningCourseResponse)
def update_course(
    course_id: str,
    payload: LearningCourseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    course = db.query(LearningCourse).filter(
        LearningCourse.id == course_id,
        LearningCourse.tenant_id == tenant_id,
    ).first()
    if not course:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(course, k, v)

    db.commit()
    db.refresh(course)
    r = LearningCourseResponse.from_orm(course)
    r.module_count = len(course.modules)
    return r


@router.post("/courses/{course_id}/publish", response_model=LearningCourseResponse)
def publish_course(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    course = db.query(LearningCourse).filter(
        LearningCourse.id == course_id,
        LearningCourse.tenant_id == tenant_id,
    ).first()
    if not course:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    course.status = CourseLifecycleStatus.PUBLISHED.value
    db.commit()
    db.refresh(course)
    return LearningCourseResponse.from_orm(course)


@router.post("/courses/{course_id}/archive", response_model=LearningCourseResponse)
def archive_course(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    course = db.query(LearningCourse).filter(
        LearningCourse.id == course_id,
        LearningCourse.tenant_id == tenant_id,
    ).first()
    if not course:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    course.status = CourseLifecycleStatus.ARCHIVED.value
    db.commit()
    db.refresh(course)
    return LearningCourseResponse.from_orm(course)


@router.post("/courses/{course_id}/modules", response_model=LearningModuleResponse, status_code=http_status.HTTP_201_CREATED)
def add_course_module(
    course_id: str,
    payload: LearningModuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    course = db.query(LearningCourse).filter(
        LearningCourse.id == course_id,
        LearningCourse.tenant_id == tenant_id,
    ).first()
    if not course:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    mod = LearningModule(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        sequence=payload.sequence,
        duration_minutes=payload.duration_minutes,
        mandatory=payload.mandatory,
    )
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return LearningModuleResponse.from_orm(mod)


# ---------------------------------------------------------------------------
# 4. Learning Paths
# ---------------------------------------------------------------------------

@router.get("/paths", response_model=List[LearningPathResponse])
def list_learning_paths(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    paths = db.query(LearningPath).filter(LearningPath.tenant_id == tenant_id).all()
    resp = []
    for p in paths:
        r = LearningPathResponse.from_orm(p)
        r.path_courses = []
        for pc in p.path_courses:
            pc_resp = LearningPathCourseResponse.from_orm(pc)
            if pc.course:
                pc_resp.course_title = pc.course.title
                pc_resp.course_code = pc.course.course_code
            r.path_courses.append(pc_resp)
        resp.append(r)
    return resp


@router.post("/paths", response_model=LearningPathResponse, status_code=http_status.HTTP_201_CREATED)
def create_learning_path(
    payload: LearningPathCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    lp = LearningPath(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        target_role=payload.target_role,
        target_job_family=payload.target_job_family,
        status=payload.status,
        created_by=current_user.id,
    )
    db.add(lp)
    db.flush()

    if payload.courses:
        for idx, item in enumerate(payload.courses):
            lpc = LearningPathCourse(
                learning_path_id=lp.id,
                course_id=item.course_id,
                sequence=item.sequence or (idx + 1),
                mandatory=item.mandatory,
            )
            db.add(lpc)

    db.commit()
    db.refresh(lp)
    return LearningPathResponse.from_orm(lp)


@router.get("/paths/{path_id}", response_model=LearningPathResponse)
def get_learning_path(
    path_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    lp = db.query(LearningPath).filter(LearningPath.id == path_id, LearningPath.tenant_id == tenant_id).first()
    if not lp:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Learning path not found")

    r = LearningPathResponse.from_orm(lp)
    r.path_courses = []
    for pc in lp.path_courses:
        pc_resp = LearningPathCourseResponse.from_orm(pc)
        if pc.course:
            pc_resp.course_title = pc.course.title
            pc_resp.course_code = pc.course.course_code
        r.path_courses.append(pc_resp)
    return r


# ---------------------------------------------------------------------------
# 5. Course Skill Mapping
# ---------------------------------------------------------------------------

@router.post("/courses/{course_id}/skills", response_model=CourseSkillMappingResponse, status_code=http_status.HTTP_201_CREATED)
def map_course_to_skill(
    course_id: str,
    payload: CourseSkillMappingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_catalog(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Catalog management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    c = db.query(LearningCourse).filter(LearningCourse.id == course_id).first()
    if not c:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    sk = db.query(Skill).filter(Skill.id == payload.skill_id).first()
    if not sk:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Skill not found")

    mapping = CourseSkillMapping(
        tenant_id=tenant_id,
        course_id=course_id,
        skill_id=payload.skill_id,
        target_skill_level_id=payload.target_skill_level_id,
        proficiency_gain=payload.proficiency_gain,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    r = CourseSkillMappingResponse.from_orm(mapping)
    r.skill_name = sk.name
    r.skill_code = sk.code
    return r


# ---------------------------------------------------------------------------
# 6. Learning Enrollments & Progress
# ---------------------------------------------------------------------------

@router.get("/enrollments", response_model=List[LearningEnrollmentResponse])
def list_enrollments(
    request: Request,
    person_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    enr_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Ownership enforcement: employee can only see own enrollments
    if not _can_manage_enrollment(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(LearningEnrollment).filter(LearningEnrollment.tenant_id == tenant_id)
    if person_id:
        query = query.filter(LearningEnrollment.person_id == person_id)
    if course_id:
        query = query.filter(LearningEnrollment.course_id == course_id)
    if enr_status:
        query = query.filter(LearningEnrollment.status == enr_status)

    enrollments = query.all()
    resp = []
    for e in enrollments:
        r = LearningEnrollmentResponse.from_orm(e)
        if e.course:
            r.course_title = e.course.title
        if e.person:
            r.person_name = getattr(e.person, "full_name", "Employee")
        resp.append(r)
    return resp


@router.post("/enrollments", response_model=LearningEnrollmentResponse, status_code=http_status.HTTP_201_CREATED)
def create_enrollment(
    payload: LearningEnrollmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Permissions: employee can self-enroll, manager/admin can enroll others
    if not _can_manage_enrollment(current_user, db):
        if payload.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot enroll other employees")

    # Idempotency check: don't create duplicate active enrollment for same course & person
    if payload.course_id:
        existing = db.query(LearningEnrollment).filter(
            LearningEnrollment.tenant_id == tenant_id,
            LearningEnrollment.person_id == payload.person_id,
            LearningEnrollment.course_id == payload.course_id,
            LearningEnrollment.status.in_([
                LearningEnrollmentStatus.ASSIGNED.value,
                LearningEnrollmentStatus.ENROLLED.value,
                LearningEnrollmentStatus.IN_PROGRESS.value,
            ]),
        ).first()
        if existing:
            r = LearningEnrollmentResponse.from_orm(existing)
            if existing.course:
                r.course_title = existing.course.title
            return r

    enr = LearningEnrollment(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        course_id=payload.course_id,
        learning_path_id=payload.learning_path_id,
        enrollment_type=payload.enrollment_type,
        status=LearningEnrollmentStatus.ENROLLED.value,
        due_at=payload.due_at,
        assigned_by=current_user.id if payload.enrollment_type == "ASSIGNED" else None,
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)

    r = LearningEnrollmentResponse.from_orm(enr)
    if enr.course:
        r.course_title = enr.course.title
    return r


@router.get("/enrollments/{enrollment_id}", response_model=LearningEnrollmentResponse)
def get_enrollment(
    enrollment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    enr = db.query(LearningEnrollment).filter(
        LearningEnrollment.id == enrollment_id,
        LearningEnrollment.tenant_id == tenant_id,
    ).first()
    if not enr:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    # Scope check
    if not _can_manage_enrollment(current_user, db):
        if enr.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied to this enrollment record")

    r = LearningEnrollmentResponse.from_orm(enr)
    if enr.course:
        r.course_title = enr.course.title
    if enr.person:
        r.person_name = getattr(enr.person, "full_name", "Employee")
    return r


@router.post("/enrollments/{enrollment_id}/progress", response_model=LearningEnrollmentResponse)
def update_enrollment_progress(
    enrollment_id: str,
    payload: LearningProgressUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    enr = db.query(LearningEnrollment).filter(
        LearningEnrollment.id == enrollment_id,
        LearningEnrollment.tenant_id == tenant_id,
    ).first()
    if not enr:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    if not _can_manage_enrollment(current_user, db):
        if enr.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot update another employee's enrollment progress")

    enr.progress_percentage = min(100.0, max(0.0, payload.progress_percentage))
    if enr.progress_percentage > 0 and enr.status == LearningEnrollmentStatus.ENROLLED.value:
        enr.status = LearningEnrollmentStatus.IN_PROGRESS.value
        enr.started_at = datetime.utcnow()

    if enr.progress_percentage >= 100.0:
        enr.status = LearningEnrollmentStatus.COMPLETED.value
        enr.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(enr)

    r = LearningEnrollmentResponse.from_orm(enr)
    if enr.course:
        r.course_title = enr.course.title
    return r


# ---------------------------------------------------------------------------
# 7. Assessments & Attempts
# ---------------------------------------------------------------------------

@router.get("/assessments", response_model=List[LearningAssessmentResponse])
def list_assessments(
    request: Request,
    course_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(LearningAssessment).filter(LearningAssessment.tenant_id == tenant_id)
    if course_id:
        query = query.filter(LearningAssessment.course_id == course_id)

    assessments = query.all()
    resp = []
    for a in assessments:
        r = LearningAssessmentResponse.from_orm(a)
        r.question_count = len(a.questions)
        # Suppress correct_answers
        r.questions = [
            AssessmentQuestionResponse(
                id=q.id,
                assessment_id=q.assessment_id,
                question_type=q.question_type,
                question_text=q.question_text,
                options_json=q.options_json,
                sequence=q.sequence,
                points=q.points,
            ) for q in a.questions
        ]
        resp.append(r)
    return resp


@router.post("/assessments", response_model=LearningAssessmentResponse, status_code=http_status.HTTP_201_CREATED)
def create_assessment(
    payload: LearningAssessmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_assessment(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Assessment management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    assessment = LearningAssessment(
        tenant_id=tenant_id,
        course_id=payload.course_id,
        title=payload.title,
        passing_score=payload.passing_score,
        attempts_allowed=payload.attempts_allowed,
        duration_minutes=payload.duration_minutes,
        status="ACTIVE",
    )
    db.add(assessment)
    db.flush()

    if payload.questions:
        for idx, q_data in enumerate(payload.questions):
            q = AssessmentQuestion(
                assessment_id=assessment.id,
                question_type=q_data.question_type,
                question_text=q_data.question_text,
                options_json=q_data.options_json,
                correct_answer=q_data.correct_answer,
                sequence=q_data.sequence or (idx + 1),
                points=q_data.points,
            )
            db.add(q)

    db.commit()
    db.refresh(assessment)

    r = LearningAssessmentResponse.from_orm(assessment)
    r.question_count = len(assessment.questions)
    r.questions = [
        AssessmentQuestionResponse(
            id=q.id,
            assessment_id=q.assessment_id,
            question_type=q.question_type,
            question_text=q.question_text,
            options_json=q.options_json,
            sequence=q.sequence,
            points=q.points,
        ) for q in assessment.questions
    ]
    return r


@router.get("/assessments/{assessment_id}", response_model=LearningAssessmentResponse)
def get_assessment(
    assessment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    a = db.query(LearningAssessment).filter(
        LearningAssessment.id == assessment_id,
        LearningAssessment.tenant_id == tenant_id,
    ).first()
    if not a:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    r = LearningAssessmentResponse.from_orm(a)
    r.question_count = len(a.questions)
    r.questions = [
        AssessmentQuestionResponse(
            id=q.id,
            assessment_id=q.assessment_id,
            question_type=q.question_type,
            question_text=q.question_text,
            options_json=q.options_json,
            sequence=q.sequence,
            points=q.points,
        ) for q in a.questions
    ]
    return r


@router.post("/assessments/{assessment_id}/attempt", response_model=AssessmentAttemptResponse, status_code=http_status.HTTP_201_CREATED)
def submit_attempt(
    assessment_id: str,
    payload: AssessmentAttemptCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id

    attempt = evaluate_assessment_attempt(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        person_id=person_id,
        enrollment_id=payload.enrollment_id,
        answers=payload.answers,
    )
    return AssessmentAttemptResponse.from_orm(attempt)


# ---------------------------------------------------------------------------
# 8. Certifications & Expiry Tracking
# ---------------------------------------------------------------------------

@router.get("/certifications", response_model=List[CertificationResponse])
def list_certifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    certs = db.query(Certification).filter(Certification.tenant_id == tenant_id).all()
    return certs


@router.post("/certifications", response_model=CertificationResponse, status_code=http_status.HTTP_201_CREATED)
def create_certification(
    payload: CertificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_certification(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Certification management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cert = Certification(
        tenant_id=tenant_id,
        name=payload.name,
        issuing_body=payload.issuing_body,
        description=payload.description,
        validity_months=payload.validity_months,
        status=payload.status,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.get("/employee-certifications", response_model=List[EmployeeCertificationResponse])
def list_employee_certifications(
    request: Request,
    person_id: Optional[str] = Query(None),
    ver_status: Optional[str] = Query(None, alias="verification_status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # If employee, restrict to own certifications
    if not _can_manage_certification(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(EmployeeCertification).filter(EmployeeCertification.tenant_id == tenant_id)
    if person_id:
        query = query.filter(EmployeeCertification.person_id == person_id)
    if ver_status:
        query = query.filter(EmployeeCertification.verification_status == ver_status)

    records = query.all()
    today = date.today()
    resp = []
    for r in records:
        res = EmployeeCertificationResponse.from_orm(r)
        if r.certification:
            res.certification_name = r.certification.name
            res.issuing_body = r.certification.issuing_body
        if r.person:
            res.person_name = getattr(r.person, "full_name", "Employee")
        res.is_expired = bool(r.expiry_date and r.expiry_date < today)
        resp.append(res)
    return resp


@router.post("/employee-certifications", response_model=EmployeeCertificationResponse, status_code=http_status.HTTP_201_CREATED)
def submit_employee_certification(
    payload: EmployeeCertificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_certification(current_user, db):
        if payload.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot upload credentials for other employees")

    cert = db.query(Certification).filter(Certification.id == payload.certification_id).first()
    if not cert:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Certification not found")

    ec = EmployeeCertification(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        certification_id=payload.certification_id,
        credential_number=payload.credential_number,
        issued_date=payload.issued_date,
        expiry_date=payload.expiry_date,
        verification_status=CertificationVerificationStatus.PENDING.value,
        document_reference=payload.document_reference,
    )
    db.add(ec)
    db.commit()
    db.refresh(ec)

    res = EmployeeCertificationResponse.from_orm(ec)
    res.certification_name = cert.name
    res.issuing_body = cert.issuing_body
    return res


@router.post("/employee-certifications/{cert_id}/verify", response_model=EmployeeCertificationResponse)
def verify_employee_certification(
    cert_id: str,
    payload: EmployeeCertificationVerify,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_certification(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Certification management permission required to verify")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    ec = db.query(EmployeeCertification).filter(
        EmployeeCertification.id == cert_id,
        EmployeeCertification.tenant_id == tenant_id,
    ).first()
    if not ec:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Employee certification not found")

    ec.verification_status = payload.verification_status
    ec.verified_by = current_user.id
    ec.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(ec)

    res = EmployeeCertificationResponse.from_orm(ec)
    if ec.certification:
        res.certification_name = ec.certification.name
        res.issuing_body = ec.certification.issuing_body
    return res


# ---------------------------------------------------------------------------
# 9. Training Requirements & Mandatory Assignments
# ---------------------------------------------------------------------------

@router.get("/training-requirements", response_model=List[TrainingRequirementResponse])
def list_training_requirements(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    reqs = db.query(TrainingRequirement).filter(TrainingRequirement.tenant_id == tenant_id).all()
    resp = []
    for r in reqs:
        res = TrainingRequirementResponse.from_orm(r)
        if r.course:
            res.course_title = r.course.title
        resp.append(res)
    return resp


@router.post("/training-requirements", response_model=TrainingRequirementResponse, status_code=http_status.HTTP_201_CREATED)
def create_training_requirement(
    payload: TrainingRequirementCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_learning(current_user, db)
        or has_permission(current_user, "learning:compliance:manage", db)
        or has_permission(current_user, "learning.compliance.manage", db)
    ):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Mandatory training management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    course = db.query(LearningCourse).filter(LearningCourse.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Course not found")

    tr = TrainingRequirement(
        tenant_id=tenant_id,
        name=payload.name,
        course_id=payload.course_id,
        applicability_rule=payload.applicability_rule,
        due_days=payload.due_days,
        recurrence=payload.recurrence,
        mandatory=payload.mandatory,
        compliance_reference=payload.compliance_reference,
        active=True,
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)

    res = TrainingRequirementResponse.from_orm(tr)
    res.course_title = course.title
    return res


@router.get("/training-assignments", response_model=List[TrainingAssignmentResponse])
def list_training_assignments(
    request: Request,
    person_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(TrainingAssignment).filter(TrainingAssignment.tenant_id == tenant_id)
    if person_id:
        query = query.filter(TrainingAssignment.person_id == person_id)

    assignments = query.all()
    resp = []
    for a in assignments:
        r = TrainingAssignmentResponse.from_orm(a)
        if a.requirement:
            r.requirement_name = a.requirement.name
        if a.person:
            r.person_name = getattr(a.person, "full_name", "Employee")
        resp.append(r)
    return resp


@router.post("/training-assignments", response_model=TrainingAssignmentResponse, status_code=http_status.HTTP_201_CREATED)
def assign_training(
    payload: TrainingAssignmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        _can_manage_learning(current_user, db)
        or has_permission(current_user, "learning:compliance:manage", db)
        or has_permission(current_user, "learning.compliance.manage", db)
    ):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Training assignment permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    req = db.query(TrainingRequirement).filter(
        TrainingRequirement.id == payload.requirement_id,
        TrainingRequirement.tenant_id == tenant_id,
    ).first()
    if not req:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Training requirement not found")

    assign = TrainingAssignment(
        tenant_id=tenant_id,
        requirement_id=payload.requirement_id,
        person_id=payload.person_id,
        assigned_at=datetime.utcnow(),
        due_at=payload.due_at,
        status="ASSIGNED",
    )
    db.add(assign)
    db.commit()
    db.refresh(assign)

    r = TrainingAssignmentResponse.from_orm(assign)
    r.requirement_name = req.name
    return r


# ---------------------------------------------------------------------------
# 10. Learning Plans
# ---------------------------------------------------------------------------

@router.get("/learning-plans", response_model=List[LearningPlanResponse])
def list_learning_plans(
    request: Request,
    person_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(LearningPlan).filter(LearningPlan.tenant_id == tenant_id)
    if person_id:
        query = query.filter(LearningPlan.person_id == person_id)

    plans = query.all()
    resp = []
    for lp in plans:
        r = LearningPlanResponse.from_orm(lp)
        if lp.person:
            r.person_name = getattr(lp.person, "full_name", "Employee")
        resp.append(r)
    return resp


@router.post("/learning-plans", response_model=LearningPlanResponse, status_code=http_status.HTTP_201_CREATED)
def create_learning_plan(
    payload: LearningPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        if payload.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot create learning plan for other employees")

    lp = LearningPlan(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        name=payload.name,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status="DRAFT",
        created_by=current_user.id,
    )
    db.add(lp)
    db.flush()

    if payload.items:
        for it in payload.items:
            item = LearningPlanItem(
                tenant_id=tenant_id,
                plan_id=lp.id,
                course_id=it.course_id,
                learning_path_id=it.learning_path_id,
                skill_id=it.skill_id,
                target_skill_level_id=it.target_skill_level_id,
                target_date=it.target_date,
                priority=it.priority,
                status="PLANNED",
            )
            db.add(item)

    db.commit()
    db.refresh(lp)
    return LearningPlanResponse.from_orm(lp)


# ---------------------------------------------------------------------------
# 11. Individual Development Plans (IDP) & Confidential Notes
# ---------------------------------------------------------------------------

@router.get("/development-plans", response_model=List[DevelopmentPlanResponse])
def list_development_plans(
    request: Request,
    person_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    is_privileged = (
        current_user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(current_user, "learning:development:manage", db)
        or has_permission(current_user, "learning.development.manage", db)
    )

    if not is_privileged:
        person_id = current_user.person_id or current_user.id

    query = db.query(DevelopmentPlan).filter(DevelopmentPlan.tenant_id == tenant_id)
    if person_id:
        query = query.filter(DevelopmentPlan.person_id == person_id)

    plans = query.all()
    resp = []
    for dp in plans:
        r = DevelopmentPlanResponse.from_orm(dp)
        if dp.person:
            r.person_name = getattr(dp.person, "full_name", "Employee")
        # Confidential notes protection: redact manager notes for normal employee queries!
        if not is_privileged:
            r.manager_notes = None
        resp.append(r)
    return resp


@router.post("/development-plans", response_model=DevelopmentPlanResponse, status_code=http_status.HTTP_201_CREATED)
def create_development_plan(
    payload: DevelopmentPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    is_privileged = (
        current_user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(current_user, "learning:development:manage", db)
        or has_permission(current_user, "learning.development.manage", db)
    )

    if not is_privileged:
        if payload.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot create development plans for other employees")
        # Employees cannot set manager notes
        payload.manager_notes = None

    dp = DevelopmentPlan(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        current_role=payload.current_role,
        target_role=payload.target_role,
        career_direction=payload.career_direction,
        review_period=payload.review_period,
        status="ACTIVE",
        employee_notes=payload.employee_notes,
        manager_notes=payload.manager_notes,
    )
    db.add(dp)
    db.flush()

    if payload.goals:
        for g_data in payload.goals:
            goal = DevelopmentGoal(
                tenant_id=tenant_id,
                development_plan_id=dp.id,
                title=g_data.title,
                description=g_data.description,
                skill_id=g_data.skill_id,
                target_level_id=g_data.target_level_id,
                due_date=g_data.due_date,
                status="ACTIVE",
            )
            db.add(goal)

    db.commit()
    db.refresh(dp)

    r = DevelopmentPlanResponse.from_orm(dp)
    if not is_privileged:
        r.manager_notes = None
    return r


@router.post("/development-goals", response_model=DevelopmentGoalResponse, status_code=http_status.HTTP_201_CREATED)
def add_development_goal(
    plan_id: str,
    payload: DevelopmentGoalCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    dp = db.query(DevelopmentPlan).filter(
        DevelopmentPlan.id == plan_id,
        DevelopmentPlan.tenant_id == tenant_id,
    ).first()
    if not dp:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Development plan not found")

    is_privileged = (
        current_user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(current_user, "learning:development:manage", db)
        or has_permission(current_user, "learning.development.manage", db)
    )
    if not is_privileged and dp.person_id != (current_user.person_id or current_user.id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot add goals to other employees' plans")

    goal = DevelopmentGoal(
        tenant_id=tenant_id,
        development_plan_id=plan_id,
        title=payload.title,
        description=payload.description,
        skill_id=payload.skill_id,
        target_level_id=payload.target_level_id,
        due_date=payload.due_date,
        status="ACTIVE",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return DevelopmentGoalResponse.from_orm(goal)


# ---------------------------------------------------------------------------
# 12. Career Frameworks, Levels & Paths
# ---------------------------------------------------------------------------

@router.get("/career-frameworks", response_model=List[CareerFrameworkResponse])
def list_career_frameworks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    frameworks = db.query(CareerFramework).filter(CareerFramework.tenant_id == tenant_id).all()
    resp = []
    for f in frameworks:
        r = CareerFrameworkResponse.from_orm(f)
        r.levels = [CareerLevelResponse.from_orm(l) for l in f.levels]
        r.paths = []
        for p in f.paths:
            p_resp = CareerPathResponse.from_orm(p)
            if p.from_level:
                p_resp.from_level_name = p.from_level.name
            if p.to_level:
                p_resp.to_level_name = p.to_level.name
            r.paths.append(p_resp)
        resp.append(r)
    return resp


@router.post("/career-frameworks", response_model=CareerFrameworkResponse, status_code=http_status.HTTP_201_CREATED)
def create_career_framework(
    payload: CareerFrameworkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_career(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Career framework management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cf = CareerFramework(
        tenant_id=tenant_id,
        name=payload.name,
        job_family=payload.job_family,
        description=payload.description,
        status="ACTIVE",
    )
    db.add(cf)
    db.flush()

    if payload.levels:
        for idx, lvl in enumerate(payload.levels):
            cl = CareerLevel(
                tenant_id=tenant_id,
                framework_id=cf.id,
                code=lvl.code,
                name=lvl.name,
                sequence=lvl.sequence or (idx + 1),
                description=lvl.description,
                expected_skill_profile=lvl.expected_skill_profile,
            )
            db.add(cl)

    db.commit()
    db.refresh(cf)
    return CareerFrameworkResponse.from_orm(cf)


@router.post("/career-frameworks/{framework_id}/levels", response_model=CareerLevelResponse, status_code=http_status.HTTP_201_CREATED)
def add_career_level(
    framework_id: str,
    payload: CareerLevelCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_career(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Career management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cf = db.query(CareerFramework).filter(
        CareerFramework.id == framework_id,
        CareerFramework.tenant_id == tenant_id,
    ).first()
    if not cf:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Career framework not found")

    lvl = CareerLevel(
        tenant_id=tenant_id,
        framework_id=framework_id,
        code=payload.code,
        name=payload.name,
        sequence=payload.sequence,
        description=payload.description,
        expected_skill_profile=payload.expected_skill_profile,
    )
    db.add(lvl)
    db.commit()
    db.refresh(lvl)
    return CareerLevelResponse.from_orm(lvl)


@router.post("/career-frameworks/{framework_id}/paths", response_model=CareerPathResponse, status_code=http_status.HTTP_201_CREATED)
def add_career_path(
    framework_id: str,
    payload: CareerPathCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_career(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Career management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    cf = db.query(CareerFramework).filter(
        CareerFramework.id == framework_id,
        CareerFramework.tenant_id == tenant_id,
    ).first()
    if not cf:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Career framework not found")

    cp = CareerPath(
        tenant_id=tenant_id,
        framework_id=framework_id,
        from_level_id=payload.from_level_id,
        to_level_id=payload.to_level_id,
        typical_requirements=payload.typical_requirements,
    )
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return CareerPathResponse.from_orm(cp)


# ---------------------------------------------------------------------------
# 13. Internal Career Opportunities & Applications
# ---------------------------------------------------------------------------

@router.get("/career-opportunities", response_model=List[CareerOpportunityResponse])
def list_career_opportunities(
    request: Request,
    opp_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(CareerOpportunity).filter(CareerOpportunity.tenant_id == tenant_id)
    if opp_status:
        query = query.filter(CareerOpportunity.status == opp_status)
    else:
        if not _can_manage_career(current_user, db):
            query = query.filter(CareerOpportunity.status == OpportunityStatus.OPEN.value)

    opps = query.all()
    resp = []
    for op in opps:
        r = CareerOpportunityResponse.from_orm(op)
        r.application_count = len(op.applications)
        resp.append(r)
    return resp


@router.post("/career-opportunities", response_model=CareerOpportunityResponse, status_code=http_status.HTTP_201_CREATED)
def create_career_opportunity(
    payload: CareerOpportunityCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_career(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Career management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if payload.position_id:
        pos = db.query(Position).filter(Position.id == payload.position_id).first()
        if not pos:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Position not found")

    opp = CareerOpportunity(
        tenant_id=tenant_id,
        position_id=payload.position_id,
        title=payload.title,
        description=payload.description,
        required_skills=payload.required_skills,
        required_level=payload.required_level,
        eligibility_rules=payload.eligibility_rules,
        application_deadline=payload.application_deadline,
        status=OpportunityStatus.OPEN.value,
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return CareerOpportunityResponse.from_orm(opp)


@router.get("/career-applications", response_model=List[CareerApplicationResponse])
def list_career_applications(
    request: Request,
    opportunity_id: Optional[str] = Query(None),
    person_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_career(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(CareerApplication).filter(CareerApplication.tenant_id == tenant_id)
    if opportunity_id:
        query = query.filter(CareerApplication.opportunity_id == opportunity_id)
    if person_id:
        query = query.filter(CareerApplication.person_id == person_id)

    apps = query.all()
    resp = []
    for a in apps:
        r = CareerApplicationResponse.from_orm(a)
        if a.opportunity:
            r.opportunity_title = a.opportunity.title
        if a.person:
            r.person_name = getattr(a.person, "full_name", "Employee")
        resp.append(r)
    return resp


@router.post("/career-applications", response_model=CareerApplicationResponse, status_code=http_status.HTTP_201_CREATED)
def apply_for_opportunity(
    payload: CareerApplicationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id

    opp = db.query(CareerOpportunity).filter(
        CareerOpportunity.id == payload.opportunity_id,
        CareerOpportunity.tenant_id == tenant_id,
    ).first()
    if not opp:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Career opportunity not found")

    if opp.status != OpportunityStatus.OPEN.value:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Opportunity is not open for applications")

    # Prevent duplicate active application
    existing = db.query(CareerApplication).filter(
        CareerApplication.tenant_id == tenant_id,
        CareerApplication.opportunity_id == payload.opportunity_id,
        CareerApplication.person_id == person_id,
        CareerApplication.status != CareerApplicationStatus.WITHDRAWN.value,
    ).first()
    if existing:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="You have already applied for this opportunity")

    app_rec = CareerApplication(
        tenant_id=tenant_id,
        opportunity_id=payload.opportunity_id,
        person_id=person_id,
        status=CareerApplicationStatus.SUBMITTED.value,
    )
    db.add(app_rec)
    db.commit()
    db.refresh(app_rec)

    r = CareerApplicationResponse.from_orm(app_rec)
    r.opportunity_title = opp.title
    return r


# ---------------------------------------------------------------------------
# 14. Mentoring Programs & Relationships
# ---------------------------------------------------------------------------

@router.get("/mentoring/programs", response_model=List[MentoringProgramResponse])
def list_mentoring_programs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    progs = db.query(MentoringProgram).filter(MentoringProgram.tenant_id == tenant_id).all()
    resp = []
    for p in progs:
        r = MentoringProgramResponse.from_orm(p)
        r.active_pairs_count = len([rel for rel in p.relationships if rel.status == MentoringStatus.ACTIVE.value])
        resp.append(r)
    return resp


@router.post("/mentoring/programs", response_model=MentoringProgramResponse, status_code=http_status.HTTP_201_CREATED)
def create_mentoring_program(
    payload: MentoringProgramCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_mentoring(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Mentoring management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    prog = MentoringProgram(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        duration_months=payload.duration_months,
        status="ACTIVE",
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return MentoringProgramResponse.from_orm(prog)


@router.get("/mentoring/relationships", response_model=List[MentoringRelationshipResponse])
def list_mentoring_relationships(
    request: Request,
    person_id: Optional[str] = Query(None),
    program_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_mentoring(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(MentoringRelationship).filter(MentoringRelationship.tenant_id == tenant_id)
    if program_id:
        query = query.filter(MentoringRelationship.program_id == program_id)
    if person_id:
        query = query.filter(
            or_(
                MentoringRelationship.mentor_person_id == person_id,
                MentoringRelationship.mentee_person_id == person_id,
            )
        )

    rels = query.all()
    resp = []
    for rel in rels:
        r = MentoringRelationshipResponse.from_orm(rel)
        if rel.mentor:
            r.mentor_name = getattr(rel.mentor, "full_name", "Mentor")
        if rel.mentee:
            r.mentee_name = getattr(rel.mentee, "full_name", "Mentee")
        if rel.program:
            r.program_name = rel.program.name
        resp.append(r)
    return resp


@router.post("/mentoring/relationships", response_model=MentoringRelationshipResponse, status_code=http_status.HTTP_201_CREATED)
def create_mentoring_relationship(
    payload: MentoringRelationshipCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    # Validate constraints: no self-mentoring, cross-tenant isolation, program existence
    validate_mentoring_relationship(
        db=db,
        tenant_id=tenant_id,
        program_id=payload.program_id,
        mentor_person_id=payload.mentor_person_id,
        mentee_person_id=payload.mentee_person_id,
    )

    rel = MentoringRelationship(
        tenant_id=tenant_id,
        program_id=payload.program_id,
        mentor_person_id=payload.mentor_person_id,
        mentee_person_id=payload.mentee_person_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=MentoringStatus.ACTIVE.value,
        goals=payload.goals,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    r = MentoringRelationshipResponse.from_orm(rel)
    if rel.mentor:
        r.mentor_name = getattr(rel.mentor, "full_name", "Mentor")
    if rel.mentee:
        r.mentee_name = getattr(rel.mentee, "full_name", "Mentee")
    return r


# ---------------------------------------------------------------------------
# 15. Skill Gap Remediation & Skill Evidence
# ---------------------------------------------------------------------------

@router.get("/skill-development-actions", response_model=List[SkillDevelopmentActionResponse])
def list_skill_development_actions(
    request: Request,
    person_id: Optional[str] = Query(None),
    skill_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(SkillDevelopmentAction).filter(SkillDevelopmentAction.tenant_id == tenant_id)
    if person_id:
        query = query.filter(SkillDevelopmentAction.person_id == person_id)
    if skill_id:
        query = query.filter(SkillDevelopmentAction.skill_id == skill_id)

    actions = query.all()
    resp = []
    for a in actions:
        r = SkillDevelopmentActionResponse.from_orm(a)
        if a.skill:
            r.skill_name = a.skill.name
        if a.person:
            r.person_name = getattr(a.person, "full_name", "Employee")
        resp.append(r)
    return resp


@router.post("/skill-development-actions", response_model=SkillDevelopmentActionResponse, status_code=http_status.HTTP_201_CREATED)
def create_skill_development_action(
    payload: SkillDevelopmentActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        if payload.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot assign development actions for other employees")

    sk = db.query(Skill).filter(Skill.id == payload.skill_id).first()
    if not sk:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Skill not found")

    act = SkillDevelopmentAction(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        skill_id=payload.skill_id,
        skill_gap_reference=payload.skill_gap_reference,
        action_type=payload.action_type,
        course_id=payload.course_id,
        mentoring_program_id=payload.mentoring_program_id,
        target_level_id=payload.target_level_id,
        due_date=payload.due_date,
        status="PLANNED",
    )
    db.add(act)
    db.commit()
    db.refresh(act)

    r = SkillDevelopmentActionResponse.from_orm(act)
    r.skill_name = sk.name
    return r


@router.get("/skill-evidence", response_model=List[SkillEvidenceResponse])
def list_skill_evidence(
    request: Request,
    person_id: Optional[str] = Query(None),
    skill_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        person_id = current_user.person_id or current_user.id

    query = db.query(SkillEvidence).filter(SkillEvidence.tenant_id == tenant_id)
    if person_id:
        query = query.filter(SkillEvidence.person_id == person_id)
    if skill_id:
        query = query.filter(SkillEvidence.skill_id == skill_id)

    evidences = query.all()
    resp = []
    for ev in evidences:
        r = SkillEvidenceResponse.from_orm(ev)
        if ev.skill:
            r.skill_name = ev.skill.name
        if ev.person:
            r.person_name = getattr(ev.person, "full_name", "Employee")
        resp.append(r)
    return resp


@router.post("/skill-evidence", response_model=SkillEvidenceResponse, status_code=http_status.HTTP_201_CREATED)
def record_skill_evidence(
    payload: SkillEvidenceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not _can_manage_learning(current_user, db):
        if payload.person_id != (current_user.person_id or current_user.id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot record skill evidence for other employees")

    sk = db.query(Skill).filter(Skill.id == payload.skill_id).first()
    if not sk:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Skill not found")

    ev = SkillEvidence(
        tenant_id=tenant_id,
        person_id=payload.person_id,
        skill_id=payload.skill_id,
        evidence_type=payload.evidence_type,
        source_reference=payload.source_reference,
        evidence_date=payload.evidence_date,
        verified=False,
        notes=payload.notes,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    r = SkillEvidenceResponse.from_orm(ev)
    r.skill_name = sk.name
    return r


@router.post("/skill-evidence/{evidence_id}/verify", response_model=SkillEvidenceResponse)
def verify_skill_evidence(
    evidence_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_learning(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Learning management permission required to verify skill evidence")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    ev = db.query(SkillEvidence).filter(
        SkillEvidence.id == evidence_id,
        SkillEvidence.tenant_id == tenant_id,
    ).first()
    if not ev:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Skill evidence not found")

    ev.verified = True
    ev.verified_by = current_user.id
    ev.verified_at = datetime.utcnow()

    # Controlled skill progression: update or create EmployeeSkill record
    emp_skill = db.query(EmployeeSkill).filter(
        EmployeeSkill.tenant_id == tenant_id,
        EmployeeSkill.person_id == ev.person_id,
        EmployeeSkill.skill_id == ev.skill_id,
    ).first()

    if emp_skill:
        emp_skill.verified = True
        emp_skill.verified_by = current_user.id
        emp_skill.proficiency = min(5.0, emp_skill.proficiency + 0.5)
    else:
        emp_skill = EmployeeSkill(
            tenant_id=tenant_id,
            person_id=ev.person_id,
            skill_id=ev.skill_id,
            proficiency=2.0,
            verified=True,
            verified_by=current_user.id,
        )
        db.add(emp_skill)

    db.commit()
    db.refresh(ev)

    r = SkillEvidenceResponse.from_orm(ev)
    if ev.skill:
        r.skill_name = ev.skill.name
    return r
