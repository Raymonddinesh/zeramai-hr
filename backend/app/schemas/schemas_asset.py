"""
schemas_asset.py - Pydantic schemas for Asset Catalog and Assignment History.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field

# Enums must match the SQLAlchemy enums for validation
class AssetStatus(str, Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    LOST = "lost"

class AssetCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"

class AssetCatalogBase(BaseModel):
    asset_tag: str = Field(..., description="Unique tag for the asset within a tenant")
    name: str
    asset_type: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[str] = None
    warranty_expiry: Optional[date] = None
    vendor: Optional[str] = None
    location: Optional[str] = None
    status: AssetStatus = AssetStatus.AVAILABLE
    condition: AssetCondition = AssetCondition.NEW
    notes: Optional[str] = None

class AssetCatalogCreate(AssetCatalogBase):
    pass

class AssetCatalogUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[str] = None
    warranty_expiry: Optional[date] = None
    vendor: Optional[str] = None
    location: Optional[str] = None
    status: Optional[AssetStatus] = None
    condition: Optional[AssetCondition] = None
    notes: Optional[str] = None

class AssetCatalogOut(AssetCatalogBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Assignment history schemas
class AssetAssignmentHistoryBase(BaseModel):
    asset_id: str
    employee_person_id: Optional[str] = None
    employee_user_id: Optional[str] = None
    action: str = Field(..., description="assign | transfer | return")
    from_status: Optional[AssetStatus] = None
    to_status: AssetStatus
    performed_at: datetime = Field(default_factory=datetime.utcnow)
    performed_by_user_id: str
    notes: Optional[str] = None
    previous_employee_person_id: Optional[str] = None
    new_employee_person_id: Optional[str] = None
    previous_location: Optional[str] = None
    new_location: Optional[str] = None

class AssetAssignmentHistoryCreate(AssetAssignmentHistoryBase):
    pass

class AssetAssignmentHistoryOut(AssetAssignmentHistoryBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        orm_mode = True
