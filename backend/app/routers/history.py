from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User, Person
from app.models_v3 import EmploymentHistory, HistoryChangeType

router = APIRouter(prefix="/api/v3/employees", tags=["history"])


class EmploymentHistoryCreate(BaseModel):
    tenant_id: str
    effective_date: date
    change_type: HistoryChangeType
    designation: Optional[str] = None
    department_id: Optional[str] = None
    location_id: Optional[str] = None
    manager_id: Optional[str] = None
    legal_entity_id: Optional[str] = None
    salary_amount: Optional[float] = None
    salary_currency: str = "INR"
    notes: Optional[str] = None


class EmploymentHistoryOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    tenant_id: str
    person_id: str
    effective_date: date
    change_type: HistoryChangeType
    designation: Optional[str]
    salary_amount: Optional[float]
    salary_currency: str


@router.post("/{person_id}/history", response_model=EmploymentHistoryOut, status_code=201)
def record_employment_history(
    person_id: str,
    payload: EmploymentHistoryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:update")),
):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person record not found")

    h = EmploymentHistory(
        tenant_id=payload.tenant_id,
        person_id=person_id,
        effective_date=payload.effective_date,
        change_type=payload.change_type,
        designation=payload.designation,
        department_id=payload.department_id,
        location_id=payload.location_id,
        manager_id=payload.manager_id,
        legal_entity_id=payload.legal_entity_id,
        salary_amount=payload.salary_amount,
        salary_currency=payload.salary_currency,
        notes=payload.notes,
    )
    db.add(h)
    db.commit()
    db.refresh(h)

    log_audit(db, user=current_user, action=f"employment_history_{payload.change_type.value}",
              entity="employment_history", entity_id=h.id, result=AuditResult.SUCCESS, request=request)
    return h


@router.get("/{person_id}/history", response_model=list[EmploymentHistoryOut])
def get_employment_history_timeline(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Enforce object-level access or employees:view
    if current_user.person_id != person_id:
        require_permission("employees:view")(current_user, db)

    return db.query(EmploymentHistory).filter(EmploymentHistory.person_id == person_id)\
             .order_by(EmploymentHistory.effective_date.desc()).all()
