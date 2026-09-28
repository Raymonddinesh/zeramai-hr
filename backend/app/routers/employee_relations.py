"""
routers/employee_relations.py - Module 8: Employee Relations & Disciplinary Action Router.

Endpoints:
- GET  /api/v3/employee-relations/cases
- POST /api/v3/employee-relations/cases
- GET  /api/v3/employee-relations/cases/{id}
- POST /api/v3/employee-relations/cases/{id}/assign
- POST /api/v3/employee-relations/cases/{id}/status
- POST /api/v3/employee-relations/cases/{id}/notes
- POST /api/v3/employee-relations/cases/{id}/disciplinary
- GET  /api/v3/employee-relations/disciplinary
- POST /api/v3/employee-relations/disciplinary/{id}/acknowledge
"""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, has_permission, require_permission, log_audit
from app.models import (
    AuditResult,
    User,
    UserRole,
    Person,
    Engagement,
)
from app.models_policy_er import (
    EmployeeRelationsCase,
    ERCaseNote,
    DisciplinaryAction,
    ERCaseCategory,
    ERCaseStatus,
    ERCaseSeverity,
    DisciplinaryActionType,
    DisciplinaryStatus,
)
from app.schemas_policy_er import (
    ERCaseCreate,
    ERCaseAssign,
    ERCaseStatusUpdate,
    ERCaseNoteCreate,
    ERCaseNoteOut,
    ERCaseOut,
    DisciplinaryActionCreate,
    DisciplinaryActionOut,
)

router = APIRouter(prefix="/api/v3/employee-relations", tags=["employee_relations"])


def is_hr_or_super(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


# ===========================================================================
# 1. Cases Management
# ===========================================================================

@router.get("/cases", response_model=List[ERCaseOut])
def list_cases(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List Employee Relations cases.
    - HR/Admin: sees all cases.
    - Manager: sees only cases where they are the assigned reporting_manager_id.
    - Employees: unauthorized to view general ER case queue (403).
    """
    is_hr = is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:view", db)
    is_mgr = has_permission(current_user, "compensation:recommend", db) or current_user.role == UserRole.HIRING_MANAGER

    if not is_hr and not is_mgr:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to view employee relations cases")

    query = db.query(EmployeeRelationsCase)

    if not is_hr and is_mgr:
        query = query.filter(EmployeeRelationsCase.reporting_manager_id == current_user.id)

    if status_filter:
        query = query.filter(EmployeeRelationsCase.status == status_filter)
    if category:
        query = query.filter(EmployeeRelationsCase.category == category)

    cases = query.order_by(EmployeeRelationsCase.created_at.desc()).all()
    results = []

    for c in cases:
        p = db.query(Person).filter(Person.id == c.subject_person_id).first()
        hr_u = db.query(User).filter(User.id == c.hr_owner_id).first()
        disc_count = db.query(DisciplinaryAction).filter(DisciplinaryAction.case_id == c.id).count()

        results.append(
            ERCaseOut(
                id=c.id,
                case_number=c.case_number,
                title=c.title,
                category=c.category,
                severity=c.severity,
                subject_person_id=c.subject_person_id,
                subject_person_name=p.full_name if p else None,
                reporting_manager_id=c.reporting_manager_id,
                hr_owner_id=c.hr_owner_id,
                hr_owner_name=hr_u.email if hr_u else None,
                created_by_id=c.created_by_id,
                status=c.status,
                description=c.description,
                investigation_summary=c.investigation_summary if is_hr else None,
                resolution_summary=c.resolution_summary,
                created_at=c.created_at,
                updated_at=c.updated_at,
                closed_at=c.closed_at,
                notes=[],
                disciplinary_actions_count=disc_count,
            )
        )
    return results


@router.post("/cases", response_model=ERCaseOut, status_code=201)
def create_case(
    payload: ERCaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Employee Relations case."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to create employee relations cases")

    subject = db.query(Person).filter(Person.id == payload.subject_person_id).first()
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject employee not found")

    case_num = f"ER-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

    reporting_mgr_id = payload.reporting_manager_id
    if not reporting_mgr_id:
        active_eng = db.query(Engagement).filter(
            Engagement.person_id == payload.subject_person_id,
            Engagement.status == "active"
        ).first()
        if active_eng:
            reporting_mgr_id = active_eng.reporting_manager_id

    case = EmployeeRelationsCase(
        case_number=case_num,
        title=payload.title,
        category=payload.category,
        severity=payload.severity,
        subject_person_id=payload.subject_person_id,
        reporting_manager_id=reporting_mgr_id,
        hr_owner_id=current_user.id,
        created_by_id=current_user.id,
        status=ERCaseStatus.OPEN,
        description=payload.description,
        investigation_summary=payload.investigation_summary,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    log_audit(
        db, user=current_user, action="er_case_created",
        entity="employee_relations_case", entity_id=case.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"case_number": case.case_number, "subject_person_id": case.subject_person_id}
    )

    return ERCaseOut(
        id=case.id,
        case_number=case.case_number,
        title=case.title,
        category=case.category,
        severity=case.severity,
        subject_person_id=case.subject_person_id,
        subject_person_name=subject.full_name,
        reporting_manager_id=case.reporting_manager_id,
        hr_owner_id=case.hr_owner_id,
        hr_owner_name=current_user.email,
        created_by_id=case.created_by_id,
        status=case.status,
        description=case.description,
        investigation_summary=case.investigation_summary,
        resolution_summary=None,
        created_at=case.created_at,
        updated_at=case.updated_at,
        closed_at=None,
        notes=[],
        disciplinary_actions_count=0,
    )


@router.get("/cases/{case_id}", response_model=ERCaseOut)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve details of an ER case.
    Enforces role-based confidentiality and field-level masking.
    """
    case = db.query(EmployeeRelationsCase).filter(EmployeeRelationsCase.id == case_id).first()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    is_hr = is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:view", db)
    is_assigned_mgr = bool(case.reporting_manager_id and case.reporting_manager_id == current_user.id)

    if not is_hr and not is_assigned_mgr:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to this employee relations case")

    # Filter notes based on role
    raw_notes = db.query(ERCaseNote).filter(ERCaseNote.case_id == case.id).order_by(ERCaseNote.created_at.asc()).all()
    notes_out = []
    for n in raw_notes:
        if n.is_confidential and not is_hr:
            # Mask confidential notes from managers and subject employees
            continue
        author = db.query(User).filter(User.id == n.author_id).first()
        notes_out.append(
            ERCaseNoteOut(
                id=n.id,
                case_id=n.case_id,
                author_id=n.author_id,
                author_name=author.email if author else None,
                note_type=n.note_type,
                content=n.content,
                is_confidential=n.is_confidential,
                created_at=n.created_at,
            )
        )

    p = db.query(Person).filter(Person.id == case.subject_person_id).first()
    hr_u = db.query(User).filter(User.id == case.hr_owner_id).first()
    disc_count = db.query(DisciplinaryAction).filter(DisciplinaryAction.case_id == case.id).count()

    return ERCaseOut(
        id=case.id,
        case_number=case.case_number,
        title=case.title,
        category=case.category,
        severity=case.severity,
        subject_person_id=case.subject_person_id,
        subject_person_name=p.full_name if p else None,
        reporting_manager_id=case.reporting_manager_id,
        hr_owner_id=case.hr_owner_id,
        hr_owner_name=hr_u.email if hr_u else None,
        created_by_id=case.created_by_id,
        status=case.status,
        description=case.description,
        investigation_summary=case.investigation_summary if is_hr else None,  # Confidential field masked
        resolution_summary=case.resolution_summary,
        created_at=case.created_at,
        updated_at=case.updated_at,
        closed_at=case.closed_at,
        notes=notes_out,
        disciplinary_actions_count=disc_count,
    )


@router.post("/cases/{case_id}/assign", response_model=ERCaseOut)
def assign_case_owner(
    case_id: str,
    payload: ERCaseAssign,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign or reassign HR case owner."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to assign case")

    case = db.query(EmployeeRelationsCase).filter(EmployeeRelationsCase.id == case_id).first()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    new_owner = db.query(User).filter(User.id == payload.hr_owner_id).first()
    if not new_owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assigned HR user not found")

    case.hr_owner_id = payload.hr_owner_id
    db.commit()
    db.refresh(case)

    log_audit(
        db, user=current_user, action="er_case_assigned",
        entity="employee_relations_case", entity_id=case.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"new_owner_id": payload.hr_owner_id}
    )
    return get_case(case_id, db, current_user)


@router.post("/cases/{case_id}/status", response_model=ERCaseOut)
def update_case_status(
    case_id: str,
    payload: ERCaseStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update case lifecycle status."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to update case status")

    case = db.query(EmployeeRelationsCase).filter(EmployeeRelationsCase.id == case_id).first()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    case.status = payload.status
    if payload.investigation_summary:
        case.investigation_summary = payload.investigation_summary
    if payload.resolution_summary:
        case.resolution_summary = payload.resolution_summary
    if payload.status == ERCaseStatus.CLOSED and not case.closed_at:
        case.closed_at = datetime.utcnow()

    db.commit()
    db.refresh(case)

    log_audit(
        db, user=current_user, action="er_case_status_updated",
        entity="employee_relations_case", entity_id=case.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"new_status": str(case.status)}
    )
    return get_case(case_id, db, current_user)


@router.post("/cases/{case_id}/notes", response_model=ERCaseNoteOut, status_code=201)
def add_case_note(
    case_id: str,
    payload: ERCaseNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an internal, investigation, evidence, or communication note to a case."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:manage", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to add notes to case")

    case = db.query(EmployeeRelationsCase).filter(EmployeeRelationsCase.id == case_id).first()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    note = ERCaseNote(
        case_id=case.id,
        author_id=current_user.id,
        note_type=payload.note_type,
        content=payload.content,
        is_confidential=payload.is_confidential,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    log_audit(
        db, user=current_user, action="er_case_note_added",
        entity="er_case_note", entity_id=note.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"case_id": case.id, "confidential": payload.is_confidential}
    )

    return ERCaseNoteOut(
        id=note.id,
        case_id=note.case_id,
        author_id=note.author_id,
        author_name=current_user.email,
        note_type=note.note_type,
        content=note.content,
        is_confidential=note.is_confidential,
        created_at=note.created_at,
    )


# ===========================================================================
# 2. Disciplinary Actions
# ===========================================================================

@router.post("/cases/{case_id}/disciplinary", response_model=DisciplinaryActionOut, status_code=201)
def issue_disciplinary_action(
    case_id: str,
    payload: DisciplinaryActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a formal disciplinary action for an ER case."""
    if not (is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:disciplinary", db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to issue disciplinary actions")

    case = db.query(EmployeeRelationsCase).filter(EmployeeRelationsCase.id == case_id).first()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    target_person_id = payload.person_id or case.subject_person_id
    person = db.query(Person).filter(Person.id == target_person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target employee not found")

    reason_text = payload.reason or payload.description or "Formal disciplinary action"
    issued_d = payload.issued_date or date.today()

    action = DisciplinaryAction(
        case_id=case.id,
        person_id=target_person_id,
        action_type=payload.action_type,
        reason=reason_text,
        action_plan=payload.action_plan,
        issued_by_id=current_user.id,
        issued_date=issued_d,
        effective_date=payload.effective_date,
        expiry_date=payload.expiry_date,
        status=DisciplinaryStatus.ACTIVE,
    )
    db.add(action)

    # Transition case to ACTION_REQUIRED if still open/investigating
    if case.status in (ERCaseStatus.OPEN, ERCaseStatus.UNDER_REVIEW, ERCaseStatus.INVESTIGATION):
        case.status = ERCaseStatus.ACTION_REQUIRED

    db.commit()
    db.refresh(action)

    log_audit(
        db, user=current_user, action="disciplinary_action_issued",
        entity="disciplinary_action", entity_id=action.id,
        result=AuditResult.SUCCESS, request=request,
        metadata={"action_type": action.action_type, "person_id": action.person_id}
    )

    return DisciplinaryActionOut(
        id=action.id,
        case_id=action.case_id,
        person_id=action.person_id,
        person_name=person.full_name,
        action_type=action.action_type,
        reason=action.reason,
        action_plan=action.action_plan,
        issued_by_id=action.issued_by_id,
        issued_date=action.issued_date,
        effective_date=action.effective_date,
        expiry_date=action.expiry_date,
        status=action.status,
        employee_acknowledged=action.employee_acknowledged,
        acknowledged_at=action.acknowledged_at,
        created_at=action.created_at,
    )


@router.get("/disciplinary", response_model=List[DisciplinaryActionOut])
def list_disciplinary_actions(
    person_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List formal disciplinary actions."""
    is_hr = is_hr_or_super(current_user) or has_permission(current_user, "employee_relations:view", db)

    query = db.query(DisciplinaryAction)
    if not is_hr:
        # Employee can only view their own disciplinary records
        if not current_user.person_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized")
        query = query.filter(DisciplinaryAction.person_id == current_user.person_id)
    elif person_id:
        query = query.filter(DisciplinaryAction.person_id == person_id)

    actions = query.order_by(DisciplinaryAction.issued_date.desc()).all()
    results = []
    for a in actions:
        p = db.query(Person).filter(Person.id == a.person_id).first()
        results.append(
            DisciplinaryActionOut(
                id=a.id,
                case_id=a.case_id,
                person_id=a.person_id,
                person_name=p.full_name if p else None,
                action_type=a.action_type,
                reason=a.reason,
                action_plan=a.action_plan,
                issued_by_id=a.issued_by_id,
                issued_date=a.issued_date,
                effective_date=a.effective_date,
                expiry_date=a.expiry_date,
                status=a.status,
                employee_acknowledged=a.employee_acknowledged,
                acknowledged_at=a.acknowledged_at,
                created_at=a.created_at,
            )
        )
    return results


@router.post("/disciplinary/{action_id}/acknowledge", response_model=DisciplinaryActionOut)
def acknowledge_disciplinary_action(
    action_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Employee electronically acknowledges receipt of a disciplinary action."""
    if not current_user.person_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only subject employee can acknowledge disciplinary action")

    action = db.query(DisciplinaryAction).filter(DisciplinaryAction.id == action_id).first()
    if not action:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Disciplinary action not found")

    if str(action.person_id) != str(current_user.person_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot acknowledge another employee's disciplinary action")

    action.employee_acknowledged = True
    action.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(action)

    log_audit(
        db, user=current_user, action="disciplinary_action_acknowledged",
        entity="disciplinary_action", entity_id=action.id,
        result=AuditResult.SUCCESS, request=request,
    )

    p = db.query(Person).filter(Person.id == action.person_id).first()
    return DisciplinaryActionOut(
        id=action.id,
        case_id=action.case_id,
        person_id=action.person_id,
        person_name=p.full_name if p else None,
        action_type=action.action_type,
        reason=action.reason,
        action_plan=action.action_plan,
        issued_by_id=action.issued_by_id,
        issued_date=action.issued_date,
        effective_date=action.effective_date,
        expiry_date=action.expiry_date,
        status=action.status,
        employee_acknowledged=action.employee_acknowledged,
        acknowledged_at=action.acknowledged_at,
        created_at=action.created_at,
    )
