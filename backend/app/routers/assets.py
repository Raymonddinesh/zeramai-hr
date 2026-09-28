"""
routers/assets.py - Asset catalog and asset request/transfer/return endpoints.
"""

import uuid
from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import User, Person, AuditResult
from app.models_asset import AssetCatalog, AssetAssignmentHistory, AssetAssignmentAction, AssetStatus, AssetCondition
from app.models_ess import EmployeeAsset
from app.schemas.schemas_asset import (
    AssetCatalogCreate,
    AssetCatalogUpdate,
    AssetCatalogOut,
    AssetAssignmentHistoryCreate,
    AssetAssignmentHistoryOut,
)

router = APIRouter(prefix="/api/v3/assets", tags=["asset_management"])

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _get_tenant_id(request: Request, current_user: User) -> str:
    # Resolve tenant ID server‑side only
    return request.headers.get("X-Tenant-ID") or getattr(current_user, "tenant_id", None)

def _resolve_person(current_user: User, db: Session) -> Person:
    person = db.query(Person).filter(Person.id == current_user.person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person record not found for user")
    return person

# ---------------------------------------------------------------------------
# Asset Catalog CRUD (admin only)
# ---------------------------------------------------------------------------

@router.post("/catalog", response_model=AssetCatalogOut, status_code=201, dependencies=[Depends(require_permission("asset:manage"))])
def create_asset_catalog(item: AssetCatalogCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    # Ensure uniqueness of asset_tag per tenant – DB constraint will also enforce
    catalog = AssetCatalog(
        tenant_id=tenant_id,
        asset_tag=item.asset_tag,
        name=item.name,
        asset_type=item.asset_type,
        manufacturer=item.manufacturer,
        model=item.model,
        serial_number=item.serial_number,
        purchase_date=item.purchase_date,
        purchase_cost=item.purchase_cost,
        warranty_expiry=item.warranty_expiry,
        vendor=item.vendor,
        location=item.location,
        status=item.status,
        condition=item.condition,
        notes=item.notes,
    )
    db.add(catalog)
    db.commit()
    db.refresh(catalog)

    log_audit(db, user=current_user, action="asset_catalog_created", entity="asset_catalog", entity_id=catalog.id, result=AuditResult.SUCCESS, request=request)
    return catalog

@router.get("/catalog", response_model=List[AssetCatalogOut], dependencies=[Depends(require_permission("asset:view"))])
def list_asset_catalog(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    items = db.query(AssetCatalog).filter(AssetCatalog.tenant_id == tenant_id).all()
    return items

@router.patch("/catalog/{asset_id}", response_model=AssetCatalogOut, dependencies=[Depends(require_permission("asset:manage"))])
def update_asset_catalog(asset_id: str, payload: AssetCatalogUpdate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    asset = db.query(AssetCatalog).filter(AssetCatalog.id == asset_id, AssetCatalog.tenant_id == tenant_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    log_audit(db, user=current_user, action="asset_catalog_updated", entity="asset_catalog", entity_id=asset.id, result=AuditResult.SUCCESS, request=request)
    return asset

@router.delete("/catalog/{asset_id}", status_code=204, dependencies=[Depends(require_permission("asset:manage"))])
def delete_asset_catalog(asset_id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    asset = db.query(AssetCatalog).filter(AssetCatalog.id == asset_id, AssetCatalog.tenant_id == tenant_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()
    log_audit(db, user=current_user, action="asset_catalog_deleted", entity="asset_catalog", entity_id=asset_id, result=AuditResult.SUCCESS, request=request)
    return None

# ---------------------------------------------------------------------------
# Employee‑self‑service asset requests (create workflow instance)
# ---------------------------------------------------------------------------

@router.post("/request", response_model=AssetAssignmentHistoryOut, status_code=201, dependencies=[Depends(require_permission("asset:assign"))])
def request_asset(payload: AssetAssignmentHistoryCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Employee requests an asset assignment.

    The request creates a WorkflowInstance of type ``ASSET_REQUEST`` (defined elsewhere).
    The actual assignment will be performed by an authorized HR/IT admin after approval.
    """
    tenant_id = _get_tenant_id(request, current_user)
    person = _resolve_person(current_user, db)

    # Validate that the referenced asset exists and is available
    asset = db.query(AssetCatalog).filter(AssetCatalog.id == payload.asset_id, AssetCatalog.tenant_id == tenant_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.status != AssetStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Asset is not available for assignment")

    # Create a history record in PENDING state (action = assign)
    history = AssetAssignmentHistory(
        tenant_id=tenant_id,
        asset_id=payload.asset_id,
        employee_person_id=person.id,
        employee_user_id=current_user.id,
        action=AssetAssignmentAction.ASSIGN,
        from_status=asset.status,
        to_status=AssetStatus.ASSIGNED,
        performed_at=datetime.utcnow(),
        performed_by_user_id=current_user.id,
        notes=payload.notes,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    log_audit(db, user=current_user, action="asset_request_submitted", entity="asset_assignment_history", entity_id=history.id, result=AuditResult.SUCCESS, request=request)
    return history

# ---------------------------------------------------------------------------
# Transfer & Return endpoints (admin actions after workflow approval)
# ---------------------------------------------------------------------------

@router.post("/transfer/{history_id}", response_model=AssetAssignmentHistoryOut, dependencies=[Depends(require_permission("asset:transfer"))])
def transfer_asset(history_id: str, new_user_id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    history = db.query(AssetAssignmentHistory).filter(AssetAssignmentHistory.id == history_id, AssetAssignmentHistory.tenant_id == tenant_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Assignment record not found")
    # Ensure current status is ASSIGNED
    if history.to_status != AssetStatus.ASSIGNED:
        raise HTTPException(status_code=400, detail="Only assigned assets can be transferred")
    # Create new transfer history entry
    new_history = AssetAssignmentHistory(
        tenant_id=tenant_id,
        asset_id=history.asset_id,
        employee_person_id=history.employee_person_id,
        employee_user_id=current_user.id,
        action=AssetAssignmentAction.TRANSFER,
        from_status=AssetStatus.ASSIGNED,
        to_status=AssetStatus.ASSIGNED,
        performed_at=datetime.utcnow(),
        performed_by_user_id=current_user.id,
        notes=f"Transferred to user {new_user_id}",
    )
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    log_audit(db, user=current_user, action="asset_transferred", entity="asset_assignment_history", entity_id=new_history.id, result=AuditResult.SUCCESS, request=request)
    return new_history

@router.post("/return/{history_id}", response_model=AssetAssignmentHistoryOut, dependencies=[Depends(require_permission("asset:return"))])
def return_asset(history_id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    history = db.query(AssetAssignmentHistory).filter(AssetAssignmentHistory.id == history_id, AssetAssignmentHistory.tenant_id == tenant_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Assignment record not found")
    if history.to_status != AssetStatus.ASSIGNED:
        raise HTTPException(status_code=400, detail="Only assigned assets can be returned")
    # Create return history entry
    return_history = AssetAssignmentHistory(
        tenant_id=tenant_id,
        asset_id=history.asset_id,
        employee_person_id=history.employee_person_id,
        employee_user_id=current_user.id,
        action=AssetAssignmentAction.RETURN,
        from_status=AssetStatus.ASSIGNED,
        to_status=AssetStatus.AVAILABLE,
        performed_at=datetime.utcnow(),
        performed_by_user_id=current_user.id,
        notes="Asset returned",
    )
    db.add(return_history)
    db.commit()
    db.refresh(return_history)
    log_audit(db, user=current_user, action="asset_returned", entity="asset_assignment_history", entity_id=return_history.id, result=AuditResult.SUCCESS, request=request)
    return return_history

# ---------------------------------------------------------------------------
# View assignment history (self and admin)
# ---------------------------------------------------------------------------

@router.get("/history", response_model=List[AssetAssignmentHistoryOut], dependencies=[Depends(require_permission("asset:view"))])
def list_assignment_history(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenant_id = _get_tenant_id(request, current_user)
    # Employees see only their own history; admins see all for the tenant
    if "HR_ADMIN" in current_user.roles or "SUPER_ADMIN" in current_user.roles:
        histories = db.query(AssetAssignmentHistory).filter(AssetAssignmentHistory.tenant_id == tenant_id).all()
    else:
        histories = db.query(AssetAssignmentHistory).filter(
            AssetAssignmentHistory.tenant_id == tenant_id,
            AssetAssignmentHistory.employee_user_id == current_user.id,
        ).all()
    return histories
