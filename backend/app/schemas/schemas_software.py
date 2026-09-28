"""
schemas_software.py - Pydantic schemas for Software catalog and licenses.
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field

class SoftwareStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"

class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class SoftwareBase(BaseModel):
    name: str
    vendor: Optional[str] = None
    description: Optional[str] = None
    status: SoftwareStatus = SoftwareStatus.ACTIVE

class SoftwareCreate(SoftwareBase):
    pass

class SoftwareUpdate(BaseModel):
    name: Optional[str] = None
    vendor: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SoftwareStatus] = None

class SoftwareOut(SoftwareBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class SoftwareLicenseBase(BaseModel):
    software_id: str
    license_reference: Optional[str] = None
    seat_count: int = Field(..., gt=0)
    cost: Optional[float] = None
    currency: Optional[str] = None
    purchase_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: LicenseStatus = LicenseStatus.ACTIVE
    notes: Optional[str] = None

class SoftwareLicenseCreate(SoftwareLicenseBase):
    pass

class SoftwareLicenseUpdate(BaseModel):
    license_reference: Optional[str] = None
    seat_count: Optional[int] = Field(None, gt=0)
    cost: Optional[float] = None
    currency: Optional[str] = None
    purchase_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: Optional[LicenseStatus] = None
    notes: Optional[str] = None

class SoftwareLicenseOut(SoftwareLicenseBase):
    id: str
    tenant_id: str
    allocated_seats: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class EmployeeLicenseAssignmentBase(BaseModel):
    license_id: str
    person_id: str
    user_id: str
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None

class EmployeeLicenseAssignmentCreate(EmployeeLicenseAssignmentBase):
    pass

class EmployeeLicenseAssignmentOut(EmployeeLicenseAssignmentBase):
    id: str
    tenant_id: str
    assigned_date: datetime
    revoked_date: Optional[datetime] = None
    status: LicenseStatus
    created_at: datetime

    class Config:
        orm_mode = True
