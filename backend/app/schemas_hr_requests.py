from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------

class HRRequestCreate(BaseModel):
    category: str
    priority: str = "medium"
    subject: str
    description: str


class HRRequestStatusUpdate(BaseModel):
    status: str


class HRRequestAssign(BaseModel):
    assigned_to_user_id: str


class HRRequestResolve(BaseModel):
    resolution: str


class HRRequestCommentCreate(BaseModel):
    content: str
    is_internal: bool = False  # HR can mark as internal; employees cannot


# ---------------------------------------------------------------------------
# Output — Employee view (no internal notes, no resolution internals)
# ---------------------------------------------------------------------------

class HRRequestCommentOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    author_user_id: str
    content: str
    is_internal: bool
    created_at: datetime


class HRRequestOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    ticket_number: str
    tenant_id: Optional[str] = None
    requester_user_id: str
    category: str
    priority: str
    subject: str
    description: str
    status: str
    assigned_to_user_id: Optional[str]
    resolution: Optional[str]
    closed_at: Optional[datetime]
    sla_due_date: Optional[date]
    first_response_at: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    comments: List[HRRequestCommentOut] = []
