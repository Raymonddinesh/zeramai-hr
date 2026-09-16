from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, has_permission, require_permission
from app.models import Person, User

router = APIRouter(prefix="/api/employees", tags=["employees"])


class PersonOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    full_name: str
    preferred_name: Optional[str]
    email: str
    phone: Optional[str]
    gender: Optional[str]


@router.get("/me", response_model=PersonOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:view_own")),
):
    """Employee/Trainee self-service: view own HR profile (Person record)."""
    if not current_user.person_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No person record linked to this account")
    person = db.query(Person).filter(Person.id == current_user.person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person record not found")
    return person


@router.get("", response_model=list[PersonOut])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:view")),
):
    """HR/Admin: list all person records."""
    return db.query(Person).order_by(Person.full_name).all()
