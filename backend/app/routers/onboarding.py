from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User, Person
from app.models_v4 import (
    OnboardingTemplate, OnboardingProcess, OnboardingTask,
    OnboardingStatus, TaskCategory, TaskAssigneeRole, TaskStatus
)

router = APIRouter(prefix="/api/v4/onboarding", tags=["onboarding"])


class OnboardingTemplateCreate(BaseModel):
    tenant_id: str
    name: str
    department_id: Optional[str] = None
    checklist_tasks_json: list[dict]  # [{"title": "Upload Identity Documents", "category": "document", "role": "employee"}]


class OnboardingTemplateOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    tenant_id: str
    name: str
    checklist_tasks_json: list[dict]


class OnboardingStartRequest(BaseModel):
    tenant_id: str
    person_id: str
    template_id: Optional[str] = None
    target_joining_date: date


class OnboardingTaskOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    title: str
    category: TaskCategory
    assignee_role: TaskAssigneeRole
    status: TaskStatus
    due_date: Optional[date]


class OnboardingProcessOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    tenant_id: str
    person_id: str
    target_joining_date: date
    status: OnboardingStatus
    completion_percentage: float
    tasks: list[OnboardingTaskOut]


@router.post("/templates", response_model=OnboardingTemplateOut, status_code=201)
def create_onboarding_template(
    payload: OnboardingTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:update")),
):
    tmpl = OnboardingTemplate(
        tenant_id=payload.tenant_id,
        name=payload.name,
        department_id=payload.department_id,
        checklist_tasks_json=payload.checklist_tasks_json,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    log_audit(db, user=current_user, action="onboarding_template_created", entity="onboarding_template", entity_id=tmpl.id, result=AuditResult.SUCCESS, request=request)
    return tmpl


@router.post("/start", response_model=OnboardingProcessOut, status_code=201)
def start_onboarding_process(
    payload: OnboardingStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:update")),
):
    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person record not found")

    proc = OnboardingProcess(
        tenant_id=payload.tenant_id,
        person_id=payload.person_id,
        template_id=payload.template_id,
        target_joining_date=payload.target_joining_date,
        status=OnboardingStatus.PREBOARDING,
        completion_percentage=0.0,
    )
    db.add(proc)
    db.commit()
    db.refresh(proc)

    # Spawn tasks from template if provided
    if payload.template_id:
        tmpl = db.query(OnboardingTemplate).filter(OnboardingTemplate.id == payload.template_id).first()
        if tmpl and tmpl.checklist_tasks_json:
            for item in tmpl.checklist_tasks_json:
                t = OnboardingTask(
                    process_id=proc.id,
                    title=item.get("title", "Onboarding Task"),
                    category=item.get("category", TaskCategory.DOCUMENT),
                    assignee_role=item.get("role", TaskAssigneeRole.EMPLOYEE),
                    status=TaskStatus.PENDING,
                    due_date=payload.target_joining_date,
                )
                db.add(t)
            db.commit()
            db.refresh(proc)

    log_audit(db, user=current_user, action="onboarding_started", entity="onboarding_process", entity_id=proc.id, result=AuditResult.SUCCESS, request=request)
    return proc


@router.get("/{process_id}", response_model=OnboardingProcessOut)
def get_onboarding_process(
    process_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proc = db.query(OnboardingProcess).filter(OnboardingProcess.id == process_id).first()
    if not proc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding process not found")

    if current_user.person_id != proc.person_id:
        require_permission("employees:view")(current_user, db)

    return proc


@router.post("/tasks/{task_id}/complete", response_model=OnboardingTaskOut)
def complete_onboarding_task(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding task not found")

    proc = db.query(OnboardingProcess).filter(OnboardingProcess.id == task.process_id).first()
    if current_user.person_id != proc.person_id:
        require_permission("employees:update")(current_user, db)

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    db.commit()

    # Recalculate process completion %
    all_tasks = db.query(OnboardingTask).filter(OnboardingTask.process_id == proc.id).all()
    completed_count = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED)
    total_count = len(all_tasks)
    if total_count > 0:
        proc.completion_percentage = Decimal(str(round((completed_count / total_count) * 100.0, 2)))
        if completed_count == total_count:
            proc.status = OnboardingStatus.COMPLETED
    db.commit()

    log_audit(db, user=current_user, action="onboarding_task_completed", entity="onboarding_task", entity_id=task_id, result=AuditResult.SUCCESS, request=request)
    return task
