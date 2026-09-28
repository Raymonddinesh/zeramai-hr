"""
schemas_it_access.py - Pydantic schemas for IT access requests and provisions.
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field

class ITAccessStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONED = "provisioned"
    REVOKED = "revoked"
    COMPLETED = "completed"

class ITProvisionStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"

class ITAccessRequestBase(BaseModel):
    resource: str
    access_type: str
    requested_role: Optional[str] = None
    business_justification: str
    requested_start_date: Optional[date] = None
    requested_end_date: Optional[date] = None

class ITAccessRequestCreate(ITAccessRequestBase):
    pass

class ITAccessRequestOut(ITAccessRequestBase):
    id: str
    tenant_id: str
    person_id: str
    user_id: str
    status: ITAccessStatus = ITAccessStatus.PENDING
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ITProvisionBase(BaseModel):
    granted_by_user_id: str
    external_reference: Optional[str] = None
    resource_details: Optional[str] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None

class ITProvisionCreate(ITProvisionBase):
    pass

class ITProvisionOut(ITProvisionBase):
    id: str
    tenant_id: str
    access_request_id: str
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    revoked_by_user_id: Optional[str] = None
    status: ITProvisionStatus = ITProvisionStatus.ACTIVE
    created_at: datetime

    class Config:
        orm_mode = True
