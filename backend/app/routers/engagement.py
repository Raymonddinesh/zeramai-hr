"""
engagement.py - Module 19 API Router: Employee Engagement, Surveys, Recognition & Organizational Culture
Zeramai Enterprise HRMS
"""
import uuid
import secrets
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import User, UserRole, Person, Tenant, AuditResult, Department, Engagement
from app.models_engagement import (
    SurveyTemplate,
    SurveyQuestion,
    SurveyCampaign,
    SurveyRecipient,
    SurveyResponse,
    SurveyAnswer,
    EmployeeFeedback,
    EmployeeSuggestion,
    EngagementActionPlan,
    EngagementActionItem,
    RecognitionProgram,
    RecognitionAward,
    AwardDefinition,
    AwardNomination,
    CultureInitiative,
    CultureParticipation,
    SurveyType,
    SurveyTemplateStatus,
    SurveyQuestionType,
    SurveyCampaignStatus,
    SurveyAudienceType,
    SurveyVisibilityType,
    ParticipationStatus,
    FeedbackCategory,
    FeedbackVisibility,
    FeedbackStatus,
    SuggestionStatus,
    ActionPlanStatus,
    RecognitionType,
    AwardNominationStatus,
    CultureInitiativeCategory,
)
from app.schemas_engagement import (
    SurveyQuestionCreate,
    SurveyQuestionResponse,
    SurveyTemplateCreate,
    SurveyTemplateUpdate,
    SurveyTemplateResponse,
    SurveyCampaignCreate,
    SurveyCampaignUpdate,
    SurveyCampaignResponse,
    SurveyRecipientResponse,
    SurveySubmitRequest,
    SurveyResponseItem,
    CampaignAnalyticsResponse,
    EmployeeFeedbackCreate,
    EmployeeFeedbackUpdate,
    EmployeeFeedbackResponse,
    EmployeeSuggestionCreate,
    EmployeeSuggestionUpdate,
    EmployeeSuggestionResponse,
    EngagementActionPlanCreate,
    EngagementActionPlanUpdate,
    EngagementActionPlanResponse,
    EngagementActionItemCreate,
    EngagementActionItemUpdate,
    EngagementActionItemResponse,
    RecognitionProgramCreate,
    RecognitionProgramResponse,
    RecognitionAwardCreate,
    RecognitionAwardResponse,
    AwardDefinitionCreate,
    AwardDefinitionResponse,
    AwardNominationCreate,
    AwardNominationReview,
    AwardNominationResponse,
    CultureInitiativeCreate,
    CultureInitiativeResponse,
    CultureParticipationCreate,
    CultureParticipationResponse,
    EmployeeExperienceDashboard,
    ManagerTeamEngagementDashboard,
    EngagementHRDashboard,
)
from app.services.engagement_service import (
    distribute_campaign_invitations,
    submit_survey_response,
    calculate_campaign_analytics,
    get_manager_team_engagement_data,
    validate_recognition_award,
    register_culture_participation,
    get_engagement_hr_dashboard_data,
    get_employee_experience_dashboard_data,
)

router = APIRouter(prefix="/api/v3/engagement", tags=["Module 19 - Employee Engagement, Surveys & Culture"])


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


def _format_person_name(person: Optional[Person]) -> Optional[str]:
    if not person:
        return None
    return person.full_name or person.email or "Employee"


def _can_read_engagement(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER, UserRole.EMPLOYEE, UserRole.FINANCE)
        or has_permission(user, "engagement:read", db)
        or has_permission(user, "engagement.read", db)
    )


def _can_manage_engagement(user: User, db: Session) -> bool:
    return (
        user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
        or has_permission(user, "engagement:manage", db)
        or has_permission(user, "engagement.manage", db)
    )


def _can_manage_surveys(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or has_permission(user, "engagement:surveys:manage", db)
        or has_permission(user, "engagement.surveys.manage", db)
    )


def _can_read_analytics(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(user, "engagement:analytics:read", db)
        or has_permission(user, "engagement.analytics.read", db)
    )


def _can_manage_action_plans(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(user, "engagement:action_plans:manage", db)
        or has_permission(user, "engagement.action_plans.manage", db)
    )


def _can_manage_feedback(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or has_permission(user, "engagement:feedback:manage", db)
        or has_permission(user, "engagement.feedback.manage", db)
    )


def _can_manage_suggestions(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or has_permission(user, "engagement:suggestions:manage", db)
        or has_permission(user, "engagement.suggestions.manage", db)
    )


def _can_manage_recognition(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or has_permission(user, "engagement:recognition:manage", db)
        or has_permission(user, "engagement.recognition.manage", db)
    )


def _can_manage_awards(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or has_permission(user, "engagement:awards:manage", db)
        or has_permission(user, "engagement.awards.manage", db)
    )


def _can_manage_culture(user: User, db: Session) -> bool:
    return (
        _can_manage_engagement(user, db)
        or has_permission(user, "engagement:culture:manage", db)
        or has_permission(user, "engagement.culture.manage", db)
    )


# ---------------------------------------------------------------------------
# 1. Dashboards
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=EngagementHRDashboard)
def get_hr_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_analytics(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement analytics read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return get_engagement_hr_dashboard_data(tenant_id, db)


@router.get("/team-dashboard", response_model=ManagerTeamEngagementDashboard)
def get_team_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        current_user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER)
        or has_permission(current_user, "engagement:manage", db)
        or has_permission(current_user, "engagement.manage", db)
    ):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Manager or HR permission required for team engagement dashboard")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    manager_person_id = current_user.person_id or current_user.id
    return get_manager_team_engagement_data(manager_person_id, tenant_id, db)


@router.get("/my-experience", response_model=EmployeeExperienceDashboard)
def get_my_experience(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id
    return get_employee_experience_dashboard_data(person_id, tenant_id, db)


# ---------------------------------------------------------------------------
# 2. Survey Templates & Question Bank
# ---------------------------------------------------------------------------

@router.get("/templates", response_model=List[SurveyTemplateResponse])
def list_templates(
    request: Request,
    survey_type: Optional[SurveyType] = None,
    template_status: Optional[SurveyTemplateStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(SurveyTemplate).filter(SurveyTemplate.tenant_id == tenant_id)
    if survey_type:
        query = query.filter(SurveyTemplate.survey_type == survey_type)
    if template_status:
        query = query.filter(SurveyTemplate.status == template_status)
    return query.all()


@router.post("/templates", response_model=SurveyTemplateResponse, status_code=http_status.HTTP_201_CREATED)
def create_template(
    payload: SurveyTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    tmpl = SurveyTemplate(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        survey_type=payload.survey_type,
        status=SurveyTemplateStatus.DRAFT,
        estimated_minutes=payload.estimated_minutes,
        anonymous_by_default=payload.anonymous_by_default,
        created_by=current_user.id,
    )
    db.add(tmpl)
    db.flush()

    for idx, q_data in enumerate(payload.questions or []):
        q = SurveyQuestion(
            tenant_id=tenant_id,
            template_id=tmpl.id,
            question_type=q_data.question_type,
            question_text=q_data.question_text,
            category=q_data.category,
            sequence=q_data.sequence or (idx + 1),
            required=q_data.required,
            anonymous=q_data.anonymous,
            scale_min=q_data.scale_min,
            scale_max=q_data.scale_max,
            options_json=q_data.options_json,
        )
        db.add(q)

    db.commit()
    db.refresh(tmpl)
    log_audit(db, user=current_user, action="CREATE_SURVEY_TEMPLATE", entity="SurveyTemplate", entity_id=tmpl.id, result=AuditResult.SUCCESS, request=request)
    return tmpl


@router.get("/templates/{template_id}", response_model=SurveyTemplateResponse)
def get_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(SurveyTemplate).filter(
        SurveyTemplate.id == template_id,
        SurveyTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")
    return tmpl


@router.put("/templates/{template_id}", response_model=SurveyTemplateResponse)
def update_template(
    template_id: str,
    payload: SurveyTemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(SurveyTemplate).filter(
        SurveyTemplate.id == template_id,
        SurveyTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(tmpl, k, v)
    tmpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tmpl)
    log_audit(db, user=current_user, action="UPDATE_SURVEY_TEMPLATE", entity="SurveyTemplate", entity_id=tmpl.id, result=AuditResult.SUCCESS, request=request)
    return tmpl


@router.delete("/templates/{template_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(SurveyTemplate).filter(
        SurveyTemplate.id == template_id,
        SurveyTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")
    db.delete(tmpl)
    db.commit()
    log_audit(db, user=current_user, action="DELETE_SURVEY_TEMPLATE", entity="SurveyTemplate", entity_id=template_id, result=AuditResult.SUCCESS, request=request)
    return None


@router.post("/templates/{template_id}/publish", response_model=SurveyTemplateResponse)
def publish_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(SurveyTemplate).filter(
        SurveyTemplate.id == template_id,
        SurveyTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")

    tmpl.status = SurveyTemplateStatus.PUBLISHED
    tmpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tmpl)
    log_audit(db, user=current_user, action="PUBLISH_SURVEY_TEMPLATE", entity="SurveyTemplate", entity_id=tmpl.id, result=AuditResult.SUCCESS, request=request)
    return tmpl


# ---------------------------------------------------------------------------
# 3. Question Bank Endpoints
# ---------------------------------------------------------------------------

@router.get("/questions", response_model=List[SurveyQuestionResponse])
def list_questions(
    request: Request,
    template_id: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(SurveyQuestion).filter(SurveyQuestion.tenant_id == tenant_id)
    if template_id:
        query = query.filter(SurveyQuestion.template_id == template_id)
    if category:
        query = query.filter(SurveyQuestion.category == category)
    return query.order_by(SurveyQuestion.sequence).all()


@router.post("/questions", response_model=SurveyQuestionResponse, status_code=http_status.HTTP_201_CREATED)
def create_question(
    payload: SurveyQuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    if not payload.template_id:
        raise HTTPException(status_code=400, detail="template_id is required")

    tmpl = db.query(SurveyTemplate).filter(
        SurveyTemplate.id == payload.template_id,
        SurveyTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Parent survey template not found in tenant")

    q = SurveyQuestion(
        tenant_id=tenant_id,
        template_id=payload.template_id,
        question_type=payload.question_type,
        question_text=payload.question_text,
        category=payload.category,
        sequence=payload.sequence,
        required=payload.required,
        anonymous=payload.anonymous,
        scale_min=payload.scale_min,
        scale_max=payload.scale_max,
        options_json=payload.options_json,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.get("/questions/{question_id}", response_model=SurveyQuestionResponse)
def get_question(
    question_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(SurveyQuestion).filter(
        SurveyQuestion.id == question_id,
        SurveyQuestion.tenant_id == tenant_id,
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Survey question not found")
    return q


@router.put("/questions/{question_id}", response_model=SurveyQuestionResponse)
def update_question(
    question_id: str,
    payload: SurveyQuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(SurveyQuestion).filter(
        SurveyQuestion.id == question_id,
        SurveyQuestion.tenant_id == tenant_id,
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Survey question not found")

    q.question_type = payload.question_type
    q.question_text = payload.question_text
    q.category = payload.category
    q.sequence = payload.sequence
    q.required = payload.required
    q.anonymous = payload.anonymous
    q.scale_min = payload.scale_min
    q.scale_max = payload.scale_max
    q.options_json = payload.options_json
    q.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(q)
    return q


@router.delete("/questions/{question_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(SurveyQuestion).filter(
        SurveyQuestion.id == question_id,
        SurveyQuestion.tenant_id == tenant_id,
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Survey question not found")
    db.delete(q)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# 4. Survey Campaigns
# ---------------------------------------------------------------------------

@router.get("/campaigns", response_model=List[SurveyCampaignResponse])
def list_campaigns(
    request: Request,
    campaign_status: Optional[SurveyCampaignStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(SurveyCampaign).filter(SurveyCampaign.tenant_id == tenant_id)
    if campaign_status:
        query = query.filter(SurveyCampaign.status == campaign_status)
    campaigns = query.all()

    results: List[SurveyCampaignResponse] = []
    for c in campaigns:
        r_cnt = db.query(SurveyRecipient).filter(SurveyRecipient.campaign_id == c.id).count()
        resp_cnt = db.query(SurveyResponse).filter(SurveyResponse.campaign_id == c.id).count()
        results.append(
            SurveyCampaignResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                template_id=c.template_id,
                name=c.name,
                description=c.description,
                audience_type=c.audience_type,
                target_department_id=c.target_department_id,
                target_organization_unit_id=c.target_organization_unit_id,
                start_at=c.start_at,
                end_at=c.end_at,
                anonymous=c.anonymous,
                minimum_anonymity_threshold=c.minimum_anonymity_threshold,
                visibility_type=c.visibility_type,
                status=c.status,
                created_by=c.created_by,
                created_at=c.created_at,
                updated_at=c.updated_at,
                template_name=c.template.name if c.template else None,
                recipient_count=r_cnt,
                response_count=resp_cnt,
            )
        )
    return results


@router.post("/campaigns", response_model=SurveyCampaignResponse, status_code=http_status.HTTP_201_CREATED)
def create_campaign(
    payload: SurveyCampaignCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    tmpl = db.query(SurveyTemplate).filter(
        SurveyTemplate.id == payload.template_id,
        SurveyTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found in tenant")

    campaign = SurveyCampaign(
        tenant_id=tenant_id,
        template_id=payload.template_id,
        name=payload.name,
        description=payload.description,
        audience_type=payload.audience_type,
        target_department_id=payload.target_department_id,
        target_organization_unit_id=payload.target_organization_unit_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        anonymous=payload.anonymous,
        minimum_anonymity_threshold=payload.minimum_anonymity_threshold,
        visibility_type=payload.visibility_type,
        status=SurveyCampaignStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    log_audit(db, user=current_user, action="CREATE_SURVEY_CAMPAIGN", entity="SurveyCampaign", entity_id=campaign.id, result=AuditResult.SUCCESS, request=request)
    return SurveyCampaignResponse(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        template_id=campaign.template_id,
        name=campaign.name,
        description=campaign.description,
        audience_type=campaign.audience_type,
        target_department_id=campaign.target_department_id,
        target_organization_unit_id=campaign.target_organization_unit_id,
        start_at=campaign.start_at,
        end_at=campaign.end_at,
        anonymous=campaign.anonymous,
        minimum_anonymity_threshold=campaign.minimum_anonymity_threshold,
        visibility_type=campaign.visibility_type,
        status=campaign.status,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        template_name=tmpl.name,
        recipient_count=0,
        response_count=0,
    )


@router.get("/campaigns/{campaign_id}", response_model=SurveyCampaignResponse)
def get_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    r_cnt = db.query(SurveyRecipient).filter(SurveyRecipient.campaign_id == c.id).count()
    resp_cnt = db.query(SurveyResponse).filter(SurveyResponse.campaign_id == c.id).count()
    return SurveyCampaignResponse(
        id=c.id,
        tenant_id=c.tenant_id,
        template_id=c.template_id,
        name=c.name,
        description=c.description,
        audience_type=c.audience_type,
        target_department_id=c.target_department_id,
        target_organization_unit_id=c.target_organization_unit_id,
        start_at=c.start_at,
        end_at=c.end_at,
        anonymous=c.anonymous,
        minimum_anonymity_threshold=c.minimum_anonymity_threshold,
        visibility_type=c.visibility_type,
        status=c.status,
        created_by=c.created_by,
        created_at=c.created_at,
        updated_at=c.updated_at,
        template_name=c.template.name if c.template else None,
        recipient_count=r_cnt,
        response_count=resp_cnt,
    )


@router.put("/campaigns/{campaign_id}", response_model=SurveyCampaignResponse)
def update_campaign(
    campaign_id: str,
    payload: SurveyCampaignUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    log_audit(db, user=current_user, action="UPDATE_SURVEY_CAMPAIGN", entity="SurveyCampaign", entity_id=c.id, result=AuditResult.SUCCESS, request=request)

    r_cnt = db.query(SurveyRecipient).filter(SurveyRecipient.campaign_id == c.id).count()
    resp_cnt = db.query(SurveyResponse).filter(SurveyResponse.campaign_id == c.id).count()
    return SurveyCampaignResponse(
        id=c.id,
        tenant_id=c.tenant_id,
        template_id=c.template_id,
        name=c.name,
        description=c.description,
        audience_type=c.audience_type,
        target_department_id=c.target_department_id,
        target_organization_unit_id=c.target_organization_unit_id,
        start_at=c.start_at,
        end_at=c.end_at,
        anonymous=c.anonymous,
        minimum_anonymity_threshold=c.minimum_anonymity_threshold,
        visibility_type=c.visibility_type,
        status=c.status,
        created_by=c.created_by,
        created_at=c.created_at,
        updated_at=c.updated_at,
        template_name=c.template.name if c.template else None,
        recipient_count=r_cnt,
        response_count=resp_cnt,
    )


@router.post("/campaigns/{campaign_id}/publish", response_model=SurveyCampaignResponse)
def publish_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    c.status = SurveyCampaignStatus.ACTIVE
    c.updated_at = datetime.utcnow()
    # Distribute invitations to audience
    invited_cnt = distribute_campaign_invitations(c, db)

    db.commit()
    db.refresh(c)
    log_audit(db, user=current_user, action="PUBLISH_SURVEY_CAMPAIGN", entity="SurveyCampaign", entity_id=c.id, result=AuditResult.SUCCESS, request=request, metadata={"invited_count": invited_cnt})

    r_cnt = db.query(SurveyRecipient).filter(SurveyRecipient.campaign_id == c.id).count()
    resp_cnt = db.query(SurveyResponse).filter(SurveyResponse.campaign_id == c.id).count()
    return SurveyCampaignResponse(
        id=c.id,
        tenant_id=c.tenant_id,
        template_id=c.template_id,
        name=c.name,
        description=c.description,
        audience_type=c.audience_type,
        target_department_id=c.target_department_id,
        target_organization_unit_id=c.target_organization_unit_id,
        start_at=c.start_at,
        end_at=c.end_at,
        anonymous=c.anonymous,
        minimum_anonymity_threshold=c.minimum_anonymity_threshold,
        visibility_type=c.visibility_type,
        status=c.status,
        created_by=c.created_by,
        created_at=c.created_at,
        updated_at=c.updated_at,
        template_name=c.template.name if c.template else None,
        recipient_count=r_cnt,
        response_count=resp_cnt,
    )


@router.post("/campaigns/{campaign_id}/close", response_model=SurveyCampaignResponse)
def close_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    c.status = SurveyCampaignStatus.CLOSED
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    log_audit(db, user=current_user, action="CLOSE_SURVEY_CAMPAIGN", entity="SurveyCampaign", entity_id=c.id, result=AuditResult.SUCCESS, request=request)

    r_cnt = db.query(SurveyRecipient).filter(SurveyRecipient.campaign_id == c.id).count()
    resp_cnt = db.query(SurveyResponse).filter(SurveyResponse.campaign_id == c.id).count()
    return SurveyCampaignResponse(
        id=c.id,
        tenant_id=c.tenant_id,
        template_id=c.template_id,
        name=c.name,
        description=c.description,
        audience_type=c.audience_type,
        target_department_id=c.target_department_id,
        target_organization_unit_id=c.target_organization_unit_id,
        start_at=c.start_at,
        end_at=c.end_at,
        anonymous=c.anonymous,
        minimum_anonymity_threshold=c.minimum_anonymity_threshold,
        visibility_type=c.visibility_type,
        status=c.status,
        created_by=c.created_by,
        created_at=c.created_at,
        updated_at=c.updated_at,
        template_name=c.template.name if c.template else None,
        recipient_count=r_cnt,
        response_count=resp_cnt,
    )


@router.get("/campaigns/{campaign_id}/results", response_model=CampaignAnalyticsResponse)
def get_campaign_results(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_analytics(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement analytics read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return calculate_campaign_analytics(campaign_id, tenant_id, db)


@router.get("/campaigns/{campaign_id}/participation", response_model=List[SurveyRecipientResponse])
def get_campaign_recipients(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_surveys(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Survey management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    c = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    recipients = db.query(SurveyRecipient).filter(
        SurveyRecipient.campaign_id == campaign_id,
        SurveyRecipient.tenant_id == tenant_id,
    ).all()

    results: List[SurveyRecipientResponse] = []
    for r in recipients:
        p_name = _format_person_name(r.person)
        results.append(
            SurveyRecipientResponse(
                id=r.id,
                tenant_id=r.tenant_id,
                campaign_id=r.campaign_id,
                person_id=r.person_id,
                invitation_sent_at=r.invitation_sent_at,
                started_at=r.started_at,
                completed_at=r.completed_at,
                participation_status=r.participation_status,
                created_at=r.created_at,
                person_name=p_name,
            )
        )
    return results


# ---------------------------------------------------------------------------
# 5. Surveys & Response Submission
# ---------------------------------------------------------------------------

@router.get("/surveys/available", response_model=List[SurveyCampaignResponse])
def get_available_surveys(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id
    now = datetime.utcnow()

    # Active campaigns
    active_campaigns = db.query(SurveyCampaign).filter(
        SurveyCampaign.tenant_id == tenant_id,
        SurveyCampaign.status == SurveyCampaignStatus.ACTIVE,
        SurveyCampaign.start_at <= now,
        SurveyCampaign.end_at >= now,
    ).all()

    # Exclude already completed
    completed_campaign_ids = set(
        r[0] for r in db.query(SurveyRecipient.campaign_id).filter(
            SurveyRecipient.person_id == person_id,
            SurveyRecipient.participation_status == ParticipationStatus.COMPLETED,
        ).all()
    )

    results: List[SurveyCampaignResponse] = []
    for c in active_campaigns:
        if c.id not in completed_campaign_ids:
            results.append(
                SurveyCampaignResponse(
                    id=c.id,
                    tenant_id=c.tenant_id,
                    template_id=c.template_id,
                    name=c.name,
                    description=c.description,
                    audience_type=c.audience_type,
                    target_department_id=c.target_department_id,
                    target_organization_unit_id=c.target_organization_unit_id,
                    start_at=c.start_at,
                    end_at=c.end_at,
                    anonymous=c.anonymous,
                    minimum_anonymity_threshold=c.minimum_anonymity_threshold,
                    visibility_type=c.visibility_type,
                    status=c.status,
                    created_by=c.created_by,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                    template_name=c.template.name if c.template else None,
                    recipient_count=0,
                    response_count=0,
                )
            )
    return results


@router.get("/surveys/{campaign_id}/respond", response_model=SurveyTemplateResponse)
def get_survey_questions_for_taking(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    c = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    tmpl = c.template
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")

    return tmpl


@router.post("/surveys/{campaign_id}/submit", response_model=SurveyResponseItem, status_code=http_status.HTTP_201_CREATED)
def submit_survey(
    campaign_id: str,
    payload: SurveySubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id

    answers_input = [a.dict() for a in payload.answers]
    response = submit_survey_response(
        campaign_id=campaign_id,
        person_id=person_id,
        answers_input=answers_input,
        completion_time_seconds=payload.completion_time_seconds,
        db=db,
        tenant_id=tenant_id,
    )

    # Note: For anonymous campaigns, response.recipient_id is None!
    log_audit(db, user=current_user, action="SUBMIT_SURVEY_RESPONSE", entity="SurveyResponse", entity_id=response.id, result=AuditResult.SUCCESS, request=request)
    return response


# ---------------------------------------------------------------------------
# 6. Employee Feedback & Suggestion Box
# ---------------------------------------------------------------------------

@router.get("/feedback", response_model=List[EmployeeFeedbackResponse])
def list_feedback(
    request: Request,
    category: Optional[FeedbackCategory] = None,
    feedback_status: Optional[FeedbackStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    query = db.query(EmployeeFeedback).filter(EmployeeFeedback.tenant_id == tenant_id)
    # If not HR/Admin, only show feedback submitted by the user
    if not _can_manage_feedback(current_user, db):
        person_id = current_user.person_id or current_user.id
        query = query.filter(EmployeeFeedback.person_id == person_id)

    if category:
        query = query.filter(EmployeeFeedback.category == category)
    if feedback_status:
        query = query.filter(EmployeeFeedback.status == feedback_status)

    feedbacks = query.order_by(EmployeeFeedback.submitted_at.desc()).all()
    results: List[EmployeeFeedbackResponse] = []
    for f in feedbacks:
        p_name = _format_person_name(f.person)
        results.append(
            EmployeeFeedbackResponse(
                id=f.id,
                tenant_id=f.tenant_id,
                person_id=f.person_id,
                category=f.category,
                subject=f.subject,
                message=f.message,
                visibility=f.visibility,
                status=f.status,
                is_grievance_referral=f.is_grievance_referral,
                er_case_id=f.er_case_id,
                grievance_case_id=f.grievance_case_id,
                submitted_at=f.submitted_at,
                resolved_at=f.resolved_at,
                admin_notes=f.admin_notes if _can_manage_feedback(current_user, db) else None,
                created_at=f.created_at,
                updated_at=f.updated_at,
                person_name=p_name,
            )
        )
    return results


@router.post("/feedback", response_model=EmployeeFeedbackResponse, status_code=http_status.HTTP_201_CREATED)
def submit_feedback(
    payload: EmployeeFeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id

    fb = EmployeeFeedback(
        tenant_id=tenant_id,
        person_id=person_id,
        category=payload.category,
        subject=payload.subject,
        message=payload.message,
        visibility=payload.visibility,
        status=FeedbackStatus.SUBMITTED,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    log_audit(db, user=current_user, action="SUBMIT_FEEDBACK", entity="EmployeeFeedback", entity_id=fb.id, result=AuditResult.SUCCESS, request=request)
    return EmployeeFeedbackResponse(
        id=fb.id,
        tenant_id=fb.tenant_id,
        person_id=fb.person_id,
        category=fb.category,
        subject=fb.subject,
        message=fb.message,
        visibility=fb.visibility,
        status=fb.status,
        is_grievance_referral=fb.is_grievance_referral,
        er_case_id=fb.er_case_id,
        grievance_case_id=fb.grievance_case_id,
        submitted_at=fb.submitted_at,
        resolved_at=fb.resolved_at,
        admin_notes=fb.admin_notes,
        created_at=fb.created_at,
        updated_at=fb.updated_at,
        person_name=None,
    )


@router.get("/feedback/{feedback_id}", response_model=EmployeeFeedbackResponse)
def get_feedback(
    feedback_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    fb = db.query(EmployeeFeedback).filter(
        EmployeeFeedback.id == feedback_id,
        EmployeeFeedback.tenant_id == tenant_id,
    ).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")

    person_id = current_user.person_id or current_user.id
    if not _can_manage_feedback(current_user, db) and fb.person_id != person_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied to this feedback entry")

    return EmployeeFeedbackResponse(
        id=fb.id,
        tenant_id=fb.tenant_id,
        person_id=fb.person_id,
        category=fb.category,
        subject=fb.subject,
        message=fb.message,
        visibility=fb.visibility,
        status=fb.status,
        is_grievance_referral=fb.is_grievance_referral,
        er_case_id=fb.er_case_id,
        grievance_case_id=fb.grievance_case_id,
        submitted_at=fb.submitted_at,
        resolved_at=fb.resolved_at,
        admin_notes=fb.admin_notes if _can_manage_feedback(current_user, db) else None,
        created_at=fb.created_at,
        updated_at=fb.updated_at,
        person_name=_format_person_name(fb.person),
    )


@router.put("/feedback/{feedback_id}", response_model=EmployeeFeedbackResponse)
def update_feedback(
    feedback_id: str,
    payload: EmployeeFeedbackUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_feedback(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Feedback management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    fb = db.query(EmployeeFeedback).filter(
        EmployeeFeedback.id == feedback_id,
        EmployeeFeedback.tenant_id == tenant_id,
    ).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(fb, k, v)
    if payload.status in [FeedbackStatus.RESOLVED, FeedbackStatus.CLOSED] and not fb.resolved_at:
        fb.resolved_at = datetime.utcnow()
    fb.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(fb)
    log_audit(db, user=current_user, action="UPDATE_FEEDBACK", entity="EmployeeFeedback", entity_id=fb.id, result=AuditResult.SUCCESS, request=request)

    return EmployeeFeedbackResponse(
        id=fb.id,
        tenant_id=fb.tenant_id,
        person_id=fb.person_id,
        category=fb.category,
        subject=fb.subject,
        message=fb.message,
        visibility=fb.visibility,
        status=fb.status,
        is_grievance_referral=fb.is_grievance_referral,
        er_case_id=fb.er_case_id,
        grievance_case_id=fb.grievance_case_id,
        submitted_at=fb.submitted_at,
        resolved_at=fb.resolved_at,
        admin_notes=fb.admin_notes,
        created_at=fb.created_at,
        updated_at=fb.updated_at,
        person_name=_format_person_name(fb.person),
    )


@router.post("/feedback/{feedback_id}/refer-grievance", response_model=EmployeeFeedbackResponse)
def refer_feedback_to_grievance(
    feedback_id: str,
    request: Request,
    er_case_id: Optional[str] = Query(None),
    grievance_case_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_feedback(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Feedback management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    fb = db.query(EmployeeFeedback).filter(
        EmployeeFeedback.id == feedback_id,
        EmployeeFeedback.tenant_id == tenant_id,
    ).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")

    fb.is_grievance_referral = True
    fb.er_case_id = er_case_id
    fb.grievance_case_id = grievance_case_id
    fb.status = FeedbackStatus.ACTIONED
    fb.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(fb)
    log_audit(db, user=current_user, action="REFER_FEEDBACK_GRIEVANCE", entity="EmployeeFeedback", entity_id=fb.id, result=AuditResult.SUCCESS, request=request)

    return EmployeeFeedbackResponse(
        id=fb.id,
        tenant_id=fb.tenant_id,
        person_id=fb.person_id,
        category=fb.category,
        subject=fb.subject,
        message=fb.message,
        visibility=fb.visibility,
        status=fb.status,
        is_grievance_referral=fb.is_grievance_referral,
        er_case_id=fb.er_case_id,
        grievance_case_id=fb.grievance_case_id,
        submitted_at=fb.submitted_at,
        resolved_at=fb.resolved_at,
        admin_notes=fb.admin_notes,
        created_at=fb.created_at,
        updated_at=fb.updated_at,
        person_name=_format_person_name(fb.person),
    )


# ---------------------------------------------------------------------------
# 7. Suggestions Box
# ---------------------------------------------------------------------------

@router.get("/suggestions", response_model=List[EmployeeSuggestionResponse])
def list_suggestions(
    request: Request,
    suggestion_status: Optional[SuggestionStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(EmployeeSuggestion).filter(EmployeeSuggestion.tenant_id == tenant_id)
    if suggestion_status:
        query = query.filter(EmployeeSuggestion.status == suggestion_status)

    suggestions = query.order_by(EmployeeSuggestion.created_at.desc()).all()
    results: List[EmployeeSuggestionResponse] = []
    for s in suggestions:
        # If anonymous, mask person_id and name completely!
        p_name = None
        p_id = s.person_id
        if s.anonymous:
            p_id = None
            p_name = "Anonymous Employee"
        else:
            p_name = _format_person_name(s.person)

        results.append(
            EmployeeSuggestionResponse(
                id=s.id,
                tenant_id=s.tenant_id,
                person_id=p_id,
                category=s.category,
                title=s.title,
                description=s.description,
                anonymous=s.anonymous,
                status=s.status,
                submitted_at=s.submitted_at,
                reviewed_at=s.reviewed_at,
                reviewed_by=s.reviewed_by,
                admin_notes=s.admin_notes if _can_manage_suggestions(current_user, db) else None,
                votes_count=s.votes_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
                person_name=p_name,
            )
        )
    return results


@router.post("/suggestions", response_model=EmployeeSuggestionResponse, status_code=http_status.HTTP_201_CREATED)
def submit_suggestion(
    payload: EmployeeSuggestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    # If anonymous is True, store person_id as None or detach
    person_id = None if payload.anonymous else (current_user.person_id or current_user.id)

    sugg = EmployeeSuggestion(
        tenant_id=tenant_id,
        person_id=person_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        anonymous=payload.anonymous,
        status=SuggestionStatus.SUBMITTED,
    )
    db.add(sugg)
    db.commit()
    db.refresh(sugg)

    log_audit(db, user=current_user, action="SUBMIT_SUGGESTION", entity="EmployeeSuggestion", entity_id=sugg.id, result=AuditResult.SUCCESS, request=request)
    return EmployeeSuggestionResponse(
        id=sugg.id,
        tenant_id=sugg.tenant_id,
        person_id=None if payload.anonymous else person_id,
        category=sugg.category,
        title=sugg.title,
        description=sugg.description,
        anonymous=sugg.anonymous,
        status=sugg.status,
        submitted_at=sugg.submitted_at,
        reviewed_at=sugg.reviewed_at,
        reviewed_by=sugg.reviewed_by,
        admin_notes=sugg.admin_notes,
        votes_count=sugg.votes_count,
        created_at=sugg.created_at,
        updated_at=sugg.updated_at,
        person_name="Anonymous Employee" if payload.anonymous else None,
    )


@router.get("/suggestions/{suggestion_id}", response_model=EmployeeSuggestionResponse)
def get_suggestion(
    suggestion_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    s = db.query(EmployeeSuggestion).filter(
        EmployeeSuggestion.id == suggestion_id,
        EmployeeSuggestion.tenant_id == tenant_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    p_id = None if s.anonymous else s.person_id
    p_name = "Anonymous Employee" if s.anonymous else _format_person_name(s.person)

    return EmployeeSuggestionResponse(
        id=s.id,
        tenant_id=s.tenant_id,
        person_id=p_id,
        category=s.category,
        title=s.title,
        description=s.description,
        anonymous=s.anonymous,
        status=s.status,
        submitted_at=s.submitted_at,
        reviewed_at=s.reviewed_at,
        reviewed_by=s.reviewed_by,
        admin_notes=s.admin_notes if _can_manage_suggestions(current_user, db) else None,
        votes_count=s.votes_count,
        created_at=s.created_at,
        updated_at=s.updated_at,
        person_name=p_name,
    )


@router.put("/suggestions/{suggestion_id}", response_model=EmployeeSuggestionResponse)
def update_suggestion(
    suggestion_id: str,
    payload: EmployeeSuggestionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_suggestions(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Suggestion management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    s = db.query(EmployeeSuggestion).filter(
        EmployeeSuggestion.id == suggestion_id,
        EmployeeSuggestion.tenant_id == tenant_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if payload.status:
        s.status = payload.status
        s.reviewed_at = datetime.utcnow()
        s.reviewed_by = current_user.id
    if payload.admin_notes:
        s.admin_notes = payload.admin_notes
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    log_audit(db, user=current_user, action="UPDATE_SUGGESTION", entity="EmployeeSuggestion", entity_id=s.id, result=AuditResult.SUCCESS, request=request)

    p_id = None if s.anonymous else s.person_id
    p_name = "Anonymous Employee" if s.anonymous else _format_person_name(s.person)

    return EmployeeSuggestionResponse(
        id=s.id,
        tenant_id=s.tenant_id,
        person_id=p_id,
        category=s.category,
        title=s.title,
        description=s.description,
        anonymous=s.anonymous,
        status=s.status,
        submitted_at=s.submitted_at,
        reviewed_at=s.reviewed_at,
        reviewed_by=s.reviewed_by,
        admin_notes=s.admin_notes,
        votes_count=s.votes_count,
        created_at=s.created_at,
        updated_at=s.updated_at,
        person_name=p_name,
    )


@router.post("/suggestions/{suggestion_id}/vote", response_model=EmployeeSuggestionResponse)
def vote_suggestion(
    suggestion_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    s = db.query(EmployeeSuggestion).filter(
        EmployeeSuggestion.id == suggestion_id,
        EmployeeSuggestion.tenant_id == tenant_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    s.votes_count += 1
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)

    p_id = None if s.anonymous else s.person_id
    p_name = "Anonymous Employee" if s.anonymous else _format_person_name(s.person)
    return EmployeeSuggestionResponse(
        id=s.id,
        tenant_id=s.tenant_id,
        person_id=p_id,
        category=s.category,
        title=s.title,
        description=s.description,
        anonymous=s.anonymous,
        status=s.status,
        submitted_at=s.submitted_at,
        reviewed_at=s.reviewed_at,
        reviewed_by=s.reviewed_by,
        admin_notes=s.admin_notes if _can_manage_suggestions(current_user, db) else None,
        votes_count=s.votes_count,
        created_at=s.created_at,
        updated_at=s.updated_at,
        person_name=p_name,
    )


# ---------------------------------------------------------------------------
# 8. Engagement Action Plans
# ---------------------------------------------------------------------------

@router.get("/action-plans", response_model=List[EngagementActionPlanResponse])
def list_action_plans(
    request: Request,
    campaign_id: Optional[str] = None,
    plan_status: Optional[ActionPlanStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(EngagementActionPlan).filter(EngagementActionPlan.tenant_id == tenant_id)
    if campaign_id:
        query = query.filter(EngagementActionPlan.campaign_id == campaign_id)
    if plan_status:
        query = query.filter(EngagementActionPlan.status == plan_status)

    plans = query.all()
    results: List[EngagementActionPlanResponse] = []
    for p in plans:
        items_res = [
            EngagementActionItemResponse(
                id=it.id,
                tenant_id=it.tenant_id,
                action_plan_id=it.action_plan_id,
                action=it.action,
                owner_user_id=it.owner_user_id,
                due_date=it.due_date,
                status=it.status,
                completed_at=it.completed_at,
                notes=it.notes,
                created_at=it.created_at,
                updated_at=it.updated_at,
            ) for it in p.items
        ]
        results.append(
            EngagementActionPlanResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                campaign_id=p.campaign_id,
                organization_unit_id=p.organization_unit_id,
                department_id=p.department_id,
                title=p.title,
                description=p.description,
                owner_user_id=p.owner_user_id,
                due_date=p.due_date,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at,
                owner_name=p.owner.email if p.owner else None,
                items=items_res,
            )
        )
    return results


@router.post("/action-plans", response_model=EngagementActionPlanResponse, status_code=http_status.HTTP_201_CREATED)
def create_action_plan(
    payload: EngagementActionPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_action_plans(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Action plans management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    plan = EngagementActionPlan(
        tenant_id=tenant_id,
        campaign_id=payload.campaign_id,
        organization_unit_id=payload.organization_unit_id,
        department_id=payload.department_id,
        title=payload.title,
        description=payload.description,
        owner_user_id=payload.owner_user_id,
        due_date=payload.due_date,
        status=ActionPlanStatus.OPEN,
    )
    db.add(plan)
    db.flush()

    for item_data in payload.items or []:
        it = EngagementActionItem(
            tenant_id=tenant_id,
            action_plan_id=plan.id,
            action=item_data.action,
            owner_user_id=item_data.owner_user_id,
            due_date=item_data.due_date,
            status=ActionPlanStatus.OPEN,
            notes=item_data.notes,
        )
        db.add(it)

    db.commit()
    db.refresh(plan)
    log_audit(db, user=current_user, action="CREATE_ENGAGEMENT_ACTION_PLAN", entity="EngagementActionPlan", entity_id=plan.id, result=AuditResult.SUCCESS, request=request)

    items_res = [
        EngagementActionItemResponse(
            id=it.id,
            tenant_id=it.tenant_id,
            action_plan_id=it.action_plan_id,
            action=it.action,
            owner_user_id=it.owner_user_id,
            due_date=it.due_date,
            status=it.status,
            completed_at=it.completed_at,
            notes=it.notes,
            created_at=it.created_at,
            updated_at=it.updated_at,
        ) for it in plan.items
    ]
    return EngagementActionPlanResponse(
        id=plan.id,
        tenant_id=plan.tenant_id,
        campaign_id=plan.campaign_id,
        organization_unit_id=plan.organization_unit_id,
        department_id=plan.department_id,
        title=plan.title,
        description=plan.description,
        owner_user_id=plan.owner_user_id,
        due_date=plan.due_date,
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        owner_name=plan.owner.email if plan.owner else None,
        items=items_res,
    )


@router.get("/action-plans/{plan_id}", response_model=EngagementActionPlanResponse)
def get_action_plan(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    plan = db.query(EngagementActionPlan).filter(
        EngagementActionPlan.id == plan_id,
        EngagementActionPlan.tenant_id == tenant_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Action plan not found")

    items_res = [
        EngagementActionItemResponse(
            id=it.id,
            tenant_id=it.tenant_id,
            action_plan_id=it.action_plan_id,
            action=it.action,
            owner_user_id=it.owner_user_id,
            due_date=it.due_date,
            status=it.status,
            completed_at=it.completed_at,
            notes=it.notes,
            created_at=it.created_at,
            updated_at=it.updated_at,
        ) for it in plan.items
    ]
    return EngagementActionPlanResponse(
        id=plan.id,
        tenant_id=plan.tenant_id,
        campaign_id=plan.campaign_id,
        organization_unit_id=plan.organization_unit_id,
        department_id=plan.department_id,
        title=plan.title,
        description=plan.description,
        owner_user_id=plan.owner_user_id,
        due_date=plan.due_date,
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        owner_name=plan.owner.email if plan.owner else None,
        items=items_res,
    )


@router.put("/action-plans/{plan_id}", response_model=EngagementActionPlanResponse)
def update_action_plan(
    plan_id: str,
    payload: EngagementActionPlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_action_plans(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Action plans management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    plan = db.query(EngagementActionPlan).filter(
        EngagementActionPlan.id == plan_id,
        EngagementActionPlan.tenant_id == tenant_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Action plan not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(plan, k, v)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    log_audit(db, user=current_user, action="UPDATE_ENGAGEMENT_ACTION_PLAN", entity="EngagementActionPlan", entity_id=plan.id, result=AuditResult.SUCCESS, request=request)

    items_res = [
        EngagementActionItemResponse(
            id=it.id,
            tenant_id=it.tenant_id,
            action_plan_id=it.action_plan_id,
            action=it.action,
            owner_user_id=it.owner_user_id,
            due_date=it.due_date,
            status=it.status,
            completed_at=it.completed_at,
            notes=it.notes,
            created_at=it.created_at,
            updated_at=it.updated_at,
        ) for it in plan.items
    ]
    return EngagementActionPlanResponse(
        id=plan.id,
        tenant_id=plan.tenant_id,
        campaign_id=plan.campaign_id,
        organization_unit_id=plan.organization_unit_id,
        department_id=plan.department_id,
        title=plan.title,
        description=plan.description,
        owner_user_id=plan.owner_user_id,
        due_date=plan.due_date,
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        owner_name=plan.owner.email if plan.owner else None,
        items=items_res,
    )


@router.post("/action-plans/{plan_id}/items", response_model=EngagementActionItemResponse, status_code=http_status.HTTP_201_CREATED)
def add_action_item(
    plan_id: str,
    payload: EngagementActionItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_action_plans(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Action plans management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    plan = db.query(EngagementActionPlan).filter(
        EngagementActionPlan.id == plan_id,
        EngagementActionPlan.tenant_id == tenant_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Action plan not found")

    it = EngagementActionItem(
        tenant_id=tenant_id,
        action_plan_id=plan.id,
        action=payload.action,
        owner_user_id=payload.owner_user_id,
        due_date=payload.due_date,
        status=ActionPlanStatus.OPEN,
        notes=payload.notes,
    )
    db.add(it)
    db.commit()
    db.refresh(it)
    return EngagementActionItemResponse(
        id=it.id,
        tenant_id=it.tenant_id,
        action_plan_id=it.action_plan_id,
        action=it.action,
        owner_user_id=it.owner_user_id,
        due_date=it.due_date,
        status=it.status,
        completed_at=it.completed_at,
        notes=it.notes,
        created_at=it.created_at,
        updated_at=it.updated_at,
    )


@router.put("/action-plans/{plan_id}/items/{item_id}", response_model=EngagementActionItemResponse)
def update_action_item(
    plan_id: str,
    item_id: str,
    payload: EngagementActionItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_action_plans(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Action plans management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    it = db.query(EngagementActionItem).filter(
        EngagementActionItem.id == item_id,
        EngagementActionItem.action_plan_id == plan_id,
        EngagementActionItem.tenant_id == tenant_id,
    ).first()
    if not it:
        raise HTTPException(status_code=404, detail="Action item not found")

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(it, k, v)
    if payload.status == ActionPlanStatus.COMPLETED and not it.completed_at:
        it.completed_at = datetime.utcnow()
    it.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(it)

    return EngagementActionItemResponse(
        id=it.id,
        tenant_id=it.tenant_id,
        action_plan_id=it.action_plan_id,
        action=it.action,
        owner_user_id=it.owner_user_id,
        due_date=it.due_date,
        status=it.status,
        completed_at=it.completed_at,
        notes=it.notes,
        created_at=it.created_at,
        updated_at=it.updated_at,
    )


# ---------------------------------------------------------------------------
# 9. Recognition Programs & Awards
# ---------------------------------------------------------------------------

@router.get("/recognition/programs", response_model=List[RecognitionProgramResponse])
def list_recognition_programs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return db.query(RecognitionProgram).filter(RecognitionProgram.tenant_id == tenant_id).all()


@router.post("/recognition/programs", response_model=RecognitionProgramResponse, status_code=http_status.HTTP_201_CREATED)
def create_recognition_program(
    payload: RecognitionProgramCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_recognition(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Recognition management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    program = RecognitionProgram(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        recognition_type=payload.recognition_type,
        points_reward=payload.points_reward,
        status="ACTIVE",
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    log_audit(db, user=current_user, action="CREATE_RECOGNITION_PROGRAM", entity="RecognitionProgram", entity_id=program.id, result=AuditResult.SUCCESS, request=request)
    return program


@router.get("/recognition/programs/{program_id}", response_model=RecognitionProgramResponse)
def get_recognition_program(
    program_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    prog = db.query(RecognitionProgram).filter(
        RecognitionProgram.id == program_id,
        RecognitionProgram.tenant_id == tenant_id,
    ).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Recognition program not found")
    return prog


@router.get("/recognition/awards", response_model=List[RecognitionAwardResponse])
def list_recognition_awards(
    request: Request,
    program_id: Optional[str] = None,
    recipient_person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(RecognitionAward).filter(RecognitionAward.tenant_id == tenant_id)
    if program_id:
        query = query.filter(RecognitionAward.program_id == program_id)
    if recipient_person_id:
        query = query.filter(RecognitionAward.recipient_person_id == recipient_person_id)

    awards = query.order_by(RecognitionAward.created_at.desc()).all()
    results: List[RecognitionAwardResponse] = []
    for a in awards:
        g_name = _format_person_name(a.giver)
        r_name = _format_person_name(a.recipient)
        results.append(
            RecognitionAwardResponse(
                id=a.id,
                tenant_id=a.tenant_id,
                program_id=a.program_id,
                giver_person_id=a.giver_person_id,
                recipient_person_id=a.recipient_person_id,
                title=a.title,
                message=a.message,
                category=a.category,
                visibility=a.visibility,
                awarded_at=a.awarded_at,
                status=a.status,
                created_at=a.created_at,
                giver_name=g_name,
                recipient_name=r_name,
            )
        )
    return results


@router.post("/recognition/awards", response_model=RecognitionAwardResponse, status_code=http_status.HTTP_201_CREATED)
def create_recognition_award(
    payload: RecognitionAwardCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    giver_person_id = current_user.person_id or current_user.id

    # Enforce anti-self recognition and tenant isolation
    validate_recognition_award(giver_person_id, payload.recipient_person_id, tenant_id, db)

    prog = db.query(RecognitionProgram).filter(
        RecognitionProgram.id == payload.program_id,
        RecognitionProgram.tenant_id == tenant_id,
    ).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Recognition program not found in tenant")

    award = RecognitionAward(
        tenant_id=tenant_id,
        program_id=payload.program_id,
        giver_person_id=giver_person_id,
        recipient_person_id=payload.recipient_person_id,
        title=payload.title,
        message=payload.message,
        category=payload.category,
        visibility=payload.visibility,
        awarded_at=datetime.utcnow(),
        status="PUBLISHED",
    )
    db.add(award)
    db.commit()
    db.refresh(award)

    log_audit(db, user=current_user, action="CREATE_RECOGNITION_AWARD", entity="RecognitionAward", entity_id=award.id, result=AuditResult.SUCCESS, request=request)
    g_name = _format_person_name(award.giver)
    r_name = _format_person_name(award.recipient)
    return RecognitionAwardResponse(
        id=award.id,
        tenant_id=award.tenant_id,
        program_id=award.program_id,
        giver_person_id=award.giver_person_id,
        recipient_person_id=award.recipient_person_id,
        title=award.title,
        message=award.message,
        category=award.category,
        visibility=award.visibility,
        awarded_at=award.awarded_at,
        status=award.status,
        created_at=award.created_at,
        giver_name=g_name,
        recipient_name=r_name,
    )


# ---------------------------------------------------------------------------
# 10. Award Definitions & Nominations
# ---------------------------------------------------------------------------

@router.get("/awards", response_model=List[AwardDefinitionResponse])
def list_awards(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return db.query(AwardDefinition).filter(AwardDefinition.tenant_id == tenant_id).all()


@router.post("/awards", response_model=AwardDefinitionResponse, status_code=http_status.HTTP_201_CREATED)
def create_award(
    payload: AwardDefinitionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_awards(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Award management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    award = AwardDefinition(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        criteria=payload.criteria,
        frequency=payload.frequency,
        active=payload.active,
    )
    db.add(award)
    db.commit()
    db.refresh(award)
    log_audit(db, user=current_user, action="CREATE_AWARD_DEFINITION", entity="AwardDefinition", entity_id=award.id, result=AuditResult.SUCCESS, request=request)
    return award


@router.get("/awards/nominations", response_model=List[AwardNominationResponse])
def list_nominations(
    request: Request,
    award_definition_id: Optional[str] = None,
    nomination_status: Optional[AwardNominationStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(AwardNomination).filter(AwardNomination.tenant_id == tenant_id)
    if award_definition_id:
        query = query.filter(AwardNomination.award_definition_id == award_definition_id)
    if nomination_status:
        query = query.filter(AwardNomination.status == nomination_status)

    noms = query.order_by(AwardNomination.created_at.desc()).all()
    results: List[AwardNominationResponse] = []
    for n in noms:
        aw_name = n.award_definition.name if n.award_definition else None
        nom_name = _format_person_name(n.nominee)
        nomr_name = _format_person_name(n.nominator)
        results.append(
            AwardNominationResponse(
                id=n.id,
                tenant_id=n.tenant_id,
                award_definition_id=n.award_definition_id,
                nominee_person_id=n.nominee_person_id,
                nominated_by=n.nominated_by,
                justification=n.justification,
                status=n.status,
                nominated_at=n.nominated_at,
                reviewed_at=n.reviewed_at,
                reviewed_by=n.reviewed_by,
                review_comments=n.review_comments,
                created_at=n.created_at,
                award_name=aw_name,
                nominee_name=nom_name,
                nominator_name=nomr_name,
            )
        )
    return results


@router.post("/awards/nominations", response_model=AwardNominationResponse, status_code=http_status.HTTP_201_CREATED)
def submit_nomination(
    payload: AwardNominationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    nominator_person_id = current_user.person_id or current_user.id

    # Self-nomination check
    if nominator_person_id == payload.nominee_person_id:
        raise HTTPException(status_code=400, detail="Self-nomination is not allowed for this award")

    award_def = db.query(AwardDefinition).filter(
        AwardDefinition.id == payload.award_definition_id,
        AwardDefinition.tenant_id == tenant_id,
    ).first()
    if not award_def:
        raise HTTPException(status_code=404, detail="Award definition not found in tenant")

    nom = AwardNomination(
        tenant_id=tenant_id,
        award_definition_id=payload.award_definition_id,
        nominee_person_id=payload.nominee_person_id,
        nominated_by=nominator_person_id,
        justification=payload.justification,
        status=AwardNominationStatus.NOMINATED,
        nominated_at=datetime.utcnow(),
    )
    db.add(nom)
    db.commit()
    db.refresh(nom)

    log_audit(db, user=current_user, action="SUBMIT_AWARD_NOMINATION", entity="AwardNomination", entity_id=nom.id, result=AuditResult.SUCCESS, request=request)
    return AwardNominationResponse(
        id=nom.id,
        tenant_id=nom.tenant_id,
        award_definition_id=nom.award_definition_id,
        nominee_person_id=nom.nominee_person_id,
        nominated_by=nom.nominated_by,
        justification=nom.justification,
        status=nom.status,
        nominated_at=nom.nominated_at,
        reviewed_at=nom.reviewed_at,
        reviewed_by=nom.reviewed_by,
        review_comments=nom.review_comments,
        created_at=nom.created_at,
        award_name=award_def.name,
    )


@router.put("/awards/nominations/{nomination_id}/review", response_model=AwardNominationResponse)
def review_nomination(
    nomination_id: str,
    payload: AwardNominationReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_awards(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Award management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    nom = db.query(AwardNomination).filter(
        AwardNomination.id == nomination_id,
        AwardNomination.tenant_id == tenant_id,
    ).first()
    if not nom:
        raise HTTPException(status_code=404, detail="Award nomination not found")

    nom.status = payload.status
    nom.reviewed_at = datetime.utcnow()
    nom.reviewed_by = current_user.id
    nom.review_comments = payload.review_comments
    db.commit()
    db.refresh(nom)

    log_audit(db, user=current_user, action="REVIEW_AWARD_NOMINATION", entity="AwardNomination", entity_id=nom.id, result=AuditResult.SUCCESS, request=request)
    return AwardNominationResponse(
        id=nom.id,
        tenant_id=nom.tenant_id,
        award_definition_id=nom.award_definition_id,
        nominee_person_id=nom.nominee_person_id,
        nominated_by=nom.nominated_by,
        justification=nom.justification,
        status=nom.status,
        nominated_at=nom.nominated_at,
        reviewed_at=nom.reviewed_at,
        reviewed_by=nom.reviewed_by,
        review_comments=nom.review_comments,
        created_at=nom.created_at,
        award_name=nom.award_definition.name if nom.award_definition else None,
    )


# ---------------------------------------------------------------------------
# 11. Culture Initiatives & Participation
# ---------------------------------------------------------------------------

@router.get("/culture/initiatives", response_model=List[CultureInitiativeResponse])
def list_culture_initiatives(
    request: Request,
    category: Optional[CultureInitiativeCategory] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    query = db.query(CultureInitiative).filter(CultureInitiative.tenant_id == tenant_id)
    if category:
        query = query.filter(CultureInitiative.category == category)

    inits = query.all()
    results: List[CultureInitiativeResponse] = []
    for i in inits:
        results.append(
            CultureInitiativeResponse(
                id=i.id,
                tenant_id=i.tenant_id,
                name=i.name,
                description=i.description,
                category=i.category,
                owner_user_id=i.owner_user_id,
                start_date=i.start_date,
                end_date=i.end_date,
                status=i.status,
                target_participants=i.target_participants,
                participant_count=len(i.participants),
                created_at=i.created_at,
                updated_at=i.updated_at,
                owner_name=i.owner.email if i.owner else None,
            )
        )
    return results


@router.post("/culture/initiatives", response_model=CultureInitiativeResponse, status_code=http_status.HTTP_201_CREATED)
def create_culture_initiative(
    payload: CultureInitiativeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_culture(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Culture management permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)

    init = CultureInitiative(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        owner_user_id=payload.owner_user_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        target_participants=payload.target_participants,
        status="ACTIVE",
    )
    db.add(init)
    db.commit()
    db.refresh(init)

    log_audit(db, user=current_user, action="CREATE_CULTURE_INITIATIVE", entity="CultureInitiative", entity_id=init.id, result=AuditResult.SUCCESS, request=request)
    return CultureInitiativeResponse(
        id=init.id,
        tenant_id=init.tenant_id,
        name=init.name,
        description=init.description,
        category=init.category,
        owner_user_id=init.owner_user_id,
        start_date=init.start_date,
        end_date=init.end_date,
        status=init.status,
        target_participants=init.target_participants,
        participant_count=0,
        created_at=init.created_at,
        updated_at=init.updated_at,
    )


@router.get("/culture/initiatives/{initiative_id}", response_model=CultureInitiativeResponse)
def get_culture_initiative(
    initiative_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    init = db.query(CultureInitiative).filter(
        CultureInitiative.id == initiative_id,
        CultureInitiative.tenant_id == tenant_id,
    ).first()
    if not init:
        raise HTTPException(status_code=404, detail="Culture initiative not found")

    return CultureInitiativeResponse(
        id=init.id,
        tenant_id=init.tenant_id,
        name=init.name,
        description=init.description,
        category=init.category,
        owner_user_id=init.owner_user_id,
        start_date=init.start_date,
        end_date=init.end_date,
        status=init.status,
        target_participants=init.target_participants,
        participant_count=len(init.participants),
        created_at=init.created_at,
        updated_at=init.updated_at,
        owner_name=init.owner.email if init.owner else None,
    )


@router.post("/culture/initiatives/{initiative_id}/participation", response_model=CultureParticipationResponse, status_code=http_status.HTTP_201_CREATED)
def join_culture_initiative(
    initiative_id: str,
    payload: CultureParticipationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = current_user.person_id or current_user.id

    part = register_culture_participation(
        initiative_id=initiative_id,
        person_id=person_id,
        tenant_id=tenant_id,
        participation_type=payload.participation_type,
        feedback=payload.feedback,
        db=db,
    )
    p_name = _format_person_name(part.person)
    return CultureParticipationResponse(
        id=part.id,
        tenant_id=part.tenant_id,
        initiative_id=part.initiative_id,
        person_id=part.person_id,
        participation_type=part.participation_type,
        feedback=part.feedback,
        participated_at=part.participated_at,
        created_at=part.created_at,
        person_name=p_name,
    )


@router.get("/culture/initiatives/{initiative_id}/participants", response_model=List[CultureParticipationResponse])
def list_culture_participants(
    initiative_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_read_engagement(current_user, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Engagement read permission required")
    tenant_id = _resolve_tenant_id(request, db, current_user)
    parts = db.query(CultureParticipation).filter(
        CultureParticipation.initiative_id == initiative_id,
        CultureParticipation.tenant_id == tenant_id,
    ).all()

    results: List[CultureParticipationResponse] = []
    for p in parts:
        p_name = _format_person_name(p.person)
        results.append(
            CultureParticipationResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                initiative_id=p.initiative_id,
                person_id=p.person_id,
                participation_type=p.participation_type,
                feedback=p.feedback,
                participated_at=p.participated_at,
                created_at=p.created_at,
                person_name=p_name,
            )
        )
    return results
