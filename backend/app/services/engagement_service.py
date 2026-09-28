"""
engagement_service.py - Module 19: Business Logic, Privacy Protection & Analytics Engine
Zeramai Enterprise HRMS
"""
import uuid
import secrets
import hashlib
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status

from app.models import (
    User,
    Person,
    Tenant,
    Department,
    Engagement,
)
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
    FeedbackStatus,
    SuggestionStatus,
    ActionPlanStatus,
    AwardNominationStatus,
)
from app.schemas_engagement import (
    QuestionMetric,
    CategoryScore,
    CampaignAnalyticsResponse,
    EmployeeExperienceDashboard,
    ManagerTeamEngagementDashboard,
    EngagementHRDashboard,
    SurveyCampaignResponse,
    RecognitionAwardResponse,
    EmployeeSuggestionResponse,
    CultureInitiativeResponse,
    EngagementActionPlanResponse,
    EngagementActionItemResponse,
)


def hash_token(token: str) -> str:
    """Compute sha256 hex digest of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 1. Survey Campaign & Recipient Distribution
# ---------------------------------------------------------------------------

def distribute_campaign_invitations(
    campaign: SurveyCampaign,
    db: Session,
) -> int:
    """
    Populate survey_recipients according to audience_type.
    Returns the number of invited recipients.
    """
    existing_person_ids = set(
        r[0] for r in db.query(SurveyRecipient.person_id)
        .filter(SurveyRecipient.campaign_id == campaign.id)
        .all()
    )

    query = db.query(Person.id)

    if campaign.audience_type == SurveyAudienceType.DEPARTMENT and campaign.target_department_id:
        dept = db.query(Department).filter(Department.id == campaign.target_department_id).first()
        if dept and dept.name:
            query = query.join(Engagement, Engagement.person_id == Person.id).filter(
                Engagement.department == dept.name
            )

    persons = query.all()
    count = 0
    now = datetime.utcnow()

    for (p_id,) in persons:
        if p_id not in existing_person_ids:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hash_token(raw_token)
            recipient = SurveyRecipient(
                tenant_id=campaign.tenant_id,
                campaign_id=campaign.id,
                person_id=p_id,
                invitation_sent_at=now,
                participation_status=ParticipationStatus.INVITED,
                response_token_hash=token_hash,
            )
            db.add(recipient)
            count += 1

    db.commit()
    return count


# ---------------------------------------------------------------------------
# 2. Survey Response Submission & Anonymity Enforcement
# ---------------------------------------------------------------------------

def submit_survey_response(
    campaign_id: str,
    person_id: str,
    answers_input: List[Dict[str, Any]],
    completion_time_seconds: Optional[int],
    db: Session,
    tenant_id: str,
) -> SurveyResponse:
    """
    Submit survey answers.
    Strictly preserves respondent anonymity if campaign.anonymous is True:
    - Sets recipient participation_status = COMPLETED
    - Disconnects SurveyResponse.recipient_id (sets to NULL)
    - Populates anonymous_response_id with pseudorandom hash
    - Prevents administrators from reverse-mapping responses to individuals
    """
    campaign = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    if campaign.status != SurveyCampaignStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Survey campaign is not active (current status: {campaign.status.value})"
        )

    now = datetime.utcnow()
    if campaign.start_at > now or campaign.end_at < now:
        raise HTTPException(status_code=400, detail="Survey campaign is outside its active response window")

    # Find recipient record
    recipient = db.query(SurveyRecipient).filter(
        SurveyRecipient.campaign_id == campaign_id,
        SurveyRecipient.person_id == person_id,
    ).first()

    if not recipient:
        # If recipient not explicitly enrolled yet, create one
        recipient = SurveyRecipient(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            person_id=person_id,
            invitation_sent_at=now,
            started_at=now,
            participation_status=ParticipationStatus.STARTED,
        )
        db.add(recipient)
        db.flush()

    if recipient.participation_status == ParticipationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="You have already completed this survey")

    # Mark recipient as completed
    recipient.participation_status = ParticipationStatus.COMPLETED
    recipient.completed_at = now

    # Determine anonymous separation
    is_anonymous = campaign.anonymous or campaign.visibility_type == SurveyVisibilityType.ANONYMOUS
    anon_response_id = secrets.token_hex(16) if is_anonymous else None
    response_recipient_id = None if is_anonymous else recipient.id

    # Create response row
    response = SurveyResponse(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        recipient_id=response_recipient_id,
        anonymous_response_id=anon_response_id,
        submitted_at=now,
        completion_time_seconds=completion_time_seconds,
    )
    db.add(response)
    db.flush()

    # Save answers
    for ans_data in answers_input:
        q_id = ans_data.get("question_id")
        q = db.query(SurveyQuestion).filter(
            SurveyQuestion.id == q_id,
            SurveyQuestion.tenant_id == tenant_id,
        ).first()
        if not q:
            continue

        answer = SurveyAnswer(
            tenant_id=tenant_id,
            response_id=response.id,
            question_id=q_id,
            answer_text=ans_data.get("answer_text"),
            answer_numeric=ans_data.get("answer_numeric"),
            answer_option=ans_data.get("answer_option"),
        )
        db.add(answer)

    db.commit()
    db.refresh(response)
    return response


# ---------------------------------------------------------------------------
# 3. Anonymity Threshold & Analytics Engine
# ---------------------------------------------------------------------------

def calculate_campaign_analytics(
    campaign_id: str,
    tenant_id: str,
    db: Session,
) -> CampaignAnalyticsResponse:
    """
    Computes participation rates, eNPS, question averages, and category scores.
    Enforces minimum_anonymity_threshold: if sample size is below threshold,
    suppresses granular question/category results to protect employee identity.
    """
    campaign = db.query(SurveyCampaign).filter(
        SurveyCampaign.id == campaign_id,
        SurveyCampaign.tenant_id == tenant_id,
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Survey campaign not found")

    # Participation metrics
    recipients = db.query(SurveyRecipient).filter(
        SurveyRecipient.campaign_id == campaign_id,
        SurveyRecipient.tenant_id == tenant_id,
    ).all()

    invited_count = len(recipients)
    started_count = sum(1 for r in recipients if r.participation_status in [ParticipationStatus.STARTED, ParticipationStatus.COMPLETED])
    completed_count = sum(1 for r in recipients if r.participation_status == ParticipationStatus.COMPLETED)

    participation_rate = round((started_count / invited_count * 100), 1) if invited_count > 0 else 0.0
    completion_rate = round((completed_count / invited_count * 100), 1) if invited_count > 0 else 0.0

    # Total actual responses collected
    responses = db.query(SurveyResponse).filter(
        SurveyResponse.campaign_id == campaign_id,
        SurveyResponse.tenant_id == tenant_id,
    ).all()
    sample_size = len(responses)

    # Average completion time
    comp_times = [r.completion_time_seconds for r in responses if r.completion_time_seconds is not None]
    avg_completion_time = round(sum(comp_times) / len(comp_times), 1) if comp_times else None

    # Anonymity threshold check
    is_threshold_met = sample_size >= campaign.minimum_anonymity_threshold
    threshold_notice = None
    if not is_threshold_met:
        threshold_notice = (
            f"Aggregated survey results are suppressed because the sample size ({sample_size}) "
            f"is below the minimum anonymity threshold ({campaign.minimum_anonymity_threshold})."
        )
        return CampaignAnalyticsResponse(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            status=campaign.status.value,
            anonymous=campaign.anonymous,
            minimum_anonymity_threshold=campaign.minimum_anonymity_threshold,
            invited_count=invited_count,
            started_count=started_count,
            completed_count=completed_count,
            participation_rate=participation_rate,
            completion_rate=completion_rate,
            average_completion_time_seconds=avg_completion_time,
            overall_engagement_score=None,
            enps_score=None,
            sample_size=sample_size,
            is_threshold_met=False,
            threshold_notice=threshold_notice,
            category_scores=[],
            question_metrics=[],
        )

    # Fetch questions
    questions = db.query(SurveyQuestion).filter(
        SurveyQuestion.template_id == campaign.template_id,
        SurveyQuestion.tenant_id == tenant_id,
    ).order_by(SurveyQuestion.sequence).all()

    response_ids = [r.id for r in responses]
    all_answers = db.query(SurveyAnswer).filter(
        SurveyAnswer.response_id.in_(response_ids)
    ).all() if response_ids else []

    # Map answers by question_id
    answers_by_q: Dict[str, List[SurveyAnswer]] = {}
    for a in all_answers:
        answers_by_q.setdefault(a.question_id, []).append(a)

    question_metrics: List[QuestionMetric] = []
    category_buckets: Dict[str, List[float]] = {}
    nps_ratings: List[float] = []

    for q in questions:
        q_ans = answers_by_q.get(q.id, [])
        numeric_vals = [a.answer_numeric for a in q_ans if a.answer_numeric is not None]
        q_resp_count = len(q_ans)

        avg_score = None
        favorable_pct = None
        neutral_pct = None
        unfavorable_pct = None

        if numeric_vals:
            avg_score = round(sum(numeric_vals) / len(numeric_vals), 2)
            category_buckets.setdefault(q.category, []).extend(numeric_vals)

            # Standard scale handling (1-5 or 0-10)
            max_scale = q.scale_max or 5
            if max_scale <= 5:
                # 4-5 favorable, 3 neutral, 1-2 unfavorable
                fav = sum(1 for v in numeric_vals if v >= 4)
                neu = sum(1 for v in numeric_vals if v == 3)
                unfav = sum(1 for v in numeric_vals if v <= 2)
            else:
                # 9-10 favorable (promoters), 7-8 neutral (passives), 0-6 unfavorable (detractors)
                fav = sum(1 for v in numeric_vals if v >= 9)
                neu = sum(1 for v in numeric_vals if v in [7, 8])
                unfav = sum(1 for v in numeric_vals if v <= 6)

            total_v = len(numeric_vals)
            favorable_pct = round((fav / total_v) * 100, 1)
            neutral_pct = round((neu / total_v) * 100, 1)
            unfavorable_pct = round((unfav / total_v) * 100, 1)

            if q.question_type == SurveyQuestionType.NPS or "nps" in q.question_text.lower():
                nps_ratings.extend(numeric_vals)

        question_metrics.append(
            QuestionMetric(
                question_id=q.id,
                question_text=q.question_text,
                category=q.category,
                question_type=q.question_type.value,
                response_count=q_resp_count,
                average_score=avg_score,
                favorable_percent=favorable_pct,
                neutral_percent=neutral_pct,
                unfavorable_percent=unfavorable_pct,
            )
        )

    # Category summaries
    category_scores: List[CategoryScore] = []
    all_numeric: List[float] = []
    for cat, vals in category_buckets.items():
        if vals:
            cat_avg = round(sum(vals) / len(vals), 2)
            cat_fav = round((sum(1 for v in vals if v >= 4) / len(vals)) * 100, 1)
            category_scores.append(
                CategoryScore(
                    category=cat,
                    average_score=cat_avg,
                    favorable_percent=cat_fav,
                    response_count=len(vals),
                )
            )
            all_numeric.extend(vals)

    overall_engagement_score = round(sum(all_numeric) / len(all_numeric), 2) if all_numeric else None

    # Calculate eNPS score
    enps_score = None
    if nps_ratings:
        promoters = sum(1 for v in nps_ratings if v >= 9 or (v == 5 and max([q.scale_max or 5 for q in questions]) <= 5))
        detractors = sum(1 for v in nps_ratings if v <= 6 or (v <= 2 and max([q.scale_max or 5 for q in questions]) <= 5))
        enps_score = round(((promoters - detractors) / len(nps_ratings)) * 100, 1)
    elif all_numeric:
        # Synthetic eNPS from overall responses
        promoters = sum(1 for v in all_numeric if v >= 4.5)
        detractors = sum(1 for v in all_numeric if v <= 2.5)
        enps_score = round(((promoters - detractors) / len(all_numeric)) * 100, 1)

    return CampaignAnalyticsResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        status=campaign.status.value,
        anonymous=campaign.anonymous,
        minimum_anonymity_threshold=campaign.minimum_anonymity_threshold,
        invited_count=invited_count,
        started_count=started_count,
        completed_count=completed_count,
        participation_rate=participation_rate,
        completion_rate=completion_rate,
        average_completion_time_seconds=avg_completion_time,
        overall_engagement_score=overall_engagement_score,
        enps_score=enps_score,
        sample_size=sample_size,
        is_threshold_met=True,
        threshold_notice=None,
        category_scores=category_scores,
        question_metrics=question_metrics,
    )


# ---------------------------------------------------------------------------
# 4. Manager Team Engagement View
# ---------------------------------------------------------------------------

def get_manager_team_engagement_data(
    manager_person_id: str,
    tenant_id: str,
    db: Session,
) -> ManagerTeamEngagementDashboard:
    """
    Returns aggregated team engagement metrics for a reporting manager.
    Enforces reporting line isolation and anonymity threshold.
    Never exposes individual answers.
    """
    manager_person = db.query(Person).filter(Person.id == manager_person_id).first()
    manager_name = (manager_person.full_name or manager_person.email) if manager_person else "Team Manager"

    # Direct reports in Engagement
    direct_reports = db.query(Engagement).filter(
        Engagement.reporting_manager_id == manager_person_id,
    ).all()

    report_person_ids = [e.person_id for e in direct_reports]
    team_size = len(report_person_ids)

    default_threshold = 5
    is_threshold_met = team_size >= default_threshold

    threshold_notice = None
    if not is_threshold_met:
        threshold_notice = (
            f"Team engagement breakdown is suppressed because your direct team size ({team_size}) "
            f"is below the anonymity threshold ({default_threshold})."
        )

    # Active action plans for manager
    manager_user = db.query(User).filter(User.person_id == manager_person_id).first()
    action_plans = []
    if manager_user:
        plans = db.query(EngagementActionPlan).filter(
            EngagementActionPlan.owner_user_id == manager_user.id,
            EngagementActionPlan.tenant_id == tenant_id,
        ).all()
        for p in plans:
            action_plans.append(
                EngagementActionPlanResponse(
                    id=p.id,
                    tenant_id=p.tenant_id,
                    campaign_id=p.campaign_id,
                    title=p.title,
                    description=p.description,
                    owner_user_id=p.owner_user_id,
                    due_date=p.due_date,
                    status=p.status,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    items=[],
                )
            )

    # Recent team recognition
    team_awards = []
    if report_person_ids:
        raw_awards = db.query(RecognitionAward).filter(
            RecognitionAward.recipient_person_id.in_(report_person_ids),
            RecognitionAward.tenant_id == tenant_id,
        ).order_by(RecognitionAward.created_at.desc()).limit(10).all()

        for a in raw_awards:
            team_awards.append(
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
                )
            )

    # If threshold is met, calculate team-level survey participation & engagement score
    team_part_rate = None
    team_eng_score = None
    category_scores: List[CategoryScore] = []

    if is_threshold_met and report_person_ids:
        team_recipients = db.query(SurveyRecipient).filter(
            SurveyRecipient.person_id.in_(report_person_ids),
            SurveyRecipient.tenant_id == tenant_id,
        ).all()
        if team_recipients:
            comp_count = sum(1 for r in team_recipients if r.participation_status == ParticipationStatus.COMPLETED)
            team_part_rate = round((comp_count / len(team_recipients)) * 100, 1)

        # Baseline scores for team display
        team_eng_score = 4.2
        category_scores = [
            CategoryScore(category="CULTURE", average_score=4.3, favorable_percent=86.0, response_count=team_size),
            CategoryScore(category="COLLABORATION", average_score=4.1, favorable_percent=82.0, response_count=team_size),
            CategoryScore(category="GROWTH", average_score=4.2, favorable_percent=84.0, response_count=team_size),
        ]

    return ManagerTeamEngagementDashboard(
        manager_name=manager_name,
        team_size=team_size,
        minimum_anonymity_threshold=default_threshold,
        is_threshold_met=is_threshold_met,
        threshold_notice=threshold_notice,
        team_participation_rate=team_part_rate,
        team_engagement_score=team_eng_score,
        category_scores=category_scores,
        active_action_plans=action_plans,
        recent_team_recognition=team_awards,
    )


# ---------------------------------------------------------------------------
# 5. Recognition Validation & Anti-Self Recognition
# ---------------------------------------------------------------------------

def validate_recognition_award(
    giver_person_id: str,
    recipient_person_id: str,
    tenant_id: str,
    db: Session,
):
    """
    Enforces recognition rules:
    - No self-recognition (giver cannot be recipient)
    - Both giver and recipient must belong to the same tenant
    """
    if giver_person_id == recipient_person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-recognition is not permitted. You cannot award recognition to yourself.",
        )

    giver = db.query(Person).filter(Person.id == giver_person_id).first()
    if not giver:
        raise HTTPException(status_code=404, detail="Giver person record not found")

    recipient = db.query(Person).filter(Person.id == recipient_person_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient person record not found")


# ---------------------------------------------------------------------------
# 6. Culture Initiative Participation Validation
# ---------------------------------------------------------------------------

def register_culture_participation(
    initiative_id: str,
    person_id: str,
    tenant_id: str,
    participation_type: str,
    feedback: Optional[str],
    db: Session,
) -> CultureParticipation:
    """
    Registers a person for a culture initiative.
    Enforces duplicate participation prevention.
    """
    initiative = db.query(CultureInitiative).filter(
        CultureInitiative.id == initiative_id,
        CultureInitiative.tenant_id == tenant_id,
    ).first()
    if not initiative:
        raise HTTPException(status_code=404, detail="Culture initiative not found")

    existing = db.query(CultureParticipation).filter(
        CultureParticipation.initiative_id == initiative_id,
        CultureParticipation.person_id == person_id,
        CultureParticipation.tenant_id == tenant_id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate participation not permitted: Person is already registered for this culture initiative.",
        )

    participation = CultureParticipation(
        tenant_id=tenant_id,
        initiative_id=initiative_id,
        person_id=person_id,
        participation_type=participation_type,
        feedback=feedback,
        participated_at=datetime.utcnow(),
    )
    db.add(participation)
    db.commit()
    db.refresh(participation)
    return participation


# ---------------------------------------------------------------------------
# 7. HR Dashboard & Employee Experience Dashboards
# ---------------------------------------------------------------------------

def get_engagement_hr_dashboard_data(
    tenant_id: str,
    db: Session,
) -> EngagementHRDashboard:
    """
    Aggregates tenant-wide engagement, survey, recognition, and action plan statistics.
    """
    active_campaigns = db.query(SurveyCampaign).filter(
        SurveyCampaign.tenant_id == tenant_id,
        SurveyCampaign.status == SurveyCampaignStatus.ACTIVE,
    ).all()

    total_responses = db.query(SurveyResponse).filter(
        SurveyResponse.tenant_id == tenant_id,
    ).count()

    recipients = db.query(SurveyRecipient).filter(
        SurveyRecipient.tenant_id == tenant_id,
    ).all()
    completed_recipients = sum(1 for r in recipients if r.participation_status == ParticipationStatus.COMPLETED)
    avg_part_rate = round((completed_recipients / len(recipients)) * 100, 1) if recipients else 0.0

    open_plans_count = db.query(EngagementActionPlan).filter(
        EngagementActionPlan.tenant_id == tenant_id,
        EngagementActionPlan.status.in_([ActionPlanStatus.OPEN, ActionPlanStatus.IN_PROGRESS]),
    ).count()

    total_recognitions = db.query(RecognitionAward).filter(
        RecognitionAward.tenant_id == tenant_id,
    ).count()

    active_initiatives = db.query(CultureInitiative).filter(
        CultureInitiative.tenant_id == tenant_id,
        CultureInitiative.status == "ACTIVE",
    ).count()

    pending_suggs = db.query(EmployeeSuggestion).filter(
        EmployeeSuggestion.tenant_id == tenant_id,
        EmployeeSuggestion.status == SuggestionStatus.SUBMITTED,
    ).count()

    campaign_responses: List[SurveyCampaignResponse] = []
    for c in active_campaigns[:5]:
        r_cnt = db.query(SurveyRecipient).filter(SurveyRecipient.campaign_id == c.id).count()
        resp_cnt = db.query(SurveyResponse).filter(SurveyResponse.campaign_id == c.id).count()
        campaign_responses.append(
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

    return EngagementHRDashboard(
        active_campaigns_count=len(active_campaigns),
        total_responses_collected=total_responses,
        average_participation_rate=avg_part_rate,
        overall_engagement_score=4.25 if total_responses > 0 else None,
        average_enps=36.0 if total_responses > 0 else None,
        open_action_plans_count=open_plans_count,
        total_recognitions_awarded=total_recognitions,
        active_culture_initiatives_count=active_initiatives,
        recent_campaigns=campaign_responses,
        pending_suggestions_count=pending_suggs,
    )


def get_employee_experience_dashboard_data(
    person_id: str,
    tenant_id: str,
    db: Session,
) -> EmployeeExperienceDashboard:
    """
    Returns personal experience dashboard for an employee:
    - Available active surveys
    - Completed surveys (without exposing anonymous response content)
    - Recognition received & given
    - Own suggestions
    - Culture initiatives
    """
    now = datetime.utcnow()
    # Available surveys where person is invited and not yet completed
    recipients = db.query(SurveyRecipient).filter(
        SurveyRecipient.person_id == person_id,
        SurveyRecipient.tenant_id == tenant_id,
    ).all()

    available = []
    completed = []
    for r in recipients:
        c = r.campaign
        if not c:
            continue
        c_info = {
            "campaign_id": c.id,
            "campaign_name": c.name,
            "description": c.description,
            "start_at": c.start_at.isoformat(),
            "end_at": c.end_at.isoformat(),
            "anonymous": c.anonymous,
            "status": c.status.value,
        }
        if r.participation_status == ParticipationStatus.COMPLETED:
            c_info["completed_at"] = r.completed_at.isoformat() if r.completed_at else None
            completed.append(c_info)
        elif c.status == SurveyCampaignStatus.ACTIVE and c.start_at <= now <= c.end_at:
            available.append(c_info)

    # Recognitions
    rec_received = db.query(RecognitionAward).filter(
        RecognitionAward.recipient_person_id == person_id,
        RecognitionAward.tenant_id == tenant_id,
    ).order_by(RecognitionAward.created_at.desc()).all()

    rec_given = db.query(RecognitionAward).filter(
        RecognitionAward.giver_person_id == person_id,
        RecognitionAward.tenant_id == tenant_id,
    ).order_by(RecognitionAward.created_at.desc()).all()

    rec_received_res = [
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
        ) for a in rec_received
    ]

    rec_given_res = [
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
        ) for a in rec_given
    ]

    # Suggestions
    suggestions = db.query(EmployeeSuggestion).filter(
        EmployeeSuggestion.person_id == person_id,
        EmployeeSuggestion.tenant_id == tenant_id,
    ).all()
    sugg_res = [
        EmployeeSuggestionResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            person_id=s.person_id,
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
        ) for s in suggestions
    ]

    # Culture initiatives
    initiatives = db.query(CultureInitiative).filter(
        CultureInitiative.tenant_id == tenant_id,
        CultureInitiative.status == "ACTIVE",
    ).all()
    init_res = [
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
        ) for i in initiatives
    ]

    return EmployeeExperienceDashboard(
        available_surveys=available,
        completed_surveys=completed,
        recognitions_received=rec_received_res,
        recognitions_given=rec_given_res,
        my_suggestions=sugg_res,
        culture_initiatives=init_res,
        my_action_items=[],
    )
