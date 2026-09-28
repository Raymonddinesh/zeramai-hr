import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Enum, JSON, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Workflow Engine Core Models
# ---------------------------------------------------------------------------

class WorkflowEntityType(str, enum.Enum):
    """Entity types that a workflow can be attached to."""
    LEAVE_REQUEST = "leave_request"
    EXPENSE_REQUEST = "expense_request"
    HR_REQUEST = "hr_request"
    OFFBOARDING = "offboarding"
    COMPENSATION = "compensation"
    BENEFIT = "benefit"
    CUSTOM = "custom"

class WorkflowDefinitionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ApproverType(str, enum.Enum):
    MANAGER = "manager"
    HR = "hr"
    FINANCE = "finance"
    ROLE = "role"
    USER = "user"
    DEPARTMENT_HEAD = "department_head"

class ApprovalMode(str, enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    entity_type = Column(Enum(WorkflowEntityType), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(Enum(WorkflowDefinitionStatus), nullable=False, default=WorkflowDefinitionStatus.DRAFT)
    tenant_id = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    steps = relationship("WorkflowStep", back_populates="definition", cascade="all, delete-orphan")
    instances = relationship("WorkflowInstance", back_populates="definition")

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True, default=gen_uuid)
    definition_id = Column(String, ForeignKey("workflow_definitions.id"), nullable=False)
    order = Column(Integer, nullable=False)  # 1‑based order within the definition
    name = Column(String, nullable=False)
    step_type = Column(String, nullable=True)  # e.g., "approval", "notification"
    approval_mode = Column(Enum(ApprovalMode), nullable=False, default=ApprovalMode.SEQUENTIAL)
    required = Column(Boolean, nullable=False, default=True)
    sla_hours = Column(Integer, nullable=True)  # Service‑level‑agreement in hours
    approver_rule = Column(JSON, nullable=False)  # e.g., {"type": "manager"} or {"type": "role", "role": "finance"}
    conditions = Column(JSON, nullable=True)  # optional condition dict evaluated server‑side

    definition = relationship("WorkflowDefinition", back_populates="steps")
    tasks = relationship("ApprovalTask", back_populates="step")

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(String, primary_key=True, default=gen_uuid)
    definition_id = Column(String, ForeignKey("workflow_definitions.id"), nullable=False)
    definition_version = Column(Integer, nullable=False)
    tenant_id = Column(String, nullable=False)
    entity_type = Column(Enum(WorkflowEntityType), nullable=False)
    entity_id = Column(String, nullable=False)  # e.g., leave request id
    requester_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(WorkflowDefinitionStatus), nullable=False, default=WorkflowDefinitionStatus.DRAFT)
    current_step_order = Column(Integer, nullable=True)  # null when completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    definition = relationship("WorkflowDefinition", back_populates="instances")
    tasks = relationship("ApprovalTask", back_populates="instance", cascade="all, delete-orphan")

class ApprovalTaskStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    step_id = Column(String, ForeignKey("workflow_steps.id"), nullable=False)
    approver_type = Column(Enum(ApproverType), nullable=False)
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=True)  # resolved server‑side
    status = Column(Enum(ApprovalTaskStatus), nullable=False, default=ApprovalTaskStatus.PENDING)
    due_date = Column(Date, nullable=True)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    instance = relationship("WorkflowInstance", back_populates="tasks")
    step = relationship("WorkflowStep", back_populates="tasks")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])

class Delegation(Base):
    __tablename__ = "delegations"

    id = Column(String, primary_key=True, default=gen_uuid)
    delegator_id = Column(String, ForeignKey("users.id"), nullable=False)
    delegate_id = Column(String, ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    scope = Column(JSON, nullable=False)  # e.g., {"entity_type": "leave_request", "definition_code": "LEAVE_APPROVAL"}
    reason = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    tenant_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, default=gen_uuid)
    task_id = Column(String, ForeignKey("approval_tasks.id"), nullable=False)
    due_date = Column(Date, nullable=False)
    level = Column(Integer, nullable=False, default=1)
    target_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="open")
    tenant_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    task = relationship("ApprovalTask")
    target_user = relationship("User", foreign_keys=[target_user_id])
