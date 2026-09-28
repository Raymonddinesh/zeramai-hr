"""
communications_service.py - Module 20: Enterprise Employee Communications & Knowledge Management Service
Zeramai Enterprise HRMS
"""
import hashlib
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import func, or_, and_, desc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models_communications import (
    KnowledgeCategory,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeAccessRule,
    KnowledgeArticleRelation,
    KnowledgeFeedback,
    KnowledgeArticleView,
    KnowledgeReviewTask,
    KnowledgeSearchEvent,
    EmployeeAnnouncement,
    AnnouncementAudienceRule,
    AnnouncementReadReceipt,
    CommunicationAcknowledgement,
    CommunicationTemplate,
    CommunicationPreference,
    ArticleType,
    ArticleStatus,
    ArticleVisibility,
    AccessRuleType,
    ArticleRelationType,
    KnowledgeFeedbackType,
    ReviewTaskStatus,
    AnnouncementType,
    AnnouncementPriority,
    AnnouncementStatus,
    AudienceType,
    CommunicationCategory,
)
from app.models import Person, Engagement, User


# ===========================================================================
# 1. Knowledge Category Hierarchy & Cycle Prevention
# ===========================================================================

def validate_category_hierarchy(db: Session, tenant_id: str, category_id: Optional[str], new_parent_id: Optional[str]):
    """Ensure parent exists in same tenant and prevent circular references."""
    if not new_parent_id:
        return

    if category_id and category_id == new_parent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Circular category reference detected: category cannot be its own parent",
        )

    parent = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.id == new_parent_id,
        KnowledgeCategory.tenant_id == tenant_id,
    ).first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent category not found in tenant",
        )

    # Walk ancestors to detect deeper cycles
    curr_id = parent.parent_id
    visited = {new_parent_id}
    while curr_id:
        if category_id and curr_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Circular category reference detected in category hierarchy chain",
            )
        if curr_id in visited:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Circular category loop detected in existing parent structure",
            )
        visited.add(curr_id)
        ancestor = db.query(KnowledgeCategory).filter(
            KnowledgeCategory.id == curr_id,
            KnowledgeCategory.tenant_id == tenant_id,
        ).first()
        curr_id = ancestor.parent_id if ancestor else None


def get_category_tree_data(db: Session, tenant_id: str) -> List[Dict[str, Any]]:
    """Build full hierarchical tree of active categories for the tenant."""
    categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.tenant_id == tenant_id,
    ).order_by(KnowledgeCategory.display_order.asc(), KnowledgeCategory.name.asc()).all()

    cat_map: Dict[str, Dict[str, Any]] = {}
    roots: List[Dict[str, Any]] = []

    for cat in categories:
        art_count = db.query(func.count(KnowledgeArticle.id)).filter(
            KnowledgeArticle.category_id == cat.id,
            KnowledgeArticle.status == ArticleStatus.PUBLISHED,
        ).scalar() or 0

        cat_map[cat.id] = {
            "id": cat.id,
            "tenant_id": cat.tenant_id,
            "code": cat.code,
            "name": cat.name,
            "description": cat.description,
            "parent_id": cat.parent_id,
            "display_order": cat.display_order,
            "active": cat.active,
            "created_at": cat.created_at,
            "updated_at": cat.updated_at,
            "article_count": art_count,
            "children": [],
        }

    for cat_id, node in cat_map.items():
        p_id = node["parent_id"]
        if p_id and p_id in cat_map:
            cat_map[p_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


# ===========================================================================
# 2. Knowledge Access Authorization (Server-Side)
# ===========================================================================

def user_can_access_article(db: Session, article: KnowledgeArticle, user: Any) -> bool:
    """Evaluate server-side whether user has authority to read an article."""
    if not user:
        return False

    user_role = getattr(user, "role", "").lower()
    if user_role in ["super_admin", "hr_admin"]:
        return True

    # If article is not published, only owner or HR/admin can view it
    if article.status != ArticleStatus.PUBLISHED:
        if article.owner_user_id == getattr(user, "id", None):
            return True
        return False

    # Check Visibility
    if article.visibility == ArticleVisibility.ALL_EMPLOYEES:
        return True

    if article.visibility == ArticleVisibility.HR_ONLY:
        return user_role in ["hr_admin", "super_admin"]

    person_id = getattr(user, "person_id", None)
    engagement = None
    if person_id:
        engagement = db.query(Engagement).filter(Engagement.person_id == person_id).first()

    if article.visibility == ArticleVisibility.MANAGERS:
        if user_role in ["hiring_manager", "manager"]:
            return True
        if person_id:
            user_id = getattr(user, "id", None)
            is_mgr = db.query(Engagement).filter(
                Engagement.reporting_manager_id.in_([person_id, user_id])
            ).first()
            if is_mgr:
                return True
        return False

    if article.visibility == ArticleVisibility.CUSTOM_AUDIENCE:
        rules = db.query(KnowledgeAccessRule).filter(
            KnowledgeAccessRule.article_id == article.id,
            KnowledgeAccessRule.tenant_id == article.tenant_id,
        ).all()
        if not rules:
            return True  # If custom audience with no rules, default to visible

        for r in rules:
            if r.rule_type == AccessRuleType.TENANT:
                return True
            if r.rule_type == AccessRuleType.ROLE and r.role_reference:
                if user_role == r.role_reference.lower():
                    return True
            if engagement:
                if r.rule_type == AccessRuleType.DEPARTMENT and r.department_id:
                    if engagement.department == r.department_id:
                        return True
                if r.rule_type == AccessRuleType.LOCATION and r.location_reference:
                    if engagement.work_location == r.location_reference:
                        return True

        return False

    return False


# ===========================================================================
# 3. Knowledge Article Lifecycle & Immutable Versioning
# ===========================================================================

def create_article_with_version(
    db: Session,
    tenant_id: str,
    user_id: str,
    category_id: str,
    title: str,
    slug: str,
    summary: Optional[str],
    content_reference: str,
    article_type: ArticleType,
    visibility: ArticleVisibility,
    review_due_at: Optional[datetime] = None,
    change_summary: Optional[str] = "Initial draft",
    status_val: ArticleStatus = ArticleStatus.DRAFT,
) -> KnowledgeArticle:
    """Create a new article and its sequential version 1."""
    category = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.id == category_id,
        KnowledgeCategory.tenant_id == tenant_id,
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if review_due_at and review_due_at.tzinfo is not None:
        review_due_at = review_due_at.replace(tzinfo=None)

    article = KnowledgeArticle(
        tenant_id=tenant_id,
        category_id=category_id,
        title=title,
        slug=slug,
        summary=summary,
        content_reference=content_reference,
        article_type=article_type,
        status=status_val,
        visibility=visibility,
        owner_user_id=user_id,
        review_due_at=review_due_at,
        published_at=datetime.utcnow() if status_val == ArticleStatus.PUBLISHED else None,
    )
    db.add(article)
    db.flush()

    # Immutable initial version
    version = KnowledgeArticleVersion(
        tenant_id=tenant_id,
        article_id=article.id,
        version_number=1,
        title=title,
        content_reference=content_reference,
        change_summary=change_summary,
        created_by=user_id,
        published_at=datetime.utcnow() if status_val == ArticleStatus.PUBLISHED else None,
    )
    db.add(version)
    db.commit()
    db.refresh(article)
    return article


def update_article_with_new_version(
    db: Session,
    article: KnowledgeArticle,
    user_id: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content_reference: Optional[str] = None,
    category_id: Optional[str] = None,
    article_type: Optional[ArticleType] = None,
    visibility: Optional[ArticleVisibility] = None,
    review_due_at: Optional[datetime] = None,
    change_summary: Optional[str] = "Content updated",
) -> KnowledgeArticle:
    """Update article properties and append an immutable sequential version record."""
    has_content_or_title_change = False

    if title and title != article.title:
        article.title = title
        has_content_or_title_change = True

    if summary is not None:
        article.summary = summary

    if content_reference and content_reference != article.content_reference:
        article.content_reference = content_reference
        has_content_or_title_change = True

    if category_id:
        article.category_id = category_id

    if article_type:
        article.article_type = article_type

    if visibility:
        article.visibility = visibility

    if review_due_at:
        if review_due_at.tzinfo is not None:
            review_due_at = review_due_at.replace(tzinfo=None)
        article.review_due_at = review_due_at

    # If title, content, or explicit version change requested, generate new version
    if has_content_or_title_change or change_summary:
        max_ver = db.query(func.max(KnowledgeArticleVersion.version_number)).filter(
            KnowledgeArticleVersion.article_id == article.id,
        ).scalar() or 0

        next_ver = max_ver + 1
        new_version = KnowledgeArticleVersion(
            tenant_id=article.tenant_id,
            article_id=article.id,
            version_number=next_ver,
            title=article.title,
            content_reference=article.content_reference,
            change_summary=change_summary,
            created_by=user_id,
            published_at=datetime.utcnow() if article.status == ArticleStatus.PUBLISHED else None,
        )
        db.add(new_version)

    article.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(article)
    return article


def create_article_relation(
    db: Session,
    tenant_id: str,
    article_id: str,
    related_article_id: str,
    relation_type: ArticleRelationType,
) -> KnowledgeArticleRelation:
    """Link two knowledge articles. Strictly prohibits self-references."""
    if article_id == related_article_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-referencing article relation is prohibited",
        )

    # Verify both articles exist in tenant
    art1 = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == article_id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    art2 = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == related_article_id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not art1 or not art2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both articles not found in tenant",
        )

    existing = db.query(KnowledgeArticleRelation).filter(
        KnowledgeArticleRelation.article_id == article_id,
        KnowledgeArticleRelation.related_article_id == related_article_id,
        KnowledgeArticleRelation.relation_type == relation_type,
    ).first()
    if existing:
        return existing

    rel = KnowledgeArticleRelation(
        tenant_id=tenant_id,
        article_id=article_id,
        related_article_id=related_article_id,
        relation_type=relation_type,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


# ===========================================================================
# 4. Search & Discovery with Privacy-Safe Hashing
# ===========================================================================

def search_knowledge_articles(
    db: Session,
    tenant_id: str,
    user: Any,
    query_str: str,
    category_id: Optional[str] = None,
    article_type: Optional[ArticleType] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[KnowledgeArticle], int]:
    """Search articles with keyword matching, server-side auth, and privacy logging."""
    query = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id,
        KnowledgeArticle.status == ArticleStatus.PUBLISHED,
    )

    if category_id:
        query = query.filter(KnowledgeArticle.category_id == category_id)

    if article_type:
        query = query.filter(KnowledgeArticle.article_type == article_type)

    if query_str and query_str.strip():
        term = f"%{query_str.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(KnowledgeArticle.title).like(term),
                func.lower(KnowledgeArticle.summary).like(term),
                func.lower(KnowledgeArticle.content_reference).like(term),
            )
        )

    candidates = query.order_by(KnowledgeArticle.published_at.desc()).all()

    # Filter candidates strictly by user's access rights
    authorized_articles = [art for art in candidates if user_can_access_article(db, art, user)]

    total_count = len(authorized_articles)
    start_idx = (page - 1) * page_size
    paged = authorized_articles[start_idx : start_idx + page_size]

    # Privacy-preserving search event logging (query string is securely hashed)
    if query_str and query_str.strip():
        q_hash = hashlib.sha256(query_str.strip().lower().encode("utf-8")).hexdigest()
        person_id = getattr(user, "person_id", None)
        evt = KnowledgeSearchEvent(
            tenant_id=tenant_id,
            person_id=person_id,
            query_hash=q_hash,
            result_count=total_count,
            category_filter=category_id,
        )
        db.add(evt)
        db.commit()

    return paged, total_count


# ===========================================================================
# 5. Announcements, Targeting & Audience Scope
# ===========================================================================

def user_matches_announcement_audience(
    db: Session,
    announcement: EmployeeAnnouncement,
    user: Any,
) -> bool:
    """Evaluate whether an announcement should be presented to the calling user."""
    if not user:
        return False

    user_role = getattr(user, "role", "").lower()
    if user_role in ["super_admin", "hr_admin"]:
        return True

    # Check status
    if announcement.status != AnnouncementStatus.PUBLISHED:
        return False

    # Check expiration
    now = datetime.utcnow()
    exp = announcement.expires_at
    if exp:
        if exp.tzinfo is not None:
            exp = exp.replace(tzinfo=None)
        if exp < now:
            return False

    # Check audience rules
    rules = db.query(AnnouncementAudienceRule).filter(
        AnnouncementAudienceRule.announcement_id == announcement.id,
        AnnouncementAudienceRule.tenant_id == announcement.tenant_id,
    ).all()

    if not rules:
        return True  # If no audience rules specified, defaults to all employees

    person_id = getattr(user, "person_id", None)
    engagement = None
    if person_id:
        engagement = db.query(Engagement).filter(Engagement.person_id == person_id).first()

    for r in rules:
        if r.audience_type == AudienceType.ALL_EMPLOYEES:
            return True
        if r.audience_type == AudienceType.ROLE and r.role_reference:
            if user_role == r.role_reference.lower():
                return True
        if engagement:
            if r.audience_type == AudienceType.DEPARTMENT and r.department_id:
                if engagement.department == r.department_id:
                    return True
            if r.audience_type == AudienceType.LOCATION and r.location_reference:
                if engagement.work_location == r.location_reference:
                    return True
            if r.audience_type == AudienceType.MANAGER_TEAM and r.manager_scope:
                # Check if user's reporting manager matches manager_scope
                if engagement.reporting_manager_id == r.manager_scope:
                    return True

    return False


def estimate_announcement_reach(
    db: Session,
    tenant_id: str,
    rules: List[Any],
) -> int:
    """Estimate total target employee reach based on audience configuration."""
    if not rules:
        return db.query(func.count(Person.id)).scalar() or 0

    target_count = 0
    for r in rules:
        if getattr(r, "audience_type", None) == AudienceType.ALL_EMPLOYEES:
            return db.query(func.count(Person.id)).scalar() or 0

        q = db.query(func.count(Engagement.id))
        if getattr(r, "department_id", None):
            q = q.filter(Engagement.department == r.department_id)
        if getattr(r, "location_reference", None):
            q = q.filter(Engagement.work_location == r.location_reference)
        target_count += q.scalar() or 0

    return max(1, target_count)


# ===========================================================================
# 6. Read Receipts & Non-Policy Acknowledgements
# ===========================================================================

def record_announcement_read(
    db: Session,
    tenant_id: str,
    announcement_id: str,
    person_id: str,
) -> AnnouncementReadReceipt:
    """Idempotently record proof-of-read receipt for an announcement."""
    announcement = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == announcement_id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    receipt = db.query(AnnouncementReadReceipt).filter(
        AnnouncementReadReceipt.announcement_id == announcement_id,
        AnnouncementReadReceipt.person_id == person_id,
    ).first()
    if receipt:
        return receipt

    receipt = AnnouncementReadReceipt(
        tenant_id=tenant_id,
        announcement_id=announcement_id,
        person_id=person_id,
        read_at=datetime.utcnow(),
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def record_communication_acknowledgement(
    db: Session,
    tenant_id: str,
    announcement_id: str,
    person_id: str,
    ack_ref: Optional[str] = "EMPLOYEE_SELF_ACK",
) -> CommunicationAcknowledgement:
    """Record non-policy announcement acknowledgement."""
    announcement = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.id == announcement_id,
        EmployeeAnnouncement.tenant_id == tenant_id,
    ).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    if not announcement.acknowledgement_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This announcement does not require an acknowledgement",
        )

    ack = db.query(CommunicationAcknowledgement).filter(
        CommunicationAcknowledgement.announcement_id == announcement_id,
        CommunicationAcknowledgement.person_id == person_id,
    ).first()
    if ack:
        return ack

    ack = CommunicationAcknowledgement(
        tenant_id=tenant_id,
        announcement_id=announcement_id,
        person_id=person_id,
        acknowledged_at=datetime.utcnow(),
        acknowledgement_reference=ack_ref,
    )
    db.add(ack)
    db.commit()
    db.refresh(ack)
    return ack


# ===========================================================================
# 7. Manager Scope & Reporting-Line Communications
# ===========================================================================

def get_manager_team_communications_summary(
    db: Session,
    tenant_id: str,
    manager_person_id: str,
) -> Dict[str, Any]:
    """Calculate aggregate read and acknowledgement metrics for a manager's direct team."""
    manager_user = db.query(User).filter(User.person_id == manager_person_id).first()
    manager_user_id = manager_user.id if manager_user else manager_person_id

    team_engagements = db.query(Engagement).filter(
        Engagement.reporting_manager_id.in_([manager_person_id, manager_user_id]),
    ).all()

    team_person_ids = [e.person_id for e in team_engagements if e.person_id]
    team_size = len(team_person_ids)

    announcements = db.query(EmployeeAnnouncement).filter(
        EmployeeAnnouncement.tenant_id == tenant_id,
        EmployeeAnnouncement.status == AnnouncementStatus.PUBLISHED,
    ).order_by(EmployeeAnnouncement.publish_at.desc()).limit(15).all()

    total_reads = 0
    total_acks = 0
    if team_person_ids:
        total_reads = db.query(func.count(AnnouncementReadReceipt.id)).filter(
            AnnouncementReadReceipt.tenant_id == tenant_id,
            AnnouncementReadReceipt.person_id.in_(team_person_ids),
        ).scalar() or 0

        total_acks = db.query(func.count(CommunicationAcknowledgement.id)).filter(
            CommunicationAcknowledgement.tenant_id == tenant_id,
            CommunicationAcknowledgement.person_id.in_(team_person_ids),
        ).scalar() or 0

    max_possible_reads = max(1, team_size * len(announcements))
    read_rate = round((total_reads / max_possible_reads) * 100, 1)

    ack_required_count = sum(1 for a in announcements if a.acknowledgement_required)
    max_possible_acks = max(1, team_size * ack_required_count)
    ack_rate = round((total_acks / max_possible_acks) * 100, 1) if ack_required_count > 0 else 100.0

    return {
        "manager_person_id": manager_person_id,
        "team_size": team_size,
        "announcements_count": len(announcements),
        "team_read_count": total_reads,
        "team_read_rate_pct": min(100.0, read_rate),
        "team_acknowledgement_count": total_acks,
        "team_acknowledgement_rate_pct": min(100.0, ack_rate),
        "announcements": announcements,
    }


# ===========================================================================
# 8. Communication Preferences Protection
# ===========================================================================

def update_employee_communication_preference(
    db: Session,
    tenant_id: str,
    person_id: str,
    comm_type: CommunicationCategory,
    email_enabled: Optional[bool] = None,
    in_app_enabled: Optional[bool] = None,
    sms_enabled: Optional[bool] = None,
) -> CommunicationPreference:
    """Update employee preference with safety rule: HR/Compliance cannot be fully disabled."""
    pref = db.query(CommunicationPreference).filter(
        CommunicationPreference.tenant_id == tenant_id,
        CommunicationPreference.person_id == person_id,
        CommunicationPreference.communication_type == comm_type,
    ).first()

    if not pref:
        pref = CommunicationPreference(
            tenant_id=tenant_id,
            person_id=person_id,
            communication_type=comm_type,
            email_enabled=True,
            in_app_enabled=True,
            sms_enabled=False,
        )
        db.add(pref)

    # Invariant: Mandatory HR/compliance channels cannot be disabled
    if comm_type == CommunicationCategory.HR:
        if in_app_enabled is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mandatory HR and compliance communications cannot have in-app delivery disabled",
            )

    if email_enabled is not None:
        pref.email_enabled = email_enabled
    if in_app_enabled is not None:
        pref.in_app_enabled = in_app_enabled
    if sms_enabled is not None:
        pref.sms_enabled = sms_enabled

    pref.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pref)
    return pref
