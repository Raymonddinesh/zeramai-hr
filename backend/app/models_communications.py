"""
models_communications.py - Module 20: Enterprise Employee Communications & Knowledge Management

Provides:
- Knowledge categories (hierarchical, cycle-prevented)
- Knowledge articles, versioning (immutable published versions), and relations
- Access rules and server-side authorization
- Knowledge feedback and article view tracking
- Knowledge review tasks and governance integration
- Employee announcements, priority, scheduling, and audience targeting
- Read receipts and communication acknowledgements
- Communication templates and user preferences
- Search events and privacy-safe search analytics
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Enums
# ===========================================================================

class ArticleType(str, enum.Enum):
    ARTICLE = "ARTICLE"
    FAQ = "FAQ"
    HOW_TO = "HOW_TO"
    GUIDE = "GUIDE"
    REFERENCE = "REFERENCE"
    TROUBLESHOOTING = "TROUBLESHOOTING"


class ArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class ArticleVisibility(str, enum.Enum):
    ALL_EMPLOYEES = "ALL_EMPLOYEES"
    MANAGERS = "MANAGERS"
    HR_ONLY = "HR_ONLY"
    CUSTOM_AUDIENCE = "CUSTOM_AUDIENCE"


class AccessRuleType(str, enum.Enum):
    TENANT = "TENANT"
    LEGAL_ENTITY = "LEGAL_ENTITY"
    DEPARTMENT = "DEPARTMENT"
    ORGANIZATION_UNIT = "ORGANIZATION_UNIT"
    LOCATION = "LOCATION"
    ROLE = "ROLE"
    MANAGER = "MANAGER"
    CUSTOM = "CUSTOM"


class ArticleRelationType(str, enum.Enum):
    RELATED = "RELATED"
    PREREQUISITE = "PREREQUISITE"
    NEXT_STEP = "NEXT_STEP"
    SEE_ALSO = "SEE_ALSO"


class KnowledgeFeedbackType(str, enum.Enum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    OUTDATED = "OUTDATED"
    INCORRECT = "INCORRECT"
    MISSING_INFORMATION = "MISSING_INFORMATION"


class ReviewTaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    REQUIRES_UPDATE = "REQUIRES_UPDATE"
    EXPIRED = "EXPIRED"


class AnnouncementType(str, enum.Enum):
    GENERAL = "GENERAL"
    HR = "HR"
    POLICY = "POLICY"
    PAYROLL = "PAYROLL"
    BENEFITS = "BENEFITS"
    COMPLIANCE = "COMPLIANCE"
    IT = "IT"
    SAFETY = "SAFETY"
    EVENT = "EVENT"
    URGENT = "URGENT"
    OTHER = "OTHER"


class AnnouncementPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnnouncementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class AudienceType(str, enum.Enum):
    ALL_EMPLOYEES = "ALL_EMPLOYEES"
    LEGAL_ENTITY = "LEGAL_ENTITY"
    DEPARTMENT = "DEPARTMENT"
    ORGANIZATION_UNIT = "ORGANIZATION_UNIT"
    LOCATION = "LOCATION"
    ROLE = "ROLE"
    MANAGER_TEAM = "MANAGER_TEAM"
    CUSTOM = "CUSTOM"


class CommunicationTemplateType(str, enum.Enum):
    ANNOUNCEMENT = "ANNOUNCEMENT"
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    REMINDER = "REMINDER"
    POLICY_NOTICE = "POLICY_NOTICE"


class CommunicationCategory(str, enum.Enum):
    GENERAL = "GENERAL"
    HR = "HR"
    LEARNING = "LEARNING"
    ENGAGEMENT = "ENGAGEMENT"
    EVENTS = "EVENTS"
    REMINDERS = "REMINDERS"


# ===========================================================================
# Knowledge Base Models
# ===========================================================================

class KnowledgeCategory(Base):
    """Hierarchical category taxonomy for organizing knowledge articles and FAQs."""
    __tablename__ = "knowledge_categories"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    parent_id = Column(String, ForeignKey("knowledge_categories.id"), nullable=True, index=True)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    parent = relationship("KnowledgeCategory", remote_side=[id], backref="children")
    articles = relationship("KnowledgeArticle", back_populates="category", cascade="all, delete-orphan")


class KnowledgeArticle(Base):
    """Canonical knowledge article or FAQ document."""
    __tablename__ = "knowledge_articles"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    category_id = Column(String, ForeignKey("knowledge_categories.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    content_reference = Column(Text, nullable=False)  # Markdown text or document URI
    article_type = Column(Enum(ArticleType), default=ArticleType.ARTICLE, nullable=False, index=True)
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False, index=True)
    visibility = Column(Enum(ArticleVisibility), default=ArticleVisibility.ALL_EMPLOYEES, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    review_due_at = Column(DateTime, nullable=True, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    category = relationship("KnowledgeCategory", back_populates="articles")
    owner = relationship("User", foreign_keys=[owner_user_id])
    versions = relationship("KnowledgeArticleVersion", back_populates="article", cascade="all, delete-orphan", order_by="KnowledgeArticleVersion.version_number.desc()")
    access_rules = relationship("KnowledgeAccessRule", back_populates="article", cascade="all, delete-orphan")
    feedbacks = relationship("KnowledgeFeedback", back_populates="article", cascade="all, delete-orphan")
    views = relationship("KnowledgeArticleView", back_populates="article", cascade="all, delete-orphan")
    review_tasks = relationship("KnowledgeReviewTask", back_populates="article", cascade="all, delete-orphan")


class KnowledgeArticleVersion(Base):
    """Immutable snapshot of published or draft article contents."""
    __tablename__ = "knowledge_article_versions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content_reference = Column(Text, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)

    article = relationship("KnowledgeArticle", back_populates="versions")
    author = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        UniqueConstraint("article_id", "version_number", name="uq_article_version"),
    )


class KnowledgeAccessRule(Base):
    """Server-side fine-grained access authorization rule for custom audience articles."""
    __tablename__ = "knowledge_access_rules"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    rule_type = Column(Enum(AccessRuleType), nullable=False)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    organization_unit_id = Column(String, ForeignKey("organization_units.id"), nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    location_reference = Column(String(128), nullable=True)
    role_reference = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("KnowledgeArticle", back_populates="access_rules")


class KnowledgeArticleRelation(Base):
    """Directed link between articles (related, prerequisite, next steps)."""
    __tablename__ = "knowledge_article_relations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    related_article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    relation_type = Column(Enum(ArticleRelationType), default=ArticleRelationType.RELATED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("KnowledgeArticle", foreign_keys=[article_id])
    related_article = relationship("KnowledgeArticle", foreign_keys=[related_article_id])

    __table_args__ = (
        UniqueConstraint("article_id", "related_article_id", "relation_type", name="uq_article_relation"),
    )


class KnowledgeFeedback(Base):
    """Employee feedback on knowledge articles and FAQs (helpful, outdated, etc.)."""
    __tablename__ = "knowledge_feedbacks"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    feedback_type = Column(Enum(KnowledgeFeedbackType), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("KnowledgeArticle", back_populates="feedbacks")
    person = relationship("Person", foreign_keys=[person_id])


class KnowledgeArticleView(Base):
    """Aggregated view audit records for knowledge articles."""
    __tablename__ = "knowledge_article_views"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_reference = Column(String(128), nullable=True)

    article = relationship("KnowledgeArticle", back_populates="views")
    person = relationship("Person", foreign_keys=[person_id])


class KnowledgeReviewTask(Base):
    """Governance review task ensuring published articles do not become stale."""
    __tablename__ = "knowledge_review_tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    reviewer_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(Enum(ReviewTaskStatus), default=ReviewTaskStatus.PENDING, nullable=False, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("KnowledgeArticle", back_populates="review_tasks")
    reviewer = relationship("User", foreign_keys=[reviewer_user_id])


class KnowledgeSearchEvent(Base):
    """Hashed and privacy-preserving search log for knowledge discovery analytics."""
    __tablename__ = "knowledge_search_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=True, index=True)
    query_hash = Column(String(64), nullable=False, index=True)
    result_count = Column(Integer, default=0, nullable=False)
    category_filter = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ===========================================================================
# Communications & Announcements Models
# ===========================================================================

class EmployeeAnnouncement(Base):
    """Enterprise announcements and broadcast communications."""
    __tablename__ = "employee_announcements"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    content_reference = Column(Text, nullable=False)
    announcement_type = Column(Enum(AnnouncementType), default=AnnouncementType.GENERAL, nullable=False, index=True)
    priority = Column(Enum(AnnouncementPriority), default=AnnouncementPriority.NORMAL, nullable=False, index=True)
    status = Column(Enum(AnnouncementStatus), default=AnnouncementStatus.DRAFT, nullable=False, index=True)
    author_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    publish_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    acknowledgement_required = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    author = relationship("User", foreign_keys=[author_user_id])
    audience_rules = relationship("AnnouncementAudienceRule", back_populates="announcement", cascade="all, delete-orphan")
    read_receipts = relationship("AnnouncementReadReceipt", back_populates="announcement", cascade="all, delete-orphan")
    acknowledgements = relationship("CommunicationAcknowledgement", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementAudienceRule(Base):
    """Audience targeting filter defining recipient scope for announcements."""
    __tablename__ = "announcement_audience_rules"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    announcement_id = Column(String, ForeignKey("employee_announcements.id"), nullable=False, index=True)
    audience_type = Column(Enum(AudienceType), nullable=False)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    organization_unit_id = Column(String, ForeignKey("organization_units.id"), nullable=True)
    location_reference = Column(String(128), nullable=True)
    role_reference = Column(String(128), nullable=True)
    employment_type = Column(String(64), nullable=True)
    manager_scope = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    announcement = relationship("EmployeeAnnouncement", back_populates="audience_rules")


class AnnouncementReadReceipt(Base):
    """Proof-of-read receipt for broadcast announcements."""
    __tablename__ = "announcement_read_receipts"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    announcement_id = Column(String, ForeignKey("employee_announcements.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    announcement = relationship("EmployeeAnnouncement", back_populates="read_receipts")
    person = relationship("Person", foreign_keys=[person_id])

    __table_args__ = (
        UniqueConstraint("announcement_id", "person_id", name="uq_announcement_read"),
    )


class CommunicationAcknowledgement(Base):
    """Non-policy announcement acknowledgement record."""
    __tablename__ = "communication_acknowledgements"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    announcement_id = Column(String, ForeignKey("employee_announcements.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    acknowledged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledgement_reference = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    announcement = relationship("EmployeeAnnouncement", back_populates="acknowledgements")
    person = relationship("Person", foreign_keys=[person_id])

    __table_args__ = (
        UniqueConstraint("announcement_id", "person_id", name="uq_announcement_ack"),
    )


class CommunicationTemplate(Base):
    """Reusable broadcast communication template."""
    __tablename__ = "communication_templates"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    template_type = Column(Enum(CommunicationTemplateType), nullable=False)
    subject_template = Column(String(255), nullable=False)
    body_reference = Column(Text, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    creator = relationship("User", foreign_keys=[created_by])


class CommunicationPreference(Base):
    """Employee notification channel preferences."""
    __tablename__ = "communication_preferences"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    communication_type = Column(Enum(CommunicationCategory), nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person", foreign_keys=[person_id])

    __table_args__ = (
        UniqueConstraint("person_id", "communication_type", name="uq_person_comm_pref"),
    )
