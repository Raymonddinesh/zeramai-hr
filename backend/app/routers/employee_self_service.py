"""
routers/employee_self_service.py - Module 6: Employee Self-Service (ESS) Expansion Router.

Base prefix: /api/v3/me

Endpoints:
- GET   /api/v3/me                  (Aggregated Employee Dashboard)
- PATCH /api/v3/me/profile          (Update self-service permitted contact/address fields)
- GET   /api/v3/me/assets           (View own assigned company assets)
- GET   /api/v3/me/expenses         (View own expense claims)
- POST  /api/v3/me/expenses         (Submit new expense claim)
- GET   /api/v3/me/documents        (View own employee documents)
- GET   /api/v3/me/payroll          (View own payslips)
- GET   /api/v3/me/attendance       (View own attendance records)
- GET   /api/v3/me/leave            (View own leave balances and requests)
"""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import (
    AuditResult,
    User,
    Person,
    Engagement,
    Document,
    Attendance,
    LeaveRequest,
)
from app.models_v6 import Payslip, LeaveBalance, LeavePolicy, SalaryStructure
from app.models_v7 import OKRObjective, PerformanceReview, Enrollment, TrainingCertificate
from app.models_hr_requests import HRRequest
from app.models_offboarding import ExitRequest
from app.models_ess import EmployeeAsset, ExpenseClaim
from app.models_compensation import BenefitEnrollment

from app.schemas_ess import (
    EmployeeProfileOut,
    ProfileUpdateRequest,
    AssetItemOut,
    ExpenseClaimCreate,
    ExpenseClaimOut,
    AttendanceRecordOut,
    LeaveSummaryOut,
    LeaveBalanceItemOut,
    LeaveRequestItemOut,
    PayslipSummaryOut,
    DocumentItemOut,
    PerformanceSummaryOut,
    OKRObjectiveSummaryOut,
    LearningSummaryOut,
    HRRequestSummaryOut,
    OffboardingSummaryOut,
    EmployeeDashboardOut,
)

router = APIRouter(prefix="/api/v3/me", tags=["employee_self_service"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tenant_id(request: Request, current_user: User) -> Optional[str]:
    return request.headers.get("X-Tenant-ID") or getattr(current_user, "tenant_id", None)


def _resolve_person(current_user: User, db: Session) -> Person:
    """Ensures current_user is linked to a Person record; auto-resolves if missing."""
    person = None
    if current_user.person_id:
        person = db.query(Person).filter(Person.id == current_user.person_id).first()

    if not person:
        person = db.query(Person).filter(Person.email == current_user.email).first()
        if not person:
            person = Person(
                full_name=current_user.email.split("@")[0].replace(".", " ").title(),
                email=current_user.email,
            )
            db.add(person)
            db.flush()
        current_user.person_id = person.id
        db.commit()

    return person


# ---------------------------------------------------------------------------
# 1. Aggregated Employee Dashboard
# ---------------------------------------------------------------------------

@router.get("", response_model=EmployeeDashboardOut)
def get_employee_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the comprehensive Employee Self-Service dashboard for the authenticated user.
    Server-derives identity strictly from session.
    """
    tenant_id = _get_tenant_id(request, current_user)
    person = _resolve_person(current_user, db)

    # 1. Profile & Engagement
    engagement = (
        db.query(Engagement)
        .filter(Engagement.person_id == person.id)
        .order_by(Engagement.start_date.desc())
        .first()
    )

    manager_name = None
    if engagement and engagement.reporting_manager_id:
        mgr = db.query(User).filter(User.id == engagement.reporting_manager_id).first()
        if mgr:
            mgr_person = db.query(Person).filter(Person.id == mgr.person_id).first() if mgr.person_id else None
            manager_name = mgr_person.full_name if mgr_person else mgr.email

    profile_out = EmployeeProfileOut(
        id=person.id,
        user_id=current_user.id,
        full_name=person.full_name,
        preferred_name=person.preferred_name,
        email=person.email,
        phone=person.phone,
        gender=person.gender,
        date_of_birth=person.date_of_birth,
        current_address=person.current_address,
        permanent_address=person.permanent_address,
        emergency_contact=person.emergency_contact,
        designation=engagement.designation if engagement else None,
        department=engagement.department if engagement else None,
        engagement_type=engagement.engagement_type.value if engagement else None,
        start_date=engagement.start_date if engagement else None,
        reporting_manager_id=engagement.reporting_manager_id if engagement else None,
        reporting_manager_name=manager_name,
        work_location=engagement.work_location if engagement else None,
        status=engagement.status.value if engagement else "active",
    )

    # 2. Attendance (own records only)
    attendance_records = (
        db.query(Attendance)
        .filter(Attendance.person_id == person.id)
        .order_by(Attendance.date.desc())
        .limit(10)
        .all()
    )
    attendance_out = [
        AttendanceRecordOut(
            id=a.id,
            date=a.date,
            status=a.status.value if hasattr(a.status, 'value') else str(a.status),
            check_in=a.check_in,
            check_out=a.check_out,
            notes=a.notes,
        )
        for a in attendance_records
    ]

    # 3. Leave (own balances & requests)
    leave_balances = (
        db.query(LeaveBalance)
        .filter(LeaveBalance.person_id == person.id)
        .all()
    )
    balance_items = []
    for lb in leave_balances:
        policy = db.query(LeavePolicy).filter(LeavePolicy.id == lb.leave_policy_id).first()
        balance_items.append(
            LeaveBalanceItemOut(
                policy_name=policy.name if policy else "Leave",
                leave_type=policy.leave_type if policy else "casual",
                balance=float(lb.balance or 0.0),
            )
        )

    leave_requests = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.person_id == person.id)
        .order_by(LeaveRequest.start_date.desc())
        .limit(5)
        .all()
    )
    request_items = [
        LeaveRequestItemOut(
            id=lr.id,
            start_date=lr.start_date,
            end_date=lr.end_date,
            leave_type=lr.leave_type,
            status=lr.status.value if hasattr(lr.status, 'value') else str(lr.status),
            reason=lr.reason,
        )
        for lr in leave_requests
    ]
    leave_out = LeaveSummaryOut(balances=balance_items, recent_requests=request_items)

    # 4. Payroll / Payslips (own records only)
    payslips = (
        db.query(Payslip)
        .filter(Payslip.person_id == person.id)
        .order_by(Payslip.created_at.desc())
        .limit(6)
        .all()
    )
    payslips_out = [
        PayslipSummaryOut(
            id=p.id,
            month=p.month if hasattr(p, 'month') and p.month else str(p.created_at.strftime("%Y-%m")),
            gross_pay=float(getattr(p, 'gross_salary', 0.0) or 0.0),
            total_deductions=float(p.total_deductions or 0.0),
            net_pay=float(getattr(p, 'net_salary', 0.0) or 0.0),
        )
        for p in payslips
    ]

    # 5. Documents (own records only)
    documents = (
        db.query(Document)
        .filter(Document.person_id == person.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    documents_out = [
        DocumentItemOut(
            id=d.id,
            document_type=d.document_type,
            file_name=d.file_name,
            status=d.status.value if hasattr(d.status, 'value') else str(d.status),
            upload_date=d.upload_date or d.created_at,
        )
        for d in documents
    ]

    # 6. Performance (own OKRs & review status)
    okrs = (
        db.query(OKRObjective)
        .filter(OKRObjective.person_id == person.id)
        .all()
    )
    okrs_out = [
        OKRObjectiveSummaryOut(
            id=o.id,
            title=o.title,
            progress_percentage=float(getattr(o, 'progress_pct', 0.0) or 0.0),
            status=o.status.value if hasattr(o.status, 'value') else str(o.status),
        )
        for o in okrs
    ]
    latest_review = (
        db.query(PerformanceReview)
        .filter(PerformanceReview.person_id == person.id)
        .order_by(PerformanceReview.created_at.desc())
        .first()
    )
    review_rating_str = None
    if latest_review:
        r = latest_review.final_rating or latest_review.manager_rating or latest_review.self_rating
        if r:
            review_rating_str = r.value if hasattr(r, 'value') else str(r)
    performance_out = PerformanceSummaryOut(objectives=okrs_out, latest_review_rating=review_rating_str)

    # 7. Learning / LMS
    enrollments_count = db.query(Enrollment).filter(Enrollment.person_id == person.id).count()
    completed_courses_count = (
        db.query(Enrollment)
        .filter(
            Enrollment.person_id == person.id,
            (Enrollment.status == "completed") | (Enrollment.progress_pct >= 100),
        )
        .count()
    )
    certs_count = db.query(TrainingCertificate).filter(TrainingCertificate.person_id == person.id).count()
    learning_out = LearningSummaryOut(
        enrolled_courses_count=enrollments_count,
        completed_courses_count=completed_courses_count,
        certificates_count=certs_count,
    )

    # 8. Assets (assigned to employee)
    assets = (
        db.query(EmployeeAsset)
        .filter(
            (EmployeeAsset.person_id == person.id) | (EmployeeAsset.user_id == current_user.id)
        )
        .all()
    )
    assets_out = [
        AssetItemOut(
            id=a.id,
            asset_name=a.asset_name,
            asset_type=a.asset_type,
            serial_number=a.serial_number,
            assigned_date=a.assigned_date,
            return_status=a.return_status,
        )
        for a in assets
    ]

    # 9. Expenses (own claims)
    expenses = (
        db.query(ExpenseClaim)
        .filter(ExpenseClaim.user_id == current_user.id)
        .order_by(ExpenseClaim.created_at.desc())
        .all()
    )
    expenses_out = [
        ExpenseClaimOut(
            id=e.id,
            ticket_number=e.ticket_number,
            category=e.category,
            amount=float(e.amount),
            currency=e.currency,
            description=e.description,
            merchant=e.merchant,
            receipt_url=e.receipt_url,
            status=e.status,
            created_at=e.created_at,
        )
        for e in expenses
    ]

    # 10. HR Service Desk Requests (Module 4 integration)
    hr_requests = (
        db.query(HRRequest)
        .filter(HRRequest.requester_user_id == current_user.id)
        .order_by(HRRequest.created_at.desc())
        .limit(5)
        .all()
    )
    hr_requests_out = [
        HRRequestSummaryOut(
            id=hr.id,
            ticket_number=hr.ticket_number,
            category=hr.category.value if hasattr(hr.category, 'value') else str(hr.category),
            priority=hr.priority.value if hasattr(hr.priority, 'value') else str(hr.priority),
            subject=hr.subject,
            status=hr.status.value if hasattr(hr.status, 'value') else str(hr.status),
            created_at=hr.created_at,
        )
        for hr in hr_requests
    ]

    # 11. Offboarding Exit (Module 5 integration)
    exit_req = (
        db.query(ExitRequest)
        .filter(ExitRequest.user_id == current_user.id)
        .order_by(ExitRequest.created_at.desc())
        .first()
    )
    offboarding_out = None
    if exit_req:
        offboarding_out = OffboardingSummaryOut(
            id=exit_req.id,
            ticket_number=exit_req.ticket_number,
            status=exit_req.status.value if hasattr(exit_req.status, 'value') else str(exit_req.status),
            resignation_date=exit_req.resignation_date,
            proposed_last_working_day=exit_req.proposed_last_working_day,
            approved_last_working_day=exit_req.approved_last_working_day,
        )

    # 12. Compensation Summary (Module 7 integration)
    active_ss = db.query(SalaryStructure).filter(
        SalaryStructure.person_id == person.id,
        SalaryStructure.is_active == True,
    ).first()
    comp_out = None
    if active_ss:
        comp_out = {
            "ctc_annual": float(active_ss.ctc_annual),
            "ctc_monthly": float(active_ss.ctc_monthly),
            "currency": active_ss.currency or "INR",
            "effective_from": str(active_ss.effective_from),
            "components": active_ss.components_json or [],
        }

    # 13. Benefits Enrolled (Module 7 integration)
    enrollments = db.query(BenefitEnrollment).filter(
        BenefitEnrollment.person_id == person.id,
        BenefitEnrollment.status == "enrolled",
    ).all()
    benefits_out = []
    for be in enrollments:
        plan = be.benefit_plan
        benefits_out.append({
            "id": be.id,
            "plan_name": plan.name if plan else None,
            "benefit_type": plan.benefit_type if plan else None,
            "provider": plan.provider if plan else None,
            "coverage_tier": be.coverage_tier,
            "employee_contribution": float(be.employee_contribution),
            "employer_contribution": float(be.employer_contribution),
            "effective_date": str(be.effective_date),
            "status": be.status,
        })

    log_audit(
        db, user=current_user, action="ess_dashboard_viewed",
        entity="person", entity_id=person.id,
        result=AuditResult.SUCCESS, request=request,
    )

    return EmployeeDashboardOut(
        profile=profile_out,
        attendance=attendance_out,
        leave=leave_out,
        payslips=payslips_out,
        documents=documents_out,
        performance=performance_out,
        learning=learning_out,
        assets=assets_out,
        expenses=expenses_out,
        hr_requests=hr_requests_out,
        offboarding=offboarding_out,
        compensation=comp_out,
        benefits=benefits_out,
    )



# ---------------------------------------------------------------------------
# 2. Update Self-Service Profile Fields
# ---------------------------------------------------------------------------

@router.patch("/profile", response_model=EmployeeProfileOut)
def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Employee self-service update of permitted contact & personal fields.
    Master data fields (email, full_name, designation, salary) cannot be modified.
    """
    person = _resolve_person(current_user, db)

    changes = {}
    if payload.phone is not None:
        person.phone = payload.phone
        changes["phone"] = payload.phone
    if payload.preferred_name is not None:
        person.preferred_name = payload.preferred_name
        changes["preferred_name"] = payload.preferred_name
    if payload.current_address is not None:
        person.current_address = payload.current_address
        changes["current_address"] = payload.current_address
    if payload.permanent_address is not None:
        person.permanent_address = payload.permanent_address
        changes["permanent_address"] = payload.permanent_address
    if payload.emergency_contact is not None:
        person.emergency_contact = payload.emergency_contact
        changes["emergency_contact"] = payload.emergency_contact

    db.commit()
    db.refresh(person)

    log_audit(
        db, user=current_user, action="profile_self_updated",
        entity="person", entity_id=person.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"updated_fields": list(changes.keys())},
    )

    # Return updated profile
    engagement = (
        db.query(Engagement)
        .filter(Engagement.person_id == person.id)
        .order_by(Engagement.start_date.desc())
        .first()
    )
    return EmployeeProfileOut(
        id=person.id,
        user_id=current_user.id,
        full_name=person.full_name,
        preferred_name=person.preferred_name,
        email=person.email,
        phone=person.phone,
        gender=person.gender,
        date_of_birth=person.date_of_birth,
        current_address=person.current_address,
        permanent_address=person.permanent_address,
        emergency_contact=person.emergency_contact,
        designation=engagement.designation if engagement else None,
        department=engagement.department if engagement else None,
        engagement_type=engagement.engagement_type.value if engagement else None,
        start_date=engagement.start_date if engagement else None,
        reporting_manager_id=engagement.reporting_manager_id if engagement else None,
        work_location=engagement.work_location if engagement else None,
        status=engagement.status.value if engagement else "active",
    )


# ---------------------------------------------------------------------------
# 3. View Own Assigned Assets
# ---------------------------------------------------------------------------

@router.get("/assets", response_model=List[AssetItemOut])
def get_my_assets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = _resolve_person(current_user, db)
    assets = (
        db.query(EmployeeAsset)
        .filter(
            (EmployeeAsset.person_id == person.id) | (EmployeeAsset.user_id == current_user.id)
        )
        .order_by(EmployeeAsset.assigned_date.desc())
        .all()
    )
    return [
        AssetItemOut(
            id=a.id,
            asset_name=a.asset_name,
            asset_type=a.asset_type,
            serial_number=a.serial_number,
            assigned_date=a.assigned_date,
            return_status=a.return_status,
        )
        for a in assets
    ]


# ---------------------------------------------------------------------------
# 4. View and Submit Expense Claims
# ---------------------------------------------------------------------------

@router.get("/expenses", response_model=List[ExpenseClaimOut])
def get_my_expenses(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claims = (
        db.query(ExpenseClaim)
        .filter(ExpenseClaim.user_id == current_user.id)
        .order_by(ExpenseClaim.created_at.desc())
        .all()
    )
    return [
        ExpenseClaimOut(
            id=c.id,
            ticket_number=c.ticket_number,
            category=c.category,
            amount=float(c.amount),
            currency=c.currency,
            description=c.description,
            merchant=c.merchant,
            receipt_url=c.receipt_url,
            status=c.status,
            created_at=c.created_at,
        )
        for c in claims
    ]


@router.post("/expenses", response_model=ExpenseClaimOut, status_code=201)
def submit_expense_claim(
    payload: ExpenseClaimCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = _get_tenant_id(request, current_user)
    person = _resolve_person(current_user, db)

    ticket_num = f"EXP-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    claim = ExpenseClaim(
        ticket_number=ticket_num,
        tenant_id=tenant_id,
        person_id=person.id,
        user_id=current_user.id,
        category=payload.category,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        merchant=payload.merchant,
        receipt_url=payload.receipt_url,
        status="pending",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    log_audit(
        db, user=current_user, action="expense_claim_submitted",
        entity="expense_claim", entity_id=claim.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"ticket_number": claim.ticket_number, "amount": payload.amount},
    )

    return ExpenseClaimOut(
        id=claim.id,
        ticket_number=claim.ticket_number,
        category=claim.category,
        amount=float(claim.amount),
        currency=claim.currency,
        description=claim.description,
        merchant=claim.merchant,
        receipt_url=claim.receipt_url,
        status=claim.status,
        created_at=claim.created_at,
    )


# ---------------------------------------------------------------------------
# 5. Documents, Attendance, Leave & Payroll Direct Getters
# ---------------------------------------------------------------------------

@router.get("/documents", response_model=List[DocumentItemOut])
def get_my_documents(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = _resolve_person(current_user, db)
    docs = db.query(Document).filter(Document.person_id == person.id).order_by(Document.created_at.desc()).all()
    return [
        DocumentItemOut(
            id=d.id,
            document_type=d.document_type,
            file_name=d.file_name,
            status=d.status.value if hasattr(d.status, 'value') else str(d.status),
            upload_date=d.upload_date or d.created_at,
        )
        for d in docs
    ]


@router.get("/payroll", response_model=List[PayslipSummaryOut])
def get_my_payslips(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = _resolve_person(current_user, db)
    payslips = db.query(Payslip).filter(Payslip.person_id == person.id).order_by(Payslip.created_at.desc()).all()
    return [
        PayslipSummaryOut(
            id=p.id,
            month=p.month if hasattr(p, 'month') and p.month else str(p.created_at.strftime("%Y-%m")),
            gross_pay=float(getattr(p, 'gross_salary', 0.0) or 0.0),
            total_deductions=float(p.total_deductions or 0.0),
            net_pay=float(getattr(p, 'net_salary', 0.0) or 0.0),
        )
        for p in payslips
    ]


@router.get("/attendance", response_model=List[AttendanceRecordOut])
def get_my_attendance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = _resolve_person(current_user, db)
    records = db.query(Attendance).filter(Attendance.person_id == person.id).order_by(Attendance.date.desc()).all()
    return [
        AttendanceRecordOut(
            id=a.id,
            date=a.date,
            status=a.status.value if hasattr(a.status, 'value') else str(a.status),
            check_in=a.check_in,
            check_out=a.check_out,
            notes=a.notes,
        )
        for a in records
    ]


@router.get("/leave", response_model=LeaveSummaryOut)
def get_my_leave(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = _resolve_person(current_user, db)
    leave_balances = db.query(LeaveBalance).filter(LeaveBalance.person_id == person.id).all()
    balance_items = []
    for lb in leave_balances:
        policy = db.query(LeavePolicy).filter(LeavePolicy.id == lb.leave_policy_id).first()
        balance_items.append(
            LeaveBalanceItemOut(
                policy_name=policy.name if policy else "Leave",
                leave_type=policy.leave_type if policy else "casual",
                balance=float(lb.balance or 0.0),
            )
        )
    leave_requests = db.query(LeaveRequest).filter(LeaveRequest.person_id == person.id).order_by(LeaveRequest.start_date.desc()).all()
    request_items = [
        LeaveRequestItemOut(
            id=lr.id,
            start_date=lr.start_date,
            end_date=lr.end_date,
            leave_type=lr.leave_type,
            status=lr.status.value if hasattr(lr.status, 'value') else str(lr.status),
            reason=lr.reason,
        )
        for lr in leave_requests
    ]
    return LeaveSummaryOut(balances=balance_items, recent_requests=request_items)
