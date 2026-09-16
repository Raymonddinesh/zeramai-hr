"""Phase 10 – Notifications & Communication."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v8 import (
    NotificationTemplate, Notification, Announcement,
    NotificationChannel, NotificationStatus, NotificationPriority,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_template: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    event_trigger: Optional[str] = None

class NotifCreate(BaseModel):
    user_id: str
    title: str
    message: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: NotificationPriority = NotificationPriority.MEDIUM
    action_url: Optional[str] = None

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.MEDIUM
    target_audience: str = "all"
    is_pinned: bool = False


# ── Templates ───────────────────────────────────────────────────────────

@router.post("/templates", status_code=201)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    tmpl = NotificationTemplate(**payload.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return {"id": tmpl.id, "name": tmpl.name}

@router.get("/templates")
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:view")),
):
    return [{"id": t.id, "name": t.name, "subject": t.subject, "channel": t.channel}
            for t in db.query(NotificationTemplate).filter(NotificationTemplate.is_active == True).all()]


# ── Notifications ───────────────────────────────────────────────────────

@router.post("/send", status_code=201)
def send_notification(
    payload: NotifCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    notif = Notification(**payload.model_dump())
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return {"id": notif.id, "title": notif.title, "status": notif.status}


@router.get("/inbox")
def get_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.status != NotificationStatus.ARCHIVED,
    ).order_by(Notification.sent_at.desc()).limit(50).all()
    return [
        {"id": n.id, "title": n.title, "message": n.message,
         "priority": n.priority, "status": n.status, "sent_at": n.sent_at.isoformat()}
        for n in notifs
    ]


@router.patch("/{notif_id}/read")
def mark_read(
    notif_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.id == notif_id, Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    notif.status = NotificationStatus.READ
    notif.read_at = datetime.utcnow()
    db.commit()
    return {"id": notif_id, "status": "read"}


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.status == NotificationStatus.UNREAD,
    ).count()
    return {"unread_count": count}


# ── Announcements ───────────────────────────────────────────────────────

@router.post("/announcements", status_code=201)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    ann = Announcement(**payload.model_dump(), published_by_id=current_user.id)
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return {"id": ann.id, "title": ann.title}


@router.get("/announcements")
def list_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    anns = db.query(Announcement).filter(Announcement.is_active == True).order_by(
        Announcement.is_pinned.desc(), Announcement.published_at.desc()
    ).limit(20).all()
    return [
        {"id": a.id, "title": a.title, "content": a.content,
         "category": a.category, "priority": a.priority,
         "is_pinned": a.is_pinned, "published_at": a.published_at.isoformat()}
        for a in anns
    ]
