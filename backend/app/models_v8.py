"""
models_v8.py – Phase 9 (Analytics) + Phase 10 (Notifications)

Phase 9:  AnalyticsSnapshot (pre-computed metrics)
Phase 10: NotificationTemplate, Notification, AnnouncementBoard
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum,
    Text, Integer, JSON, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ===========================================================================
# Phase 9 — Analytics & Reporting
# ===========================================================================

class AnalyticsSnapshot(Base):
    """Pre-computed analytics snapshot for dashboard widgets."""
    __tablename__ = "analytics_snapshots"

    id = Column(String, primary_key=True, default=gen_uuid)
    metric_name = Column(String, nullable=False, index=True)  # headcount, attrition_rate, etc.
    metric_value = Column(Float, nullable=False)
    dimension = Column(String, nullable=True)    # department, location, etc.
    dimension_value = Column(String, nullable=True)
    period = Column(String, nullable=False)      # "2026-09", "2026-Q3"
    metadata_json = Column(JSON, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ===========================================================================
# Phase 10 — Notifications & Communication
# ===========================================================================

class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationTemplate(Base):
    """Reusable notification template."""
    __tablename__ = "notification_templates"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)
    subject = Column(String, nullable=False)
    body_template = Column(Text, nullable=False)  # Supports {{variable}} placeholders
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP)
    event_trigger = Column(String, nullable=True)  # e.g. "leave_approved", "payroll_processed"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Notification(Base):
    """Individual notification sent to a user."""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(String, ForeignKey("notification_templates.id"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD)
    action_url = Column(String, nullable=True)    # Deep link
    metadata_json = Column(JSON, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)


class Announcement(Base):
    """Company-wide or department-wide announcements."""
    __tablename__ = "announcements"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)      # company, department, policy
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    target_audience = Column(String, default="all") # all, department:engineering, role:employee
    is_pinned = Column(Boolean, default=False)
    published_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
