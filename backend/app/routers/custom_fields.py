"""Phase 11 - Dynamic Custom Fields & Form Builder."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v9 import (
    CustomFieldDefinition, CustomFieldValue,
    CustomFieldType,
)

router = APIRouter(prefix="/api/custom-fields", tags=["custom-fields"])


class FieldDefCreate(BaseModel):
    entity_type: str
    name: str
    label: str
    field_type: CustomFieldType = CustomFieldType.TEXT
    options_json: Optional[list[str]] = None
    is_required: bool = False


class FieldDefOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    entity_type: str
    name: str
    label: str
    field_type: CustomFieldType
    options_json: Optional[list[str]]
    is_required: bool
    is_active: bool


class FieldValueUpsert(BaseModel):
    field_definition_id: str
    entity_type: str
    entity_id: str
    value_text: str


@router.post("/definitions", response_model=FieldDefOut, status_code=201)
def create_field_definition(
    payload: FieldDefCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    existing = db.query(CustomFieldDefinition).filter(
        CustomFieldDefinition.entity_type == payload.entity_type,
        CustomFieldDefinition.name == payload.name,
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Custom field already exists for this entity")

    cf = CustomFieldDefinition(**payload.model_dump())
    db.add(cf)
    db.commit()
    db.refresh(cf)
    log_audit(db, user=current_user, action="custom_field_created", entity="custom_field_definition",
              entity_id=cf.id, result=AuditResult.SUCCESS, request=request)
    return cf


@router.get("/definitions/{entity_type}", response_model=list[FieldDefOut])
def list_field_definitions(
    entity_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(CustomFieldDefinition).filter(
        CustomFieldDefinition.entity_type == entity_type,
        CustomFieldDefinition.is_active == True,
    ).all()


@router.post("/values", status_code=200)
def upsert_field_value(
    payload: FieldValueUpsert,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field_def = db.query(CustomFieldDefinition).filter(CustomFieldDefinition.id == payload.field_definition_id).first()
    if not field_def:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Custom field definition not found")

    existing_val = db.query(CustomFieldValue).filter(
        CustomFieldValue.field_definition_id == payload.field_definition_id,
        CustomFieldValue.entity_id == payload.entity_id,
    ).first()

    if existing_val:
        existing_val.value_text = payload.value_text
        val_rec = existing_val
    else:
        val_rec = CustomFieldValue(**payload.model_dump())
        db.add(val_rec)

    db.commit()
    db.refresh(val_rec)
    return {"id": val_rec.id, "entity_id": val_rec.entity_id, "value": val_rec.value_text}


@router.get("/values/{entity_type}/{entity_id}")
def get_entity_custom_values(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vals = db.query(CustomFieldValue).filter(
        CustomFieldValue.entity_type == entity_type,
        CustomFieldValue.entity_id == entity_id,
    ).all()

    results = []
    for v in vals:
        results.append({
            "id": v.id,
            "field_name": v.definition.name if v.definition else None,
            "label": v.definition.label if v.definition else None,
            "field_type": v.definition.field_type if v.definition else None,
            "value": v.value_text,
        })
    return results
