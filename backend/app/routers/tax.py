from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit, has_permission
from app.models import AuditResult, User, UserRole, Person
from app.models_v3 import Tenant
from app.models_statutory import TaxDeclaration, TaxDeclarationStatus, TaxRegime
from app.schemas_statutory import (
    TaxDeclarationCreate,
    TaxDeclarationReview,
    TaxDeclarationOut,
)

router = APIRouter(prefix="/api/v3/tax", tags=["tax"])


def _resolve_tenant_id(request: Request, db: Session) -> str:
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(name="Default Tenant", domain="zeramai.com")
        db.add(t)
        db.commit()
    return t.id


def is_hr_or_super(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


@router.get("/declarations", response_model=List[TaxDeclarationOut])
def list_tax_declarations(
    person_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tax declarations. Employees can only access their own. HR/Finance can view all."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "tax:view", db) or has_permission(current_user, "tax:declare", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view tax declarations")

    tenant_id = _resolve_tenant_id(request, db)
    query = db.query(TaxDeclaration).filter(TaxDeclaration.tenant_id == tenant_id)

    is_privileged = is_hr_or_super(current_user) or has_permission(current_user, "tax:manage", db)

    if not is_privileged:
        # Regular employee: restricted to own person_id
        if not current_user.person_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No person profile associated with user")
        if person_id and str(person_id) != str(current_user.person_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot access tax data of another employee")
        query = query.filter(TaxDeclaration.person_id == current_user.person_id)
    elif person_id:
        query = query.filter(TaxDeclaration.person_id == person_id)

    if financial_year:
        query = query.filter(TaxDeclaration.financial_year == financial_year)

    return query.order_by(TaxDeclaration.created_at.desc()).all()


@router.post("/declarations", response_model=TaxDeclarationOut, status_code=status.HTTP_201_CREATED)
def create_tax_declaration(
    payload: TaxDeclarationCreate,
    request: Request,
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit annual tax declaration and regime choice."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "tax:declare", db) or has_permission(current_user, "tax:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to declare taxes")

    tenant_id = _resolve_tenant_id(request, db)

    # Determine target person
    target_person_id = person_id if (person_id and is_hr_or_super(current_user)) else current_user.person_id
    if not target_person_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Target employee person_id required")

    # Check for existing declaration for same FY
    existing = db.query(TaxDeclaration).filter(
        TaxDeclaration.tenant_id == tenant_id,
        TaxDeclaration.person_id == target_person_id,
        TaxDeclaration.financial_year == payload.financial_year,
    ).first()

    if existing:
        # Update existing declaration if still draft
        existing.regime = payload.regime
        existing.projected_income = payload.projected_income
        existing.deductions_json = payload.deductions_json
        existing.documents_json = payload.documents_json
        existing.status = TaxDeclarationStatus.SUBMITTED
        db.commit()
        db.refresh(existing)
        return existing

    decl = TaxDeclaration(
        tenant_id=tenant_id,
        person_id=target_person_id,
        financial_year=payload.financial_year,
        regime=payload.regime,
        projected_income=payload.projected_income,
        deductions_json=payload.deductions_json,
        documents_json=payload.documents_json,
        status=TaxDeclarationStatus.SUBMITTED,
    )
    db.add(decl)
    db.commit()
    db.refresh(decl)

    log_audit(
        db,
        user=current_user,
        action="tax_declaration_submitted",
        entity="tax_declaration",
        entity_id=decl.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"person_id": target_person_id, "fy": payload.financial_year, "regime": payload.regime.value},
    )
    return decl


@router.get("/declarations/{declaration_id}", response_model=TaxDeclarationOut)
def get_tax_declaration(
    declaration_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve specific tax declaration with IDOR and tenant protection."""
    tenant_id = _resolve_tenant_id(request, db)
    decl = db.query(TaxDeclaration).filter(TaxDeclaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tax declaration not found")
    if decl.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")

    # IDOR protection: employee can only see their own
    is_privileged = is_hr_or_super(current_user) or has_permission(current_user, "tax:manage", db)
    if not is_privileged and str(decl.person_id) != str(current_user.person_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized: Cannot access tax declaration of another employee")

    return decl


@router.patch("/declarations/{declaration_id}", response_model=TaxDeclarationOut)
def review_tax_declaration(
    declaration_id: str,
    payload: TaxDeclarationReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """HR/Finance reviews and verifies/rejects an employee's tax declaration. Enforces Anti-Self-Approval."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "tax:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to review tax declarations")

    tenant_id = _resolve_tenant_id(request, db)
    decl = db.query(TaxDeclaration).filter(TaxDeclaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tax declaration not found")
    if decl.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access forbidden")

    # Anti-Self-Approval Protection: User cannot verify their own tax declaration
    if current_user.person_id and str(decl.person_id) == str(current_user.person_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-approval prohibited: Cannot verify your own tax declaration")

    act = payload.action.lower()
    if act in ("approve", "verify"):
        decl.status = TaxDeclarationStatus.VERIFIED
        decl.verified_by_id = current_user.id
        decl.verified_at = datetime.utcnow()
        decl.rejection_reason = None
    elif act == "reject":
        decl.status = TaxDeclarationStatus.REJECTED
        decl.verified_by_id = current_user.id
        decl.verified_at = datetime.utcnow()
        decl.rejection_reason = payload.rejection_reason or "Rejected by tax administrator"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid review action: {payload.action}")

    db.commit()
    db.refresh(decl)

    log_audit(
        db,
        user=current_user,
        action=f"tax_declaration_{decl.status.value}",
        entity="tax_declaration",
        entity_id=decl.id,
        result=AuditResult.SUCCESS,
        request=request,
        metadata={"person_id": decl.person_id, "status": decl.status.value},
    )
    return decl
