"""
routers/offboarding.py - Module 5: Offboarding & Exit Management Router.

Endpoints:
- POST /api/v3/offboarding/resignations       (Submit resignation)
- GET  /api/v3/offboarding/my                 (Get own exit request)
- GET  /api/v3/offboarding                    (List exits: HR sees all, Manager sees team)
- GET  /api/v3/offboarding/{id}               (Get exit details with role-based masking)
- POST /api/v3/offboarding/{id}/review        (Manager or HR review & approval)
- POST /api/v3/offboarding/{id}/clearance     (Update clearance task)
- POST /api/v3/offboarding/{id}/handover      (Add handover item)
- POST /api/v3/offboarding/{id}/handover-status (Update handover status)
- POST /api/v3/offboarding/{id}/exit-interview (Submit/record exit interview)
- POST /api/v3/offboarding/{id}/settlement-readiness (Update settlement checklist)
- POST /api/v3/offboarding/{id}/complete      (Complete exit and close employment)
"""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, has_permission, log_audit
from app.models import (
    AuditResult,
    User,
    Person,
    Engagement,
    EngagementStatus,
)
from app.models_v3 import EmploymentHistory, HistoryChangeType
from app.models_offboarding import (
    ExitRequest,
    ExitClearanceTask,
    ExitHandover,
    ExitInterview,
    ExitSettlement,
    ExitStatus,
    ExitClearanceDepartment,
)
from app.schemas_offboarding import (
    ResignationCreate,
    ExitReviewAction,
    ClearanceTaskUpdate,
    HandoverCreate,
    HandoverStatusUpdate,
    ExitInterviewUpdate,
    SettlementReadinessUpdate,
    ExitRequestOut,
    ExitClearanceTaskOut,
    ExitHandoverOut,
    ExitInterviewOut,
    ExitSettlementOut,
)

router = APIRouter(prefix="/api/v3/offboarding", tags=["offboarding"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tenant_id(request: Request, current_user: User) -> Optional[str]:
    return request.headers.get("X-Tenant-ID") or getattr(current_user, "tenant_id", None)


def _generate_ticket_number() -> str:
    return f"EXIT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _is_hr_admin(user: User, db: Session) -> bool:
    return has_permission(user, "offboarding:manage", db) or user.role == "hr_admin" or user.role == "super_admin"


def _is_reporting_manager(manager_user: User, person_id: str, db: Session) -> bool:
    """Checks if manager_user is the reporting manager on an active/recent engagement for person_id."""
    return db.query(Engagement).filter(
        Engagement.person_id == person_id,
        Engagement.reporting_manager_id == manager_user.id,
    ).first() is not None


def _get_manager_team_person_ids(manager_user: User, db: Session) -> List[str]:
    engagements = db.query(Engagement.person_id).filter(
        Engagement.reporting_manager_id == manager_user.id
    ).all()
    return [e[0] for e in engagements]


def _check_tenant(req: ExitRequest, tenant_id: Optional[str]):
    if tenant_id and req.tenant_id and req.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-tenant access denied")


def _format_exit_out(req: ExitRequest, caller: User, is_hr: bool, is_owner: bool) -> ExitRequestOut:
    """Serializes ExitRequestOut, masking sensitive exit interview feedback for non-HR / non-Owner users."""
    interview_out = None
    if req.interview:
        # If manager is viewing (not HR and not Owner), mask confidential feedback
        feedback_comp = req.interview.feedback_company
        feedback_mgmt = req.interview.feedback_management
        feedback_role = req.interview.feedback_role
        if not is_hr and not is_owner:
            feedback_comp = "[Confidential to HR]"
            feedback_mgmt = "[Confidential to HR]"
            feedback_role = "[Confidential to HR]"

        interview_out = ExitInterviewOut(
            id=req.interview.id,
            interview_date=req.interview.interview_date,
            interviewer_user_id=req.interview.interviewer_user_id,
            primary_reason=req.interview.primary_reason,
            feedback_company=feedback_comp,
            feedback_management=feedback_mgmt,
            feedback_role=feedback_role,
            is_completed=req.interview.is_completed,
            completed_at=req.interview.completed_at,
        )

    settlement_out = None
    if req.settlement:
        settlement_out = ExitSettlementOut(
            id=req.settlement.id,
            payroll_reviewed=req.settlement.payroll_reviewed,
            leave_balance_reviewed=req.settlement.leave_balance_reviewed,
            leave_encashment_days=float(req.settlement.leave_encashment_days or 0.0),
            asset_clearance_completed=req.settlement.asset_clearance_completed,
            finance_clearance_completed=req.settlement.finance_clearance_completed,
            settlement_status=req.settlement.settlement_status,
            settlement_amount=float(req.settlement.settlement_amount) if req.settlement.settlement_amount else None,
            remarks=req.settlement.remarks,
            settled_at=req.settlement.settled_at,
        )

    return ExitRequestOut(
        id=req.id,
        ticket_number=req.ticket_number,
        tenant_id=req.tenant_id,
        person_id=req.person_id,
        user_id=req.user_id,
        resignation_date=req.resignation_date,
        proposed_last_working_day=req.proposed_last_working_day,
        approved_last_working_day=req.approved_last_working_day,
        notice_period_days=req.notice_period_days,
        reason_category=req.reason_category,
        employee_comments=req.employee_comments,
        status=req.status.value,
        manager_comments=req.manager_comments,
        hr_comments=req.hr_comments,
        manager_reviewed_by_id=req.manager_reviewed_by_id,
        manager_approved_at=req.manager_approved_at,
        hr_reviewed_by_id=req.hr_reviewed_by_id,
        hr_approved_at=req.hr_approved_at,
        completed_at=req.completed_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        clearance_tasks=[
            ExitClearanceTaskOut(
                id=t.id,
                department=t.department.value,
                task_name=t.task_name,
                is_cleared=t.is_cleared,
                cleared_by_user_id=t.cleared_by_user_id,
                cleared_at=t.cleared_at,
                remarks=t.remarks,
            )
            for t in req.clearance_tasks
        ],
        handovers=[
            ExitHandoverOut(
                id=h.id,
                title=h.title,
                description=h.description,
                recipient_user_id=h.recipient_user_id,
                recipient_name=h.recipient_name,
                documentation_url=h.documentation_url,
                status=h.status,
                completed_at=h.completed_at,
            )
            for h in req.handovers
        ],
        interview=interview_out,
        settlement=settlement_out,
    )


# ---------------------------------------------------------------------------
# 1. Employee Submits Resignation
# ---------------------------------------------------------------------------

@router.post("/resignations", response_model=ExitRequestOut, status_code=201)
def submit_resignation(
    payload: ResignationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submits a new resignation exit request for the authenticated user.
    Server-derives ownership from current_user.
    """
    person_id = current_user.person_id
    if not person_id:
        p = db.query(Person).filter(Person.email == current_user.email).first()
        if not p:
            p = Person(full_name=current_user.email.split("@")[0].replace(".", " ").title(), email=current_user.email)
            db.add(p)
            db.flush()
        current_user.person_id = p.id
        person_id = p.id

    tenant_id = _get_tenant_id(request, current_user)

    # Check for active existing exit request
    existing = db.query(ExitRequest).filter(
        ExitRequest.user_id == current_user.id,
        ExitRequest.status.notin_([ExitStatus.COMPLETED, ExitStatus.CANCELLED]),
    ).first()
    if existing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"An active exit request ({existing.ticket_number}) already exists with status {existing.status.value}",
        )

    # Calculate notice period days
    notice_days = (payload.proposed_last_working_day - payload.resignation_date).days
    if notice_days < 0:
        notice_days = 30

    exit_req = ExitRequest(
        ticket_number=_generate_ticket_number(),
        tenant_id=tenant_id,
        person_id=person_id,
        user_id=current_user.id,
        resignation_date=payload.resignation_date,
        proposed_last_working_day=payload.proposed_last_working_day,
        approved_last_working_day=payload.proposed_last_working_day,
        notice_period_days=notice_days,
        reason_category=payload.reason_category,
        employee_comments=payload.employee_comments,
        status=ExitStatus.SUBMITTED,
    )
    db.add(exit_req)
    db.flush()

    # Initialize default departmental clearance tasks
    default_tasks = [
        (ExitClearanceDepartment.MANAGER, "Knowledge Handover & Project Signoff"),
        (ExitClearanceDepartment.IT, "Software/System Access Revocation & Email Forwarding"),
        (ExitClearanceDepartment.ASSETS, "Laptop, Charger & Hardware Devices Returned"),
        (ExitClearanceDepartment.ADMIN, "ID Badge, Building Access Key & Security Token"),
        (ExitClearanceDepartment.FINANCE, "Expense Reimbursements & Corporate Credit Card"),
        (ExitClearanceDepartment.HR, "Exit Interview & Relieving Documentation Verification"),
    ]
    for dept, task_title in default_tasks:
        task = ExitClearanceTask(
            exit_request_id=exit_req.id,
            department=dept,
            task_name=task_title,
            is_cleared=False,
        )
        db.add(task)

    # Initialize Exit Interview record
    interview = ExitInterview(
        exit_request_id=exit_req.id,
        primary_reason=payload.reason_category,
        is_completed=False,
    )
    db.add(interview)

    # Initialize Settlement Readiness record
    settlement = ExitSettlement(
        exit_request_id=exit_req.id,
        settlement_status="pending",
    )
    db.add(settlement)

    # Update active engagement status to RESIGNED
    engagement = db.query(Engagement).filter(
        Engagement.person_id == current_user.person_id,
        Engagement.status.in_([EngagementStatus.ACTIVE, EngagementStatus.PENDING_JOINING]),
    ).first()
    if engagement:
        engagement.status = EngagementStatus.RESIGNED

    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="resignation_submitted",
        entity="exit_request", entity_id=exit_req.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"ticket_number": exit_req.ticket_number, "resignation_date": str(exit_req.resignation_date)},
    )
    return _format_exit_out(exit_req, current_user, is_hr=_is_hr_admin(current_user, db), is_owner=True)


# ---------------------------------------------------------------------------
# 2. Get Own Exit Request
# ---------------------------------------------------------------------------

@router.get("/my", response_model=ExitRequestOut)
def get_my_exit_request(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the authenticated employee's active or latest exit request."""
    exit_req = (
        db.query(ExitRequest)
        .options(
            joinedload(ExitRequest.clearance_tasks),
            joinedload(ExitRequest.handovers),
            joinedload(ExitRequest.interview),
            joinedload(ExitRequest.settlement),
        )
        .filter(ExitRequest.user_id == current_user.id)
        .order_by(ExitRequest.created_at.desc())
        .first()
    )
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No exit request found for your account")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    return _format_exit_out(exit_req, current_user, is_hr=_is_hr_admin(current_user, db), is_owner=True)


# ---------------------------------------------------------------------------
# 3. List Exit Requests (HR sees all in tenant; Manager sees reporting team)
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ExitRequestOut])
def list_exit_requests(
    request: Request,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _get_tenant_id(request, current_user)
    is_hr = _is_hr_admin(current_user, db)

    q = db.query(ExitRequest).options(
        joinedload(ExitRequest.clearance_tasks),
        joinedload(ExitRequest.handovers),
        joinedload(ExitRequest.interview),
        joinedload(ExitRequest.settlement),
    )
    if tenant_id:
        q = q.filter((ExitRequest.tenant_id == tenant_id) | (ExitRequest.tenant_id.is_(None)))

    if is_hr:
        pass  # HR sees all in tenant
    else:
        # Check if user is a manager with reporting team members
        team_person_ids = _get_manager_team_person_ids(current_user, db)
        if team_person_ids:
            # Manager sees team members + own
            q = q.filter(
                (ExitRequest.person_id.in_(team_person_ids)) | (ExitRequest.user_id == current_user.id)
            )
        else:
            # Regular employee sees only own
            q = q.filter(ExitRequest.user_id == current_user.id)

    if status_filter:
        q = q.filter(ExitRequest.status == status_filter)

    results = q.order_by(ExitRequest.created_at.desc()).all()
    return [
        _format_exit_out(r, current_user, is_hr=is_hr, is_owner=(r.user_id == current_user.id))
        for r in results
    ]


# ---------------------------------------------------------------------------
# 4. Get Single Exit Details
# ---------------------------------------------------------------------------

@router.get("/{exit_id}", response_model=ExitRequestOut)
def get_exit_request(
    exit_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = (
        db.query(ExitRequest)
        .options(
            joinedload(ExitRequest.clearance_tasks),
            joinedload(ExitRequest.handovers),
            joinedload(ExitRequest.interview),
            joinedload(ExitRequest.settlement),
        )
        .filter(ExitRequest.id == exit_id)
        .first()
    )
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    is_hr = _is_hr_admin(current_user, db)
    is_owner = (exit_req.user_id == current_user.id)
    is_mgr = _is_reporting_manager(current_user, exit_req.person_id, db)

    if not (is_hr or is_owner or is_mgr):
        log_audit(
            db, user=current_user, action="denied:exit_request:view",
            entity="exit_request", entity_id=exit_id,
            result=AuditResult.DENIED, request=request,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied to exit record")

    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=is_owner)


# ---------------------------------------------------------------------------
# 5. Review & Approval (Manager or HR)
# ---------------------------------------------------------------------------

@router.post("/{exit_id}/review", response_model=ExitRequestOut)
def review_exit_request(
    exit_id: str,
    payload: ExitReviewAction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    # Employee CANNOT approve/review their own resignation
    if exit_req.user_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Employees cannot approve or review their own resignation",
        )

    is_hr = _is_hr_admin(current_user, db)
    is_mgr = _is_reporting_manager(current_user, exit_req.person_id, db)

    if not (is_hr or is_mgr):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized to review this exit request")

    if is_mgr and not is_hr:
        # Manager review
        if payload.comments:
            exit_req.manager_comments = payload.comments
        exit_req.manager_reviewed_by_id = current_user.id
        if payload.action == "approve":
            exit_req.manager_approved_at = datetime.utcnow()
            exit_req.status = ExitStatus.UNDER_REVIEW
        elif payload.action == "reject":
            exit_req.status = ExitStatus.CANCELLED
    else:
        # HR review / approval
        if payload.comments:
            exit_req.hr_comments = payload.comments
        exit_req.hr_reviewed_by_id = current_user.id
        if payload.approved_last_working_day:
            exit_req.approved_last_working_day = payload.approved_last_working_day

        if payload.action == "approve":
            exit_req.hr_approved_at = datetime.utcnow()
            exit_req.status = ExitStatus.APPROVED
            # Transition engagement to notice period
            eng = db.query(Engagement).filter(
                Engagement.person_id == exit_req.person_id,
                Engagement.status.in_([EngagementStatus.ACTIVE, EngagementStatus.RESIGNED]),
            ).first()
            if eng:
                eng.status = EngagementStatus.NOTICE_PERIOD
                if exit_req.approved_last_working_day:
                    eng.end_date = exit_req.approved_last_working_day
        elif payload.action == "under_review":
            exit_req.status = ExitStatus.UNDER_REVIEW
        elif payload.action == "reject":
            exit_req.status = ExitStatus.CANCELLED

    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="exit_reviewed",
        entity="exit_request", entity_id=exit_id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"action": payload.action, "status": exit_req.status.value},
    )
    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=False)


# ---------------------------------------------------------------------------
# 6. Clearance Task Update
# ---------------------------------------------------------------------------

@router.post("/{exit_id}/clearance", response_model=ExitRequestOut)
def update_clearance_task(
    exit_id: str,
    payload: ClearanceTaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    task = db.query(ExitClearanceTask).filter(
        ExitClearanceTask.id == payload.task_id,
        ExitClearanceTask.exit_request_id == exit_id,
    ).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clearance task not found")

    is_hr = _is_hr_admin(current_user, db)
    is_mgr = _is_reporting_manager(current_user, exit_req.person_id, db)

    # Department-level authorization:
    # - HR can clear any task
    # - Manager can clear MANAGER clearance tasks for their team
    # - Employee CANNOT clear their own departmental tasks
    if exit_req.user_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Departing employee cannot sign off on their own departmental clearance tasks",
        )

    if not is_hr:
        if not (is_mgr and task.department == ExitClearanceDepartment.MANAGER):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Unauthorized to clear this department's task",
            )

    task.is_cleared = payload.is_cleared
    task.cleared_by_user_id = current_user.id if payload.is_cleared else None
    task.cleared_at = datetime.utcnow() if payload.is_cleared else None
    if payload.remarks is not None:
        task.remarks = payload.remarks

    # Check if all tasks are cleared -> advance status if approved
    all_tasks = db.query(ExitClearanceTask).filter(ExitClearanceTask.exit_request_id == exit_id).all()
    if all(t.is_cleared for t in all_tasks) and exit_req.status in [ExitStatus.APPROVED, ExitStatus.NOTICE_PERIOD, ExitStatus.CLEARANCE]:
        exit_req.status = ExitStatus.SETTLEMENT_PENDING

    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="clearance_task_updated",
        entity="exit_clearance_task", entity_id=task.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"is_cleared": payload.is_cleared, "department": task.department.value},
    )
    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=False)


# ---------------------------------------------------------------------------
# 7. Knowledge Handover Management
# ---------------------------------------------------------------------------

@router.post("/{exit_id}/handover", response_model=ExitRequestOut)
def create_handover_item(
    exit_id: str,
    payload: HandoverCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    is_hr = _is_hr_admin(current_user, db)
    is_owner = (exit_req.user_id == current_user.id)
    is_mgr = _is_reporting_manager(current_user, exit_req.person_id, db)

    if not (is_hr or is_owner or is_mgr):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied to add handover")

    handover = ExitHandover(
        exit_request_id=exit_id,
        title=payload.title,
        description=payload.description,
        recipient_user_id=payload.recipient_user_id,
        recipient_name=payload.recipient_name,
        documentation_url=payload.documentation_url,
        status="pending",
    )
    db.add(handover)
    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="handover_created",
        entity="exit_handover", entity_id=handover.id,
        result=AuditResult.SUCCESS, request=request,
    )
    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=is_owner)


@router.post("/{exit_id}/handover-status", response_model=ExitRequestOut)
def update_handover_status(
    exit_id: str,
    payload: HandoverStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    handover = db.query(ExitHandover).filter(
        ExitHandover.id == payload.handover_id,
        ExitHandover.exit_request_id == exit_id,
    ).first()
    if not handover:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Handover item not found")

    is_hr = _is_hr_admin(current_user, db)
    is_owner = (exit_req.user_id == current_user.id)
    is_mgr = _is_reporting_manager(current_user, exit_req.person_id, db)

    if not (is_hr or is_owner or is_mgr):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    handover.status = payload.status
    if payload.status == "completed":
        handover.completed_at = datetime.utcnow()
    else:
        handover.completed_at = None

    db.commit()
    db.refresh(exit_req)
    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=is_owner)


# ---------------------------------------------------------------------------
# 8. Exit Interview (Protected & Confidential)
# ---------------------------------------------------------------------------

@router.post("/{exit_id}/exit-interview", response_model=ExitRequestOut)
def update_exit_interview(
    exit_id: str,
    payload: ExitInterviewUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    is_hr = _is_hr_admin(current_user, db)
    is_owner = (exit_req.user_id == current_user.id)

    # Only employee themselves or HR can submit/modify exit interview
    if not (is_hr or is_owner):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Exit interview is confidential; only the employee or HR can access it",
        )

    interview = db.query(ExitInterview).filter(ExitInterview.exit_request_id == exit_id).first()
    if not interview:
        interview = ExitInterview(exit_request_id=exit_id)
        db.add(interview)

    if payload.primary_reason:
        interview.primary_reason = payload.primary_reason
    if payload.feedback_company is not None:
        interview.feedback_company = payload.feedback_company
    if payload.feedback_management is not None:
        interview.feedback_management = payload.feedback_management
    if payload.feedback_role is not None:
        interview.feedback_role = payload.feedback_role
    if payload.is_completed:
        interview.is_completed = True
        interview.completed_at = datetime.utcnow()
        if is_hr:
            interview.interviewer_user_id = current_user.id

    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="exit_interview_updated",
        entity="exit_interview", entity_id=interview.id,
        result=AuditResult.SUCCESS, request=request,
    )
    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=is_owner)


# ---------------------------------------------------------------------------
# 9. Settlement Readiness Checklist (HR or Finance)
# ---------------------------------------------------------------------------

@router.post("/{exit_id}/settlement-readiness", response_model=ExitRequestOut)
def update_settlement_readiness(
    exit_id: str,
    payload: SettlementReadinessUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    is_hr = _is_hr_admin(current_user, db)
    is_finance = (current_user.role == "finance")
    if not (is_hr or is_finance):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only HR or Finance can update settlement readiness")

    settlement = db.query(ExitSettlement).filter(ExitSettlement.exit_request_id == exit_id).first()
    if not settlement:
        settlement = ExitSettlement(exit_request_id=exit_id)
        db.add(settlement)

    if payload.payroll_reviewed is not None:
        settlement.payroll_reviewed = payload.payroll_reviewed
    if payload.leave_balance_reviewed is not None:
        settlement.leave_balance_reviewed = payload.leave_balance_reviewed
    if payload.leave_encashment_days is not None:
        settlement.leave_encashment_days = payload.leave_encashment_days
    if payload.asset_clearance_completed is not None:
        settlement.asset_clearance_completed = payload.asset_clearance_completed
    if payload.finance_clearance_completed is not None:
        settlement.finance_clearance_completed = payload.finance_clearance_completed
    if payload.settlement_status is not None:
        settlement.settlement_status = payload.settlement_status
        if payload.settlement_status == "processed":
            settlement.settled_at = datetime.utcnow()
    if payload.settlement_amount is not None:
        settlement.settlement_amount = payload.settlement_amount
    if payload.remarks is not None:
        settlement.remarks = payload.remarks

    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="settlement_readiness_updated",
        entity="exit_settlement", entity_id=settlement.id,
        result=AuditResult.SUCCESS, request=request,
    )
    return _format_exit_out(exit_req, current_user, is_hr=is_hr, is_owner=(exit_req.user_id == current_user.id))


# ---------------------------------------------------------------------------
# 10. Complete Exit (HR Only)
# ---------------------------------------------------------------------------

@router.post("/{exit_id}/complete", response_model=ExitRequestOut)
def complete_exit(
    exit_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Finalizes employee offboarding:
    - Sets exit request status to COMPLETED
    - Sets Engagement status to COMPLETED (or TERMINATED)
    - Records HistoryChangeType.EXIT in EmploymentHistory
    """
    if not _is_hr_admin(current_user, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only authorized HR can finalize employee offboarding")

    exit_req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if not exit_req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exit request not found")

    tenant_id = _get_tenant_id(request, current_user)
    _check_tenant(exit_req, tenant_id)

    exit_req.status = ExitStatus.COMPLETED
    exit_req.completed_at = datetime.utcnow()

    # Update active engagement
    engagement = db.query(Engagement).filter(
        Engagement.person_id == exit_req.person_id,
        Engagement.status.in_([EngagementStatus.ACTIVE, EngagementStatus.NOTICE_PERIOD, EngagementStatus.RESIGNED]),
    ).first()
    if engagement:
        engagement.status = EngagementStatus.COMPLETED
        if exit_req.approved_last_working_day:
            engagement.end_date = exit_req.approved_last_working_day

    # Record EXIT in EmploymentHistory if tenant exists
    try:
        hist = EmploymentHistory(
            tenant_id=exit_req.tenant_id or "default",
            person_id=exit_req.person_id,
            effective_date=exit_req.approved_last_working_day or date.today(),
            change_type=HistoryChangeType.EXIT,
            designation=engagement.designation if engagement else None,
            notes=f"Offboarding completed via ticket {exit_req.ticket_number}",
        )
        db.add(hist)
    except Exception:
        pass  # If tenants table constraint or FK is unpopulated, proceed gracefully

    db.commit()
    db.refresh(exit_req)

    log_audit(
        db, user=current_user, action="exit_completed",
        entity="exit_request", entity_id=exit_id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"ticket_number": exit_req.ticket_number},
    )
    return _format_exit_out(exit_req, current_user, is_hr=True, is_owner=(exit_req.user_id == current_user.id))
