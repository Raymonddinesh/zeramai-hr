import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Enum, Numeric,
    Text, Integer, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Onboarding & Preboarding Engine (PRD v3.0 Section 12)
# ---------------------------------------------------------------------------

class OnboardingStatus(str, enum.Enum):
    PREBOARDING = "preboarding"
    ONBOARDING = "onboarding"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskCategory(str, enum.Enum):
    DOCUMENT = "document"
    EQUIPMENT = "equipment"
    TRAINING = "training"
    ACCOUNT_PROVISIONING = "account_provisioning"
    MANAGER_INTRO = "manager_intro"


class TaskAssigneeRole(str, enum.Enum):
    EMPLOYEE = "employee"
    HR = "hr"
    IT = "it"
    MANAGER = "manager"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class OnboardingTemplate(Base):
    __tablename__ = "onboarding_templates"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    checklist_tasks_json = Column(JSON, nullable=False)  # [{"title": "Upload PAN/Aadhaar", "category": "document", "role": "employee"}]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OnboardingProcess(Base):
    __tablename__ = "onboarding_processes"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    template_id = Column(String, ForeignKey("onboarding_templates.id"), nullable=True)
    target_joining_date = Column(Date, nullable=False)
    status = Column(Enum(OnboardingStatus), default=OnboardingStatus.PREBOARDING, nullable=False)
    completion_percentage = Column(Numeric(5, 2), default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = relationship("OnboardingTask", back_populates="process", cascade="all, delete-orphan")


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    process_id = Column(String, ForeignKey("onboarding_processes.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    category = Column(Enum(TaskCategory), default=TaskCategory.DOCUMENT, nullable=False)
    assignee_role = Column(Enum(TaskAssigneeRole), default=TaskAssigneeRole.EMPLOYEE, nullable=False)
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    process = relationship("OnboardingProcess", back_populates="tasks")
