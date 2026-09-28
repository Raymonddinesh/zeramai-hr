"""
HR Service Desk router — /api/v3/hr-requests

Security:
- Employee: create own requests, view own requests, add non-internal comments
- HR/Admin: view all requests, assign, change status, resolve, add internal notes
- Ownership derived server-side from authenticated user (never from client input)
- Internal HR comments hidden from employees
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import (
    AuditResult,
    User,
    HRRequest,
    HRRequestComment,
    HRRequestCategory,
    HRRequestPriority,
    HRRequestStatus,
)
from app.schemas_hr_requests import (
    HRRequestCreate,
    HRRequestOut,
    HRRequestCommentCreate,
    HRRequestCommentOut,
    HRRequestStatusUpdate,
    HRRequestAssign,
    HRRequestResolve,
)

router = APIRouter(prefix="/api/v3/hr-requests", tags=["hr_service_desk"])


def _generate_ticket_number() -> str:
    return f"HR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _is_hr_user(user: User, db: Session) -> bool:
    """Check if user has HR service desk management permission."""
    return has_permission(user, "hr_requests:manage", db)


def _filter_comments_for_employee(comments, user: User, db: Session):
    """Strip internal HR comments if the user is not an HR manager."""
    if _is_hr_user(user, db):
        return comments
    return [c for c in comments if not c.is_internal]


def _get_tenant_id(request: Request, current_user: User) -> Optional[str]:
    return request.headers.get("X-Tenant-ID") or getattr(current_user, "tenant_id", None)


def _request_to_out(req: HRRequest, user: User, db: Session) -> HRRequestOut:
    """Convert model to output, filtering internal comments for employees."""
    filtered = _filter_comments_for_employee(req.comments, user, db)
    return HRRequestOut(
        id=req.id,
        ticket_number=req.ticket_number,
        tenant_id=req.tenant_id,
        requester_user_id=req.requester_user_id,
        category=req.category.value,
        priority=req.priority.value,
        subject=req.subject,
        description=req.description,
        status=req.status.value,
        assigned_to_user_id=req.assigned_to_user_id,
        resolution=req.resolution,
        closed_at=req.closed_at,
        sla_due_date=req.sla_due_date,
        first_response_at=req.first_response_at,
        resolved_at=req.resolved_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        comments=[
            HRRequestCommentOut(
                id=c.id,
                author_user_id=c.author_user_id,
                content=c.content,
                is_internal=c.is_internal,
                created_at=c.created_at,
            )
            for c in filtered
        ],
    )


# ---------------------------------------------------------------------------
# Employee: Create request
# ---------------------------------------------------------------------------

@router.post("", response_model=HRRequestOut, status_code=201)
def create_hr_request(
    payload: HRRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Any authenticated user can create an HR request. Ownership is server-derived."""
    # Validate category & priority enums
    try:
        cat = HRRequestCategory(payload.category)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid category: {payload.category}")
    try:
        pri = HRRequestPriority(payload.priority)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid priority: {payload.priority}")

    tenant_id = _get_tenant_id(request, current_user)
    req = HRRequest(
        ticket_number=_generate_ticket_number(),
        tenant_id=tenant_id,
        requester_user_id=current_user.id,  # Server-derived ownership
        category=cat,
        priority=pri,
        subject=payload.subject,
        description=payload.description,
        status=HRRequestStatus.OPEN,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit(
        db, user=current_user, action="hr_request_created",
        entity="hr_request", entity_id=req.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"ticket_number": req.ticket_number, "category": payload.category},
    )
    return _request_to_out(req, current_user, db)


# ---------------------------------------------------------------------------
# List requests (employee: own only; HR: all with filters)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[HRRequestOut])
def list_hr_requests(
    request: Request,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Employee: sees only own requests (filters ignored for scope, applied within own).
    HR: sees all requests with optional filters.
    """
    q = db.query(HRRequest).options(joinedload(HRRequest.comments))

    tenant_id = _get_tenant_id(request, current_user)
    if tenant_id:
        q = q.filter((HRRequest.tenant_id == tenant_id) | (HRRequest.tenant_id.is_(None)))

    if _is_hr_user(current_user, db):
        pass  # HR sees all within tenant
    else:
        # Employee: only own requests
        q = q.filter(HRRequest.requester_user_id == current_user.id)

    if status_filter:
        q = q.filter(HRRequest.status == status_filter)
    if category_filter:
        q = q.filter(HRRequest.category == category_filter)
    if priority_filter:
        q = q.filter(HRRequest.priority == priority_filter)

    requests = q.order_by(HRRequest.created_at.desc()).all()
    return [_request_to_out(r, current_user, db) for r in requests]


# ---------------------------------------------------------------------------
# Get single request
# ---------------------------------------------------------------------------

@router.get("/{request_id}", response_model=HRRequestOut)
def get_hr_request(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Employee can view own request. HR can view any request."""
    req = (
        db.query(HRRequest)
        .options(joinedload(HRRequest.comments))
        .filter(HRRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HR request not found")

    tenant_id = _get_tenant_id(request, current_user)
    if tenant_id and req.tenant_id and req.tenant_id != tenant_id:
        log_audit(
            db, user=current_user, action="denied:hr_request:cross_tenant",
            entity="hr_request", entity_id=request_id,
            result=AuditResult.DENIED, request=request,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access denied")

    # Authorization: employee can only see own
    if not _is_hr_user(current_user, db) and req.requester_user_id != current_user.id:
        log_audit(
            db, user=current_user, action="denied:hr_request:view",
            entity="hr_request", entity_id=request_id,
            result=AuditResult.DENIED, request=request,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    return _request_to_out(req, current_user, db)


# ---------------------------------------------------------------------------
# Assign request (HR only)
# ---------------------------------------------------------------------------

@router.post("/{request_id}/assign", response_model=HRRequestOut)
def assign_hr_request(
    request_id: str,
    payload: HRRequestAssign,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_hr_user(current_user, db):
        log_audit(
            db, user=current_user, action="denied:hr_request:assign",
            entity="hr_request", entity_id=request_id,
            result=AuditResult.DENIED, request=request,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    req = db.query(HRRequest).options(joinedload(HRRequest.comments)).filter(HRRequest.id == request_id).first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HR request not found")

    tenant_id = _get_tenant_id(request, current_user)
    if tenant_id and req.tenant_id and req.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access denied")

    # Verify assignee exists
    assignee = db.query(User).filter(User.id == payload.assigned_to_user_id).first()
    if not assignee:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee user not found")

    req.assigned_to_user_id = payload.assigned_to_user_id
    if req.status == HRRequestStatus.OPEN:
        req.status = HRRequestStatus.ASSIGNED
    if not req.first_response_at:
        req.first_response_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db, user=current_user, action="hr_request_assigned",
        entity="hr_request", entity_id=request_id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"assigned_to": payload.assigned_to_user_id},
    )
    return _request_to_out(req, current_user, db)


# ---------------------------------------------------------------------------
# Change status (HR only, except employee can close RESOLVED requests)
# ---------------------------------------------------------------------------

@router.post("/{request_id}/status", response_model=HRRequestOut)
def change_hr_request_status(
    request_id: str,
    payload: HRRequestStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(HRRequest).options(joinedload(HRRequest.comments)).filter(HRRequest.id == request_id).first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HR request not found")

    tenant_id = _get_tenant_id(request, current_user)
    if tenant_id and req.tenant_id and req.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access denied")

    try:
        new_status = HRRequestStatus(payload.status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid status: {payload.status}")

    # Employee can only close their own resolved request
    if not _is_hr_user(current_user, db):
        if req.requester_user_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
        if new_status != HRRequestStatus.CLOSED or req.status != HRRequestStatus.RESOLVED:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Employees can only close their own resolved requests"
            )

    old_status = req.status.value
    req.status = new_status
    if new_status == HRRequestStatus.RESOLVED:
        req.resolved_at = datetime.utcnow()
    if new_status == HRRequestStatus.CLOSED:
        req.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db, user=current_user, action="hr_request_status_changed",
        entity="hr_request", entity_id=request_id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"old_status": old_status, "new_status": payload.status},
    )
    return _request_to_out(req, current_user, db)


# ---------------------------------------------------------------------------
# Resolve request (HR only)
# ---------------------------------------------------------------------------

@router.post("/{request_id}/resolve", response_model=HRRequestOut)
def resolve_hr_request(
    request_id: str,
    payload: HRRequestResolve,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_hr_user(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    req = db.query(HRRequest).options(joinedload(HRRequest.comments)).filter(HRRequest.id == request_id).first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HR request not found")

    tenant_id = _get_tenant_id(request, current_user)
    if tenant_id and req.tenant_id and req.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access denied")

    req.status = HRRequestStatus.RESOLVED
    req.resolution = payload.resolution
    req.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db, user=current_user, action="hr_request_resolved",
        entity="hr_request", entity_id=request_id,
        result=AuditResult.SUCCESS, request=request,
    )
    return _request_to_out(req, current_user, db)


# ---------------------------------------------------------------------------
# Add comment
# ---------------------------------------------------------------------------

@router.post("/{request_id}/comments", response_model=HRRequestCommentOut, status_code=201)
def add_comment(
    request_id: str,
    payload: HRRequestCommentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(HRRequest).filter(HRRequest.id == request_id).first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HR request not found")

    tenant_id = _get_tenant_id(request, current_user)
    if tenant_id and req.tenant_id and req.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access denied")

    is_hr = _is_hr_user(current_user, db)

    # Employee can only comment on own requests, and cannot create internal comments
    if not is_hr:
        if req.requester_user_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
        if payload.is_internal:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Employees cannot create internal HR notes"
            )

    comment = HRRequestComment(
        hr_request_id=request_id,
        author_user_id=current_user.id,
        content=payload.content,
        is_internal=payload.is_internal if is_hr else False,
    )
    db.add(comment)

    # Track first response for SLA
    if is_hr and not req.first_response_at:
        req.first_response_at = datetime.utcnow()

    db.commit()
    db.refresh(comment)

    log_audit(
        db, user=current_user, action="hr_request_comment_added",
        entity="hr_request_comment", entity_id=comment.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"hr_request_id": request_id, "is_internal": comment.is_internal},
    )
    return HRRequestCommentOut(
        id=comment.id,
        author_user_id=comment.author_user_id,
        content=comment.content,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )
