"""
schemas_communications.py - Module 20: Enterprise Employee Communications & Knowledge Management Schemas
Zeramai Enterprise HRMS
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models_communications import (
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
    CommunicationTemplateType,
    CommunicationCategory,
)


# ===========================================================================
# 1. Knowledge Categories
# ===========================================================================

class KnowledgeCategoryBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    display_order: int = 0
    active: bool = True


class KnowledgeCategoryCreate(KnowledgeCategoryBase):
    pass


class KnowledgeCategoryUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    display_order: Optional[int] = None
    active: Optional[bool] = None


class KnowledgeCategoryResponse(KnowledgeCategoryBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    article_count: Optional[int] = 0

    class Config:
        from_attributes = True


class KnowledgeCategoryTreeResponse(KnowledgeCategoryResponse):
    children: List["KnowledgeCategoryTreeResponse"] = []


# ===========================================================================
# 2. Knowledge Articles & Versions
# ===========================================================================

class KnowledgeArticleBase(BaseModel):
    category_id: str
    title: str
    slug: str
    summary: Optional[str] = None
    content_reference: str
    article_type: ArticleType = ArticleType.ARTICLE
    visibility: ArticleVisibility = ArticleVisibility.ALL_EMPLOYEES
    review_due_at: Optional[datetime] = None


class KnowledgeArticleCreate(KnowledgeArticleBase):
    change_summary: Optional[str] = "Initial draft"


class KnowledgeArticleUpdate(BaseModel):
    category_id: Optional[str] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    summary: Optional[str] = None
    content_reference: Optional[str] = None
    article_type: Optional[ArticleType] = None
    visibility: Optional[ArticleVisibility] = None
    review_due_at: Optional[datetime] = None
    change_summary: Optional[str] = None


class KnowledgeArticleVersionResponse(BaseModel):
    id: str
    tenant_id: str
    article_id: str
    version_number: int
    title: str
    content_reference: str
    change_summary: Optional[str] = None
    created_by: str
    created_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeAccessRuleBase(BaseModel):
    rule_type: AccessRuleType
    legal_entity_id: Optional[str] = None
    organization_unit_id: Optional[str] = None
    department_id: Optional[str] = None
    location_reference: Optional[str] = None
    role_reference: Optional[str] = None


class KnowledgeAccessRuleCreate(KnowledgeAccessRuleBase):
    article_id: str


class KnowledgeAccessRuleResponse(KnowledgeAccessRuleBase):
    id: str
    tenant_id: str
    article_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeArticleRelationBase(BaseModel):
    related_article_id: str
    relation_type: ArticleRelationType = ArticleRelationType.RELATED


class KnowledgeArticleRelationCreate(KnowledgeArticleRelationBase):
    article_id: Optional[str] = None


class KnowledgeArticleRelationResponse(KnowledgeArticleRelationBase):
    id: str
    tenant_id: str
    article_id: str
    created_at: datetime
    related_article_title: Optional[str] = None
    related_article_slug: Optional[str] = None

    class Config:
        from_attributes = True


class KnowledgeArticleResponse(BaseModel):
    id: str
    tenant_id: str
    category_id: str
    category_name: Optional[str] = None
    title: str
    slug: str
    summary: Optional[str] = None
    article_type: ArticleType
    status: ArticleStatus
    visibility: ArticleVisibility
    owner_user_id: str
    current_version: Optional[int] = 1
    review_due_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    view_count: Optional[int] = 0
    helpful_count: Optional[int] = 0
    not_helpful_count: Optional[int] = 0

    class Config:
        from_attributes = True


class KnowledgeArticleDetailResponse(KnowledgeArticleResponse):
    content_reference: str
    versions: List[KnowledgeArticleVersionResponse] = []
    access_rules: List[KnowledgeAccessRuleResponse] = []
    related_articles: List[KnowledgeArticleRelationResponse] = []


# ===========================================================================
# 3. Knowledge Feedback & Views
# ===========================================================================

class KnowledgeFeedbackCreate(BaseModel):
    article_id: str
    feedback_type: KnowledgeFeedbackType
    comment: Optional[str] = None


class KnowledgeFeedbackResponse(BaseModel):
    id: str
    tenant_id: str
    article_id: str
    person_id: str
    feedback_type: KnowledgeFeedbackType
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeFeedbackSummary(BaseModel):
    article_id: str
    total_feedback: int
    helpful_count: int
    not_helpful_count: int
    outdated_count: int
    incorrect_count: int
    missing_info_count: int
    helpfulness_percentage: float


class KnowledgeArticleViewCreate(BaseModel):
    session_reference: Optional[str] = None


class KnowledgeArticleViewResponse(BaseModel):
    id: str
    tenant_id: str
    article_id: str
    viewed_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 4. Review Tasks
# ===========================================================================

class KnowledgeReviewTaskCreate(BaseModel):
    article_id: str
    reviewer_user_id: str
    due_at: datetime
    review_notes: Optional[str] = None


class KnowledgeReviewTaskUpdate(BaseModel):
    status: ReviewTaskStatus
    review_notes: Optional[str] = None


class KnowledgeReviewTaskResponse(BaseModel):
    id: str
    tenant_id: str
    article_id: str
    article_title: Optional[str] = None
    reviewer_user_id: str
    reviewer_name: Optional[str] = None
    due_at: datetime
    status: ReviewTaskStatus
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 5. Knowledge Search & Discovery
# ===========================================================================

class KnowledgeSearchResultItem(BaseModel):
    id: str
    title: str
    slug: str
    summary: Optional[str] = None
    category_id: str
    category_name: Optional[str] = None
    article_type: ArticleType
    status: ArticleStatus
    published_at: Optional[datetime] = None
    relevance_score: float = 1.0


class KnowledgeSearchResponse(BaseModel):
    query: str
    category_filter: Optional[str] = None
    total_results: int
    results: List[KnowledgeSearchResultItem]
    page: int
    page_size: int


# ===========================================================================
# 6. Employee Announcements & Audience
# ===========================================================================

class AnnouncementAudienceRuleBase(BaseModel):
    audience_type: AudienceType
    legal_entity_id: Optional[str] = None
    department_id: Optional[str] = None
    organization_unit_id: Optional[str] = None
    location_reference: Optional[str] = None
    role_reference: Optional[str] = None
    employment_type: Optional[str] = None
    manager_scope: Optional[str] = None


class AnnouncementAudienceRuleCreate(AnnouncementAudienceRuleBase):
    announcement_id: Optional[str] = None


class AnnouncementAudienceRuleResponse(AnnouncementAudienceRuleBase):
    id: str
    tenant_id: str
    announcement_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeAnnouncementBase(BaseModel):
    title: str
    summary: Optional[str] = None
    content_reference: str
    announcement_type: AnnouncementType = AnnouncementType.GENERAL
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    acknowledgement_required: bool = False


class EmployeeAnnouncementCreate(EmployeeAnnouncementBase):
    audience_rules: Optional[List[AnnouncementAudienceRuleBase]] = None


class EmployeeAnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content_reference: Optional[str] = None
    announcement_type: Optional[AnnouncementType] = None
    priority: Optional[AnnouncementPriority] = None
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    acknowledgement_required: Optional[bool] = None


class EmployeeAnnouncementResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    summary: Optional[str] = None
    announcement_type: AnnouncementType
    priority: AnnouncementPriority
    status: AnnouncementStatus
    author_user_id: str
    author_name: Optional[str] = None
    publish_at: datetime
    expires_at: Optional[datetime] = None
    acknowledgement_required: bool
    created_at: datetime
    updated_at: datetime
    read_count: Optional[int] = 0
    acknowledgement_count: Optional[int] = 0
    is_read_by_me: Optional[bool] = False
    is_acknowledged_by_me: Optional[bool] = False

    class Config:
        from_attributes = True


class EmployeeAnnouncementDetailResponse(EmployeeAnnouncementResponse):
    content_reference: str
    audience_rules: List[AnnouncementAudienceRuleResponse] = []


# ===========================================================================
# 7. Receipts, Acknowledgements & Preferences
# ===========================================================================

class AnnouncementReadReceiptResponse(BaseModel):
    id: str
    tenant_id: str
    announcement_id: str
    person_id: str
    read_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class CommunicationAcknowledgementCreate(BaseModel):
    announcement_id: str
    acknowledgement_reference: Optional[str] = "EMPLOYEE_SELF_ACK"


class CommunicationAcknowledgementResponse(BaseModel):
    id: str
    tenant_id: str
    announcement_id: str
    person_id: str
    acknowledged_at: datetime
    acknowledgement_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CommunicationTemplateBase(BaseModel):
    name: str
    template_type: CommunicationTemplateType
    subject_template: str
    body_reference: str
    active: bool = True


class CommunicationTemplateCreate(CommunicationTemplateBase):
    pass


class CommunicationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_type: Optional[CommunicationTemplateType] = None
    subject_template: Optional[str] = None
    body_reference: Optional[str] = None
    active: Optional[bool] = None


class CommunicationTemplateResponse(CommunicationTemplateBase):
    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommunicationPreferenceBase(BaseModel):
    communication_type: CommunicationCategory
    email_enabled: bool = True
    in_app_enabled: bool = True
    sms_enabled: bool = False


class CommunicationPreferenceCreate(CommunicationPreferenceBase):
    person_id: Optional[str] = None


class CommunicationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None


class CommunicationPreferenceResponse(CommunicationPreferenceBase):
    id: str
    tenant_id: str
    person_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 8. Dashboards, Audience Reach & Analytics
# ===========================================================================

class AudienceReachEstimateResponse(BaseModel):
    announcement_id: Optional[str] = None
    audience_type: str
    target_count: int
    note: str = "Estimated recipient count based on server-side criteria"


class KnowledgeDashboardResponse(BaseModel):
    total_articles: int
    published_articles: int
    draft_articles: int
    review_queue_count: int
    total_views: int
    overall_helpfulness_pct: float
    total_categories: int
    popular_articles: List[KnowledgeArticleResponse] = []
    recent_articles: List[KnowledgeArticleResponse] = []
    faqs: List[KnowledgeArticleResponse] = []


class CommunicationsDashboardResponse(BaseModel):
    total_announcements: int
    published_announcements: int
    scheduled_announcements: int
    critical_notices_count: int
    overall_read_rate_pct: float
    overall_acknowledgement_rate_pct: float
    active_templates_count: int
    recent_announcements: List[EmployeeAnnouncementResponse] = []


class ManagerTeamCommunicationsResponse(BaseModel):
    manager_person_id: str
    team_size: int
    announcements_count: int
    team_read_count: int
    team_read_rate_pct: float
    team_acknowledgement_count: int
    team_acknowledgement_rate_pct: float
    announcements: List[EmployeeAnnouncementResponse] = []


class KnowledgeSearchAnalytics(BaseModel):
    total_searches: int
    zero_result_searches: int
    top_search_hashes: List[Dict[str, Any]] = []
