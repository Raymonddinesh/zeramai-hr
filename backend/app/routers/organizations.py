from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User, Person
from app.models_v3 import Tenant, LegalEntity, Department, Location

router = APIRouter(prefix="/api/v3/organizations", tags=["organizations"])


class TenantCreate(BaseModel):
    name: str
    domain: str


class TenantOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    name: str
    domain: str
    is_active: bool


class LegalEntityCreate(BaseModel):
    tenant_id: str
    name: str
    country_code: str = "IN"
    default_currency: str = "INR"
    registration_number: Optional[str] = None


class LegalEntityOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    tenant_id: str
    name: str
    country_code: str
    default_currency: str


class DepartmentCreate(BaseModel):
    tenant_id: str
    legal_entity_id: str
    name: str
    parent_department_id: Optional[str] = None
    manager_id: Optional[str] = None


class DepartmentOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    tenant_id: str
    legal_entity_id: str
    name: str
    parent_department_id: Optional[str]


@router.post("/tenants", response_model=TenantOut, status_code=201)
def create_tenant(
    payload: TenantCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    existing = db.query(Tenant).filter(Tenant.domain == payload.domain).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Domain already registered to another tenant")

    t = Tenant(name=payload.name, domain=payload.domain)
    db.add(t)
    db.commit()
    db.refresh(t)
    log_audit(db, user=current_user, action="tenant_created", entity="tenant", entity_id=t.id, result=AuditResult.SUCCESS, request=request)
    return t


@router.post("/legal-entities", response_model=LegalEntityOut, status_code=201)
def create_legal_entity(
    payload: LegalEntityCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    le = LegalEntity(
        tenant_id=payload.tenant_id,
        name=payload.name,
        country_code=payload.country_code.upper(),
        default_currency=payload.default_currency.upper(),
        registration_number=payload.registration_number,
    )
    db.add(le)
    db.commit()
    db.refresh(le)
    log_audit(db, user=current_user, action="legal_entity_created", entity="legal_entity", entity_id=le.id, result=AuditResult.SUCCESS, request=request)
    return le


@router.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:update")),
):
    dept = Department(
        tenant_id=payload.tenant_id,
        legal_entity_id=payload.legal_entity_id,
        name=payload.name,
        parent_department_id=payload.parent_department_id,
        manager_id=payload.manager_id,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit(db, user=current_user, action="department_created", entity="department", entity_id=dept.id, result=AuditResult.SUCCESS, request=request)
    return dept


@router.get("/org-chart")
def get_org_chart(
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:view")),
):
    """Returns organizational department tree & employee count breakdown."""
    departments = db.query(Department).all()
    persons = db.query(Person).all()

    dept_tree = [
        {
            "id": d.id,
            "name": d.name,
            "parent_id": d.parent_department_id,
            "legal_entity_id": d.legal_entity_id,
        }
        for d in departments
    ]

    return {
        "total_employees": len(persons),
        "total_departments": len(departments),
        "departments": dept_tree,
    }
