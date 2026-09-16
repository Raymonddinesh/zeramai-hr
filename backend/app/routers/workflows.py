from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v2 import WorkflowTemplate, WorkflowInstance, WorkflowType, WorkflowStatus

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowTemplateCreate(BaseModel):
    name: str
    workflow_type: WorkflowType = WorkflowType.CUSTOM
    steps_definition: list[dict]  # [{"step": 1, "role": "HIRING_MANAGER"}, {"step": 2, "role": "HR_ADMIN"}]


class WorkflowTemplateOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    name: str
    workflow_type: WorkflowType
    steps_definition: list[dict]


class WorkflowInstanceCreate(BaseModel):
    template_id: str
    payload_json: dict


class WorkflowInstanceOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    template_id: str
    requester_id: str
    current_step: int
    status: WorkflowStatus
    payload_json: Optional[dict]
    approval_history: list


@router.post("/templates", response_model=WorkflowTemplateOut, status_code=201)
def create_workflow_template(
    payload: WorkflowTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    tmpl = WorkflowTemplate(
        name=payload.name,
        workflow_type=payload.workflow_type,
        steps_definition=payload.steps_definition,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    log_audit(db, user=current_user, action="workflow_template_created", entity="workflow_template",
              entity_id=tmpl.id, result=AuditResult.SUCCESS, request=request)
    return tmpl


@router.post("/instances", response_model=WorkflowInstanceOut, status_code=201)
def start_workflow_instance(
    payload: WorkflowInstanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == payload.template_id).first()
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow template not found")

    inst = WorkflowInstance(
        template_id=payload.template_id,
        requester_id=current_user.id,
        current_step=1,
        status=WorkflowStatus.PENDING,
        payload_json=payload.payload_json,
        approval_history=[],
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    log_audit(db, user=current_user, action="workflow_started", entity="workflow_instance",
              entity_id=inst.id, result=AuditResult.SUCCESS, request=request)
    return inst


@router.post("/instances/{instance_id}/approve", response_model=WorkflowInstanceOut)
def approve_workflow_step(
    instance_id: str,
    note: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow instance not found")

    if inst.status != WorkflowStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Workflow is already {inst.status.value}")

    tmpl = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == inst.template_id).first()
    total_steps = len(tmpl.steps_definition) if tmpl else 1

    history = list(inst.approval_history or [])
    history.append({
        "step": inst.current_step,
        "approved_by": current_user.id,
        "note": note,
    })
    inst.approval_history = history

    if inst.current_step >= total_steps:
        inst.status = WorkflowStatus.APPROVED
    else:
        inst.current_step += 1

    db.commit()
    db.refresh(inst)

    log_audit(db, user=current_user, action="workflow_step_approved", entity="workflow_instance",
              entity_id=instance_id, result=AuditResult.SUCCESS, request=request,
              metadata={"step": inst.current_step, "status": inst.status.value})
    return inst
