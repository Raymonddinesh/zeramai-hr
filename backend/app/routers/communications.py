"""
communications.py - Module 20: Enterprise Employee Communications Router
Prefix: /api/v3/communications
Zeramai Enterprise HRMS
"""
from typing import List, Optional, Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.deps import get_current_user, require_permission
from app.models import User, Person, Engagement, Tenant
from app.models_communications import (
    EmployeeAnnouncement,
    AnnouncementAudienceRule,
    AnnouncementReadReceipt,
    CommunicationAcknowledgement,
    CommunicationTemplate,
    CommunicationPreference,
    KnowledgeSearchEvent,
    AnnouncementType,
    AnnouncementPriority,
    AnnouncementStatus,
    AudienceType,
    CommunicationTemplateType,
    CommunicationCategory,
)
from app.schemas_communications import (
    EmployeeAnnouncementCreate,
    EmployeeAnnouncementUpdate,
    EmployeeAnnouncementResponse,
    EmployeeAnnouncementDetailResponse,
    AnnouncementAudienceRuleCreate,
    AnnouncementAudienceRuleResponse,
    AnnouncementReadReceiptResponse,
    CommunicationAcknowledgementCreate,
    CommunicationAcknowledgementResponse,
    CommunicationTemplateCreate,
    CommunicationTemplateUpdate,
    CommunicationTemplateResponse,
    CommunicationPreferenceCreate,
    CommunicationPreferenceUpdate,
    CommunicationPreferenceResponse,
    AudienceReachEstimateResponse,
    CommunicationsDashboardResponse,
    ManagerTeamCommunicationsResponse,
    KnowledgeSearchAnalytics,
)
from app.services import communications_service

router = APIRouter(prefix="/api/v3/communications", tags=["Employee Communications"])


def _resolve_tenant_id(request: Request, db: Session, current_user: Optional[User] = None) -> str:
    header_tenant = request.headers.get("X-Tenant-ID")
    if header_tenant:
        return header_tenant
    if current_user and getattr(current_user, "tenant_id", None):
        return current_user.tenant_id
    if current_user and getattr(current_user, "person", None) and getattr(current_user.person, "tenant_id", None):
        return current_user.person.tenant_id
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


# ===========================================================================
# 1. Announcements Lifecycle & Audience
# ===========================================================================

@router.get("/announcements", response_model=List[EmployeeAnnouncementResponse])
def list_announcements(
    request: Request,
    unread_only: bool = Query(False, description="Filter only unread announcements"),
    priority: Optional[AnnouncementPriority] = None,
    announcement_type: Optional[AnnouncementType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List announcements accessible to current employee based on server-side audience matching."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    person_id = getattr(current_user, "person_id", None)
    user_role = getattr(current_user, "role", "").lower()

    q = db.query(EmployeeAnnouncement).filter(EmployeeAnnouncement.tenant_id == tenant_id)

    if user_role not in ["super_admin", "hr_admin"]:
        q = q.filter(EmployeeAnnouncement.status == AnnouncementStatus.PUBLISHED)

    if priority:
        q = q.filter(EmployeeAnnouncement.priority == priority)
    if announcement_type:
        q = q.filter(EmployeeAnnouncement.announcement_type == announcement_type)

    candidates = q.order_by(
        EmployeeAnnouncement.priority.desc(),
        EmployeeAnnouncement.publish_at.desc(),
    ).all()

    accessible = [a for a in candidates if communications_service.user_matches_announcement_audience(db, a, current_user)]

    res = []
    for a in accessible:
        reads = db.query(func.count(AnnouncementReadReceipt.id)).filter(
            AnnouncementReadReceipt.announcement_id == a.id,
        ).scalar() or 0
        acks = db.query(func.count(CommunicationAcknowledgement.id)).filter(
            CommunicationAcknowledgement.announcement_id == a.id,
        ).scalar() or 0

        is_read = False
        is_acked = False
        if person_id:
            is_read = db.query(AnnouncementReadReceipt).filter(
                AnnouncementReadReceipt.announcement_id == a.id,
                AnnouncementReadReceipt.person_id == person_id,
            ).first() is not None

            is_acked = db.query(CommunicationAcknowledgement).filter(
                CommunicationAcknowledgement.announcement_id == a.id,
                CommunicationAcknowledgement.person_id == person_id,
            ).first() is not None

        if unread_only and is_read:
            continue

        res.append({
            "id": a.id,
            "tenant_id": a.tenant_id,
            "title": a.title,
            "summary": a.summary,
            "announcement_type": a.announcement_type,
            "priority": a.priority,
            "status": a.status,
            "author_user_id": a.author_user_id,
            "author_name": a.author.email if a.author else None,
            "publish_at": a.publish_at,
            "expires_at": a.expires_at,
            "acknowledgement_required": a.acknowledgement_required,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "read_count": reads,
            "acknowledgement_count": acks,
            "is_read_by_me": is_read,
            "is_acknowledged_by_me": is_acked,
        })

    return res


@router.post("/announcements", response_model=EmployeeAnnouncementDetailResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    request: Request,
    payload: EmployeeAnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.manage")),
):
    """Create a new broadcast announcement with audience targeting rules."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    pub_at = payload.publish_at or datetime.utcnow()
    if pub_at.tzinfo is not None:
        pub_at = pub_at.replace(tzinfo=None)
    exp_at = payload.expires_at
    if exp_at is not None and exp_at.tzinfo is not None:
        exp_at = exp_at.replace(tzinfo=None)

    initial_status = AnnouncementStatus.DRAFT
    if pub_at > datetime.utcnow():
        initial_status = AnnouncementStatus.SCHEDULED

    ann = EmployeeAnnouncement(
        tenant_id=tenant_id,
        title=payload.title,
        summary=payload.summary,
        content_reference=payload.content_reference,
        announcement_type=payload.announcement_type,
        priority=payload.priority,
        status=initial_status,
        author_user_id=current_user.id,
        publish_at=pub_at,
        expires_at=exp_at,
        acknowledgement_required=payload.acknowledgement_required,
    )
    db.add(ann)
    db.flush()

    if payload.audience_rules:
        for r in payload.audience_rules:
            rule = AnnouncementAudienceRule(
                tenant_id=tenant_id,
                announcement_id=ann.id,
                audience_type=r.audience_type,
                legal_entity_id=r.legal_entity_id,
                department_id=r.department_id,
                organization_unit_id=r.organization_unit_id,
                location_reference=r.location_reference,
                role_reference=r.role_reference,
                employment_type=r.employment_type,
                manager_scope=r.manager_scope,
            )
            db.add(rule)

    db.commit()
    db.refresh(ann)
    return ann


@router.get("/announcements/{id}", response_model=EmployeeAnnouncementDetailResponse)
def get_announcement(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single announcement details with audience rules. Enforces access control."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    ann = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    if not communications_service.user_matches_announcement_audience(db, ann, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this announcement")

    reads = db.query(func.count(AnnouncementReadReceipt.id)).filter(
        AnnouncementReadReceipt.announcement_id == ann.id,
    ).scalar() or 0
    acks = db.query(func.count(CommunicationAcknowledgement.id)).filter(
        CommunicationAcknowledgement.announcement_id == ann.id,
    ).scalar() or 0

    person_id = getattr(current_user, "person_id", None)
    is_read = False
    is_acked = False
    if person_id:
        is_read = db.query(AnnouncementReadReceipt).filter(
            AnnouncementReadReceipt.announcement_id == ann.id,
            AnnouncementReadReceipt.person_id == person_id,
        ).first() is not None
        is_acked = db.query(CommunicationAcknowledgement).filter(
            CommunicationAcknowledgement.announcement_id == ann.id,
            CommunicationAcknowledgement.person_id == person_id,
        ).first() is not None

    return {
        "id": ann.id,
        "tenant_id": ann.tenant_id,
        "title": ann.title,
        "summary": ann.summary,
        "content_reference": ann.content_reference,
        "announcement_type": ann.announcement_type,
        "priority": ann.priority,
        "status": ann.status,
        "author_user_id": ann.author_user_id,
        "author_name": ann.author.email if ann.author else None,
        "publish_at": ann.publish_at,
        "expires_at": ann.expires_at,
        "acknowledgement_required": ann.acknowledgement_required,
        "created_at": ann.created_at,
        "updated_at": ann.updated_at,
        "read_count": reads,
        "acknowledgement_count": acks,
        "is_read_by_me": is_read,
        "is_acknowledged_by_me": is_acked,
        "audience_rules": ann.audience_rules,
    }


@router.put("/announcements/{id}", response_model=EmployeeAnnouncementResponse)
def update_announcement(
    id: str,
    request: Request,
    payload: EmployeeAnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.manage")),
):
    """Update announcement properties."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    ann = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    if payload.title is not None:
        ann.title = payload.title
    if payload.summary is not None:
        ann.summary = payload.summary
    if payload.content_reference is not None:
        ann.content_reference = payload.content_reference
    if payload.announcement_type is not None:
        ann.announcement_type = payload.announcement_type
    if payload.priority is not None:
        ann.priority = payload.priority
    if payload.publish_at is not None:
        p_at = payload.publish_at
        if p_at.tzinfo is not None:
            p_at = p_at.replace(tzinfo=None)
        ann.publish_at = p_at
    if payload.expires_at is not None:
        e_at = payload.expires_at
        if e_at.tzinfo is not None:
            e_at = e_at.replace(tzinfo=None)
        ann.expires_at = e_at
    if payload.acknowledgement_required is not None:
        ann.acknowledgement_required = payload.acknowledgement_required

    ann.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ann)
    return ann


@router.post("/announcements/{id}/publish", response_model=EmployeeAnnouncementResponse)
def publish_announcement(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.publish")),
):
    """Publish an announcement immediately."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    ann = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    ann.status = AnnouncementStatus.PUBLISHED
    ann.publish_at = datetime.utcnow()
    ann.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ann)
    return ann


@router.post("/announcements/{id}/cancel", response_model=EmployeeAnnouncementResponse)
def cancel_announcement(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.manage")),
):
    """Cancel a scheduled or published announcement."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    ann = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    ann.status = AnnouncementStatus.CANCELLED
    ann.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ann)
    return ann


@router.post("/announcements/{id}/read", response_model=AnnouncementReadReceiptResponse)
def mark_announcement_read(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record that the current employee has read the announcement (idempotent)."""
    person_id = getattr(current_user, "person_id", None)
    if not person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only employees can record read receipts")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    receipt = communications_service.record_announcement_read(
        db=db,
        tenant_id=tenant_id,
        announcement_id=id,
        person_id=person_id,
    )
    return receipt


@router.post("/announcements/{id}/acknowledge", response_model=CommunicationAcknowledgementResponse)
def acknowledge_announcement(
    id: str,
    request: Request,
    payload: CommunicationAcknowledgementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge a non-policy broadcast communication."""
    person_id = getattr(current_user, "person_id", None)
    if not person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only employees can acknowledge communications")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    ack = communications_service.record_communication_acknowledgement(
        db=db,
        tenant_id=tenant_id,
        announcement_id=id,
        person_id=person_id,
        ack_ref=payload.acknowledgement_reference,
    )
    return ack


@router.get("/announcements/{id}/reach", response_model=AudienceReachEstimateResponse)
def get_announcement_reach_preview(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.manage")),
):
    """Preview estimated recipient reach before or after publishing without exposing private identities."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    ann = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    reach = communications_service.estimate_announcement_reach(
        db=db,
        tenant_id=tenant_id,
        rules=ann.audience_rules,
    )
    return {
        "announcement_id": id,
        "audience_type": "AUDIENCE_TARGETED",
        "target_count": reach,
        "note": "Estimated employee recipient count based on server-side criteria",
    }


# ===========================================================================
# 2. Templates
# ===========================================================================

@router.get("/templates", response_model=List[CommunicationTemplateResponse])
def list_templates(
    request: Request,
    template_type: Optional[CommunicationTemplateType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List reusable broadcast communication templates."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.tenant_id == tenant_id,
        CommunicationTemplate.active == True,
    )
    if template_type:
        q = q.filter(CommunicationTemplate.template_type == template_type)
    return q.order_by(CommunicationTemplate.name.asc()).all()


@router.post("/templates", response_model=CommunicationTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    request: Request,
    payload: CommunicationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.templates.manage")),
):
    """Create a new communication template."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = CommunicationTemplate(
        tenant_id=tenant_id,
        name=payload.name,
        template_type=payload.template_type,
        subject_template=payload.subject_template,
        body_reference=payload.body_reference,
        active=payload.active,
        created_by=current_user.id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.get("/templates/{id}", response_model=CommunicationTemplateResponse)
def get_template(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve communication template by ID."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.id == id,
        CommunicationTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return tmpl


@router.put("/templates/{id}", response_model=CommunicationTemplateResponse)
def update_template(
    id: str,
    request: Request,
    payload: CommunicationTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.templates.manage")),
):
    """Update communication template."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.id == id,
        CommunicationTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    if payload.name:
        tmpl.name = payload.name
    if payload.template_type:
        tmpl.template_type = payload.template_type
    if payload.subject_template:
        tmpl.subject_template = payload.subject_template
    if payload.body_reference:
        tmpl.body_reference = payload.body_reference
    if payload.active is not None:
        tmpl.active = payload.active

    tmpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/templates/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.templates.manage")),
):
    """Deactivate or remove communication template."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    tmpl = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.id == id,
        CommunicationTemplate.tenant_id == tenant_id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    db.delete(tmpl)
    db.commit()
    return None


# ===========================================================================
# 3. Preferences
# ===========================================================================

@router.get("/preferences", response_model=List[CommunicationPreferenceResponse])
def get_preferences(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current employee communication channel preferences."""
    person_id = getattr(current_user, "person_id", None)
    if not person_id:
        return []

    tenant_id = _resolve_tenant_id(request, db, current_user)
    prefs = db.query(CommunicationPreference).filter(
        CommunicationPreference.tenant_id == tenant_id,
        CommunicationPreference.person_id == person_id,
    ).all()
    return prefs


@router.put("/preferences/{comm_type}", response_model=CommunicationPreferenceResponse)
def update_preference(
    comm_type: CommunicationCategory,
    request: Request,
    payload: CommunicationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update preference for a communication category. Strictly blocks disabling mandatory HR notices."""
    person_id = getattr(current_user, "person_id", None)
    if not person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only employees can configure communication preferences")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    return communications_service.update_employee_communication_preference(
        db=db,
        tenant_id=tenant_id,
        person_id=person_id,
        comm_type=comm_type,
        email_enabled=payload.email_enabled,
        in_app_enabled=payload.in_app_enabled,
        sms_enabled=payload.sms_enabled,
    )


# ===========================================================================
# 4. Manager Team Communications
# ===========================================================================

@router.get("/team", response_model=ManagerTeamCommunicationsResponse)
def get_manager_team_communications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get team communications and aggregate reach/read rate scoped strictly to reporting lines."""
    person_id = getattr(current_user, "person_id", None)
    if not person_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager identity could not be resolved")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    # Verify if caller manages anyone
    report_count = db.query(func.count(Engagement.id)).filter(
        Engagement.reporting_manager_id.in_([person_id, current_user.id]),
        Engagement.status == "ACTIVE",
    ).scalar() or 0

    user_role = getattr(current_user, "role", "").lower()
    if report_count == 0 and user_role not in ["super_admin", "hr_admin", "hiring_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No direct reports found for this manager")

    summary = communications_service.get_manager_team_communications_summary(
        db=db,
        tenant_id=tenant_id,
        manager_person_id=person_id,
    )
    return summary


# ===========================================================================
# 5. Broadcast Center Analytics & Search Analytics
# ===========================================================================

@router.get("/dashboard", response_model=CommunicationsDashboardResponse)
def get_broadcast_center_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("communications.analytics.read")),
):
    """HR Broadcast Center analytics dashboard."""
    tenant_id = _resolve_tenant_id(request, db, current_user)

    total = db.query(func.count(EmployeeAnnouncement.id)).filter(
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).scalar() or 0

    pub = db.query(func.count(EmployeeAnnouncement.id)).filter(
        EmployeeAnnouncement.tenant_id == tenant_id,
        EmployeeAnnouncement.status == AnnouncementStatus.PUBLISHED,
    ).scalar() or 0

    sched = db.query(func.count(EmployeeAnnouncement.id)).filter(
        EmployeeAnnouncement.tenant_id == tenant_id,
        EmployeeAnnouncement.status == AnnouncementStatus.SCHEDULED,
    ).scalar() or 0

    crit = db.query(func.count(EmployeeAnnouncement.id)).filter(
        EmployeeAnnouncement.tenant_id == tenant_id,
        EmployeeAnnouncement.priority == AnnouncementPriority.CRITICAL,
        EmployeeAnnouncement.status == AnnouncementStatus.PUBLISHED,
    ).scalar() or 0

    templates = db.query(func.count(CommunicationTemplate.id)).filter(
        CommunicationTemplate.tenant_id == tenant_id,
        CommunicationTemplate.active == True,
    ).scalar() or 0

    # Aggregate rates
    reads = db.query(func.count(AnnouncementReadReceipt.id)).filter(
        AnnouncementReadReceipt.tenant_id == tenant_id,
    ).scalar() or 0
    acks = db.query(func.count(CommunicationAcknowledgement.id)).filter(
        CommunicationAcknowledgement.tenant_id == tenant_id,
    ).scalar() or 0
    emp_count = db.query(func.count(Engagement.id)).filter(
        Engagement.tenant_id == tenant_id,
        Engagement.status == "ACTIVE",
    ).scalar() or 1

    expected_total = max(1, emp_count * max(1, pub))
    read_rate = round((reads / expected_total * 100), 1)
    ack_rate = round((acks / max(1, reads) * 100), 1)

    recent = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).order_by(EmployeeAnnouncement.created_at.desc()).limit(5).all()

    return {
        "total_announcements": total,
        "published_announcements": pub,
        "scheduled_announcements": sched,
        "critical_notices_count": crit,
        "overall_read_rate_pct": min(100.0, read_rate),
        "overall_acknowledgement_rate_pct": min(100.0, ack_rate),
        "active_templates_count": templates,
        "recent_announcements": recent,
    }


@router.get("/analytics/search", response_model=KnowledgeSearchAnalytics)
def get_search_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.analytics.read")),
):
    """Aggregate search metrics from hashed privacy-preserving logs."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    total_searches = db.query(func.count(KnowledgeSearchEvent.id)).filter(
        KnowledgeSearchEvent.tenant_id == tenant_id,
    ).scalar() or 0

    zero_results = db.query(func.count(KnowledgeSearchEvent.id)).filter(
        KnowledgeSearchEvent.tenant_id == tenant_id,
        KnowledgeSearchEvent.result_count == 0,
    ).scalar() or 0

    top_events = db.query(
        KnowledgeSearchEvent.query_hash,
        func.count(KnowledgeSearchEvent.id).label("count"),
    ).filter(
        KnowledgeSearchEvent.tenant_id == tenant_id,
    ).group_by(KnowledgeSearchEvent.query_hash).order_by(desc("count")).limit(10).all()

    top_list = [{"query_hash": t[0], "count": t[1]} for t in top_events]

    return {
        "total_searches": total_searches,
        "zero_result_searches": zero_results,
        "top_search_hashes": top_list,
    }
