"""
knowledge.py - Module 20: Enterprise Knowledge Base & FAQ Router
Prefix: /api/v3/knowledge
Zeramai Enterprise HRMS
"""
from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.deps import get_current_user, require_permission
from app.models import User, Person, Engagement, Tenant
from app.models_communications import (
    KnowledgeCategory,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeAccessRule,
    KnowledgeArticleRelation,
    KnowledgeFeedback,
    KnowledgeArticleView,
    KnowledgeReviewTask,
    ArticleType,
    ArticleStatus,
    ArticleVisibility,
    AccessRuleType,
    ArticleRelationType,
    KnowledgeFeedbackType,
    ReviewTaskStatus,
)
from app.schemas_communications import (
    KnowledgeCategoryCreate,
    KnowledgeCategoryUpdate,
    KnowledgeCategoryResponse,
    KnowledgeCategoryTreeResponse,
    KnowledgeArticleCreate,
    KnowledgeArticleUpdate,
    KnowledgeArticleResponse,
    KnowledgeArticleDetailResponse,
    KnowledgeArticleVersionResponse,
    KnowledgeAccessRuleCreate,
    KnowledgeAccessRuleResponse,
    KnowledgeArticleRelationCreate,
    KnowledgeArticleRelationResponse,
    KnowledgeFeedbackCreate,
    KnowledgeFeedbackResponse,
    KnowledgeFeedbackSummary,
    KnowledgeArticleViewCreate,
    KnowledgeArticleViewResponse,
    KnowledgeReviewTaskCreate,
    KnowledgeReviewTaskUpdate,
    KnowledgeReviewTaskResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResultItem,
    KnowledgeDashboardResponse,
)
from app.services import communications_service

router = APIRouter(prefix="/api/v3/knowledge", tags=["Knowledge Management"])


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


def _format_article_detail(article: KnowledgeArticle, db: Session):
    max_v = db.query(func.max(KnowledgeArticleVersion.version_number)).filter(
        KnowledgeArticleVersion.article_id == article.id,
    ).scalar() or 1
    views = db.query(func.count(KnowledgeArticleView.id)).filter(
        KnowledgeArticleView.article_id == article.id,
    ).scalar() or 0
    helpful = db.query(func.count(KnowledgeFeedback.id)).filter(
        KnowledgeFeedback.article_id == article.id,
        KnowledgeFeedback.feedback_type == KnowledgeFeedbackType.HELPFUL,
    ).scalar() or 0
    not_helpful = db.query(func.count(KnowledgeFeedback.id)).filter(
        KnowledgeFeedback.article_id == article.id,
        KnowledgeFeedback.feedback_type == KnowledgeFeedbackType.NOT_HELPFUL,
    ).scalar() or 0

    return {
        "id": article.id,
        "tenant_id": article.tenant_id,
        "category_id": article.category_id,
        "category_name": article.category.name if article.category else None,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "content_reference": article.content_reference,
        "article_type": article.article_type,
        "status": article.status,
        "visibility": article.visibility,
        "owner_user_id": article.owner_user_id,
        "current_version": max_v,
        "review_due_at": article.review_due_at,
        "published_at": article.published_at,
        "archived_at": article.archived_at,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
        "view_count": views,
        "helpful_count": helpful,
        "not_helpful_count": not_helpful,
        "versions": article.versions,
        "access_rules": article.access_rules,
        "related_articles": article.relations if hasattr(article, "relations") else [],
    }


# ===========================================================================
# 1. Knowledge Categories
# ===========================================================================

@router.get("/categories", response_model=List[Any])
def list_categories(
    request: Request,
    tree: bool = Query(False, description="Return as hierarchical tree if true"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List knowledge categories for current tenant, optionally as a nested tree."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    if tree:
        return communications_service.get_category_tree_data(db, tenant_id)

    categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.tenant_id == tenant_id,
        KnowledgeCategory.active == True,
    ).order_by(KnowledgeCategory.display_order.asc(), KnowledgeCategory.name.asc()).all()

    res = []
    for c in categories:
        art_count = db.query(func.count(KnowledgeArticle.id)).filter(
            KnowledgeArticle.category_id == c.id,
            KnowledgeArticle.status == ArticleStatus.PUBLISHED,
        ).scalar() or 0
        res.append({
            "id": c.id,
            "tenant_id": c.tenant_id,
            "code": c.code,
            "name": c.name,
            "description": c.description,
            "parent_id": c.parent_id,
            "display_order": c.display_order,
            "active": c.active,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "article_count": art_count,
        })
    return res


@router.post("/categories", response_model=KnowledgeCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    request: Request,
    payload: KnowledgeCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Create a new knowledge category with circular reference prevention."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    if payload.parent_id:
        communications_service.validate_category_hierarchy(db, tenant_id, None, payload.parent_id)

    # Check unique code in tenant
    existing = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.tenant_id == tenant_id,
        func.lower(KnowledgeCategory.code) == payload.code.lower(),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category code already exists in tenant")

    cat = KnowledgeCategory(
        tenant_id=tenant_id,
        code=payload.code.upper(),
        name=payload.name,
        description=payload.description,
        parent_id=payload.parent_id,
        display_order=payload.display_order,
        active=payload.active,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/categories/{id}", response_model=KnowledgeCategoryResponse)
def get_category(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve single category by ID."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cat = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.id == id,
        KnowledgeCategory.tenant_id == tenant_id,
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return cat


@router.put("/categories/{id}", response_model=KnowledgeCategoryResponse)
def update_category(
    id: str,
    request: Request,
    payload: KnowledgeCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Update category properties and hierarchy with circular reference checks."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    cat = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.id == id,
        KnowledgeCategory.tenant_id == tenant_id,
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if payload.parent_id is not None:
        communications_service.validate_category_hierarchy(db, tenant_id, id, payload.parent_id)
        cat.parent_id = payload.parent_id

    if payload.code:
        cat.code = payload.code.upper()
    if payload.name:
        cat.name = payload.name
    if payload.description is not None:
        cat.description = payload.description
    if payload.display_order is not None:
        cat.display_order = payload.display_order
    if payload.active is not None:
        cat.active = payload.active

    cat.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cat)
    return cat


# ===========================================================================
# 2. Knowledge Articles & Versions
# ===========================================================================

@router.get("/articles", response_model=List[KnowledgeArticleResponse])
def list_articles(
    request: Request,
    category_id: Optional[str] = None,
    article_type: Optional[ArticleType] = None,
    status_filter: Optional[ArticleStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List knowledge articles authorized for current user."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id)

    if category_id:
        q = q.filter(KnowledgeArticle.category_id == category_id)
    if article_type:
        q = q.filter(KnowledgeArticle.article_type == article_type)
    if status_filter:
        q = q.filter(KnowledgeArticle.status == status_filter)

    candidates = q.order_by(KnowledgeArticle.updated_at.desc()).all()
    accessible = [art for art in candidates if communications_service.user_can_access_article(db, art, current_user)]

    res = []
    for a in accessible:
        max_v = db.query(func.max(KnowledgeArticleVersion.version_number)).filter(
            KnowledgeArticleVersion.article_id == a.id,
        ).scalar() or 1
        views = db.query(func.count(KnowledgeArticleView.id)).filter(
            KnowledgeArticleView.article_id == a.id,
        ).scalar() or 0
        helpful = db.query(func.count(KnowledgeFeedback.id)).filter(
            KnowledgeFeedback.article_id == a.id,
            KnowledgeFeedback.feedback_type == KnowledgeFeedbackType.HELPFUL,
        ).scalar() or 0
        not_helpful = db.query(func.count(KnowledgeFeedback.id)).filter(
            KnowledgeFeedback.article_id == a.id,
            KnowledgeFeedback.feedback_type == KnowledgeFeedbackType.NOT_HELPFUL,
        ).scalar() or 0

        res.append({
            "id": a.id,
            "tenant_id": a.tenant_id,
            "category_id": a.category_id,
            "category_name": a.category.name if a.category else None,
            "title": a.title,
            "slug": a.slug,
            "summary": a.summary,
            "article_type": a.article_type,
            "status": a.status,
            "visibility": a.visibility,
            "owner_user_id": a.owner_user_id,
            "current_version": max_v,
            "review_due_at": a.review_due_at,
            "published_at": a.published_at,
            "archived_at": a.archived_at,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "view_count": views,
            "helpful_count": helpful,
            "not_helpful_count": not_helpful,
        })
    return res


@router.post("/articles", response_model=KnowledgeArticleDetailResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    request: Request,
    payload: KnowledgeArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Create a new knowledge article draft and its initial immutable version 1."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = communications_service.create_article_with_version(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        category_id=payload.category_id,
        title=payload.title,
        slug=payload.slug,
        summary=payload.summary,
        content_reference=payload.content_reference,
        article_type=payload.article_type,
        visibility=payload.visibility,
        review_due_at=payload.review_due_at,
        change_summary=payload.change_summary or "Initial draft",
        status_val=ArticleStatus.DRAFT,
    )
    return _format_article_detail(article, db)


@router.get("/articles/{id}", response_model=KnowledgeArticleDetailResponse)
def get_article(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full article contents, versions, and relations. Enforces server-side access and logs view."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    if not communications_service.user_can_access_article(db, article, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this knowledge article",
        )

    # Log view audit event if user is an employee
    person_id = getattr(current_user, "person_id", None)
    if person_id:
        view_log = KnowledgeArticleView(
            tenant_id=tenant_id,
            article_id=article.id,
            person_id=person_id,
            viewed_at=datetime.utcnow(),
        )
        db.add(view_log)
        db.commit()

    return _format_article_detail(article, db)



@router.put("/articles/{id}", response_model=KnowledgeArticleDetailResponse)
def update_article(
    id: str,
    request: Request,
    payload: KnowledgeArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Update article and automatically append a new sequential immutable version record."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    updated = communications_service.update_article_with_new_version(
        db=db,
        article=article,
        user_id=current_user.id,
        title=payload.title,
        summary=payload.summary,
        content_reference=payload.content_reference,
        category_id=payload.category_id,
        article_type=payload.article_type,
        visibility=payload.visibility,
        review_due_at=payload.review_due_at,
        change_summary=payload.change_summary or "Article content updated",
    )
    return _format_article_detail(updated, db)


@router.post("/articles/{id}/publish", response_model=KnowledgeArticleResponse)
def publish_article(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.publish")),
):
    """Publish an approved or drafted article."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    article.status = ArticleStatus.PUBLISHED
    article.published_at = datetime.utcnow()
    article.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{id}/archive", response_model=KnowledgeArticleResponse)
def archive_article(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Archive an article to remove it from general employee search."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    article.status = ArticleStatus.ARCHIVED
    article.archived_at = datetime.utcnow()
    article.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(article)
    return article


@router.get("/articles/{id}/versions", response_model=List[KnowledgeArticleVersionResponse])
def get_article_versions(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve immutable version history for an article."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    if not communications_service.user_can_access_article(db, article, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    versions = db.query(KnowledgeArticleVersion).filter(
        KnowledgeArticleVersion.article_id == id,
        KnowledgeArticleVersion.tenant_id == tenant_id,
    ).order_by(KnowledgeArticleVersion.version_number.desc()).all()
    return versions


# ===========================================================================
# 3. Access Rules & Related Articles
# ===========================================================================

@router.post("/articles/{id}/access-rules", response_model=KnowledgeAccessRuleResponse, status_code=status.HTTP_201_CREATED)
def add_access_rule(
    id: str,
    request: Request,
    payload: KnowledgeAccessRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Add a targeted audience access rule to an article."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    rule = KnowledgeAccessRule(
        tenant_id=tenant_id,
        article_id=id,
        rule_type=payload.rule_type,
        legal_entity_id=payload.legal_entity_id,
        organization_unit_id=payload.organization_unit_id,
        department_id=payload.department_id,
        location_reference=payload.location_reference,
        role_reference=payload.role_reference,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/articles/{id}/related", response_model=KnowledgeArticleRelationResponse, status_code=status.HTTP_201_CREATED)
def link_related_article(
    id: str,
    request: Request,
    payload: KnowledgeArticleRelationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Link two knowledge articles. Strictly prohibits self-references."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    return communications_service.create_article_relation(
        db=db,
        tenant_id=tenant_id,
        article_id=id,
        related_article_id=payload.related_article_id,
        relation_type=payload.relation_type,
    )


# ===========================================================================
# 4. Knowledge Feedback
# ===========================================================================

@router.post("/articles/{id}/feedback", response_model=KnowledgeFeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_article_feedback(
    id: str,
    request: Request,
    payload: KnowledgeFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit employee feedback on a knowledge article."""
    person_id = getattr(current_user, "person_id", None)
    if not person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only employees can submit article feedback")

    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    feedback = KnowledgeFeedback(
        tenant_id=tenant_id,
        article_id=id,
        person_id=person_id,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/articles/{id}/feedback-summary", response_model=KnowledgeFeedbackSummary)
def get_article_feedback_summary(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated feedback metrics for an article without exposing individual feedback authors."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    feedbacks = db.query(KnowledgeFeedback).filter(
        KnowledgeFeedback.article_id == id,
        KnowledgeFeedback.tenant_id == tenant_id,
    ).all()

    total = len(feedbacks)
    helpful = sum(1 for f in feedbacks if f.feedback_type == KnowledgeFeedbackType.HELPFUL)
    not_helpful = sum(1 for f in feedbacks if f.feedback_type == KnowledgeFeedbackType.NOT_HELPFUL)
    outdated = sum(1 for f in feedbacks if f.feedback_type == KnowledgeFeedbackType.OUTDATED)
    incorrect = sum(1 for f in feedbacks if f.feedback_type == KnowledgeFeedbackType.INCORRECT)
    missing = sum(1 for f in feedbacks if f.feedback_type == KnowledgeFeedbackType.MISSING_INFORMATION)

    pct = round((helpful / total * 100), 1) if total > 0 else 100.0

    return {
        "article_id": id,
        "total_feedback": total,
        "helpful_count": helpful,
        "not_helpful_count": not_helpful,
        "outdated_count": outdated,
        "incorrect_count": incorrect,
        "missing_info_count": missing,
        "helpfulness_percentage": pct,
    }


# ===========================================================================
# 5. Search
# ===========================================================================

@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    request: Request,
    q: str = Query("", description="Keyword search query"),
    category_id: Optional[str] = Query(None, description="Category filter"),
    article_type: Optional[ArticleType] = Query(None, description="Article type filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search knowledge articles. Strictly excludes unauthorized articles and securely hashes search queries."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    results, total_count = communications_service.search_knowledge_articles(
        db=db,
        tenant_id=tenant_id,
        user=current_user,
        query_str=q,
        category_id=category_id,
        article_type=article_type,
        page=page,
        page_size=page_size,
    )

    items = []
    for a in results:
        items.append({
            "id": a.id,
            "title": a.title,
            "slug": a.slug,
            "summary": a.summary,
            "category_id": a.category_id,
            "category_name": a.category.name if a.category else None,
            "article_type": a.article_type,
            "status": a.status,
            "published_at": a.published_at,
            "relevance_score": 1.0,
        })

    return {
        "query": q,
        "category_filter": category_id,
        "total_results": total_count,
        "results": items,
        "page": page,
        "page_size": page_size,
    }


# ===========================================================================
# 6. Review Tasks
# ===========================================================================

@router.get("/reviews", response_model=List[KnowledgeReviewTaskResponse])
def list_review_tasks(
    request: Request,
    status_filter: Optional[ReviewTaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.review")),
):
    """List knowledge article review tasks."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    q = db.query(KnowledgeReviewTask).filter(
        KnowledgeReviewTask.tenant_id == tenant_id,
    )
    if status_filter:
        q = q.filter(KnowledgeReviewTask.status == status_filter)

    tasks = q.order_by(KnowledgeReviewTask.due_at.asc()).all()
    res = []
    for t in tasks:
        res.append({
            "id": t.id,
            "tenant_id": t.tenant_id,
            "article_id": t.article_id,
            "article_title": t.article.title if t.article else None,
            "reviewer_user_id": t.reviewer_user_id,
            "reviewer_name": t.reviewer.email if t.reviewer else None,
            "due_at": t.due_at,
            "status": t.status,
            "reviewed_at": t.reviewed_at,
            "review_notes": t.review_notes,
            "created_at": t.created_at,
        })
    return res


@router.post("/reviews", response_model=KnowledgeReviewTaskResponse, status_code=status.HTTP_201_CREATED)
def create_review_task(
    request: Request,
    payload: KnowledgeReviewTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.manage")),
):
    """Schedule an article review task."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    article = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.id == payload.article_id,
        KnowledgeArticle.tenant_id == tenant_id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    task = KnowledgeReviewTask(
        tenant_id=tenant_id,
        article_id=payload.article_id,
        reviewer_user_id=payload.reviewer_user_id,
        due_at=payload.due_at,
        review_notes=payload.review_notes,
        status=ReviewTaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "article_id": task.article_id,
        "article_title": article.title,
        "reviewer_user_id": task.reviewer_user_id,
        "due_at": task.due_at,
        "status": task.status,
        "reviewed_at": task.reviewed_at,
        "review_notes": task.review_notes,
        "created_at": task.created_at,
    }


@router.put("/reviews/{id}", response_model=KnowledgeReviewTaskResponse)
def update_review_task(
    id: str,
    request: Request,
    payload: KnowledgeReviewTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge.review")),
):
    """Complete or update a review task."""
    tenant_id = _resolve_tenant_id(request, db, current_user)
    task = db.query(KnowledgeReviewTask).filter(
        KnowledgeReviewTask.id == id,
        KnowledgeReviewTask.tenant_id == tenant_id,
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review task not found")

    task.status = payload.status
    task.reviewed_at = datetime.utcnow()
    if payload.review_notes:
        task.review_notes = payload.review_notes

    # If marked REQUIRES_UPDATE, update article status
    if payload.status == ReviewTaskStatus.REQUIRES_UPDATE and task.article:
        task.article.status = ArticleStatus.IN_REVIEW

    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "article_id": task.article_id,
        "article_title": task.article.title if task.article else None,
        "reviewer_user_id": task.reviewer_user_id,
        "due_at": task.due_at,
        "status": task.status,
        "reviewed_at": task.reviewed_at,
        "review_notes": task.review_notes,
        "created_at": task.created_at,
    }


# ===========================================================================
# 7. Knowledge Hub Dashboard
# ===========================================================================

@router.get("/dashboard", response_model=KnowledgeDashboardResponse)
def get_knowledge_hub_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Knowledge base dashboard metrics and curated articles."""
    tenant_id = _resolve_tenant_id(request, db, current_user)

    total_articles = db.query(func.count(KnowledgeArticle.id)).filter(
        KnowledgeArticle.tenant_id == tenant_id,
    ).scalar() or 0

    published_articles = db.query(func.count(KnowledgeArticle.id)).filter(
        KnowledgeArticle.tenant_id == tenant_id,
        KnowledgeArticle.status == ArticleStatus.PUBLISHED,
    ).scalar() or 0

    draft_articles = db.query(func.count(KnowledgeArticle.id)).filter(
        KnowledgeArticle.tenant_id == tenant_id,
        KnowledgeArticle.status == ArticleStatus.DRAFT,
    ).scalar() or 0

    review_queue = db.query(func.count(KnowledgeReviewTask.id)).filter(
        KnowledgeReviewTask.tenant_id == tenant_id,
        KnowledgeReviewTask.status == ReviewTaskStatus.PENDING,
    ).scalar() or 0

    total_views = db.query(func.count(KnowledgeArticleView.id)).filter(
        KnowledgeArticleView.tenant_id == tenant_id,
    ).scalar() or 0

    total_categories = db.query(func.count(KnowledgeCategory.id)).filter(
        KnowledgeCategory.tenant_id == tenant_id,
        KnowledgeCategory.active == True,
    ).scalar() or 0

    feedbacks = db.query(KnowledgeFeedback).filter(KnowledgeFeedback.tenant_id == tenant_id).all()
    helpful = sum(1 for f in feedbacks if f.feedback_type == KnowledgeFeedbackType.HELPFUL)
    overall_helpfulness = round((helpful / len(feedbacks) * 100), 1) if feedbacks else 100.0

    # Published articles visible to user
    published = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id,
        KnowledgeArticle.status == ArticleStatus.PUBLISHED,
    ).order_by(KnowledgeArticle.published_at.desc()).all()

    accessible = [a for a in published if communications_service.user_can_access_article(db, a, current_user)]

    recent = accessible[:5]
    faqs = [a for a in accessible if a.article_type == ArticleType.FAQ][:5]

    return {
        "total_articles": total_articles,
        "published_articles": published_articles,
        "draft_articles": draft_articles,
        "review_queue_count": review_queue,
        "total_views": total_views,
        "overall_helpfulness_pct": overall_helpfulness,
        "total_categories": total_categories,
        "popular_articles": accessible[:5],
        "recent_articles": recent,
        "faqs": faqs,
    }
