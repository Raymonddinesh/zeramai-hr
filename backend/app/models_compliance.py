import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Compliance Calendar & Task Enums
# ---------------------------------------------------------------------------

class ComplianceType(str, enum.Enum):
    STATUTORY = "statutory"
    PAYROLL = "payroll"
    HR = "hr"
    POLICY = "policy"
    GENERAL = "general"


class ComplianceStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    WAIVED = "waived"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Compliance Models
# ---------------------------------------------------------------------------

class ComplianceTask(Base):
    """A task that must be completed for statutory or HR compliance.
    Linked to tenant, optional legal entity, assigned owner, source entity, and completion evidence.
    """
    __tablename__ = "compliance_tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True, index=True)
    compliance_type = Column(Enum(ComplianceType), nullable=False)
    authority = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    period = Column(String, nullable=True)  # e.g., "FY2026-27", "2026-10"
    due_date = Column(Date, nullable=False)
    status = Column(Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.OPEN)
    priority = Column(Integer, nullable=True, default=1)  # 1 = low, 2 = medium, 3 = high, 4 = urgent
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    evidence_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    source_entity_type = Column(String, nullable=True)  # e.g. "statutory_filing", "payroll_run"
    source_entity_id = Column(String, nullable=True)
    reminder_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")
    assigned_user = relationship("User")
    evidence_document = relationship("Document")


class ComplianceCalendar(Base):
    """Calendar entries for compliance deadlines, statutory due dates, and reminders."""
    __tablename__ = "compliance_calendar"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    legal_entity_id = Column(String, ForeignKey("legal_entities.id"), nullable=True, index=True)
    compliance_type = Column(Enum(ComplianceType), nullable=False)
    authority = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    period = Column(String, nullable=True)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.OPEN)
    priority = Column(Integer, nullable=True, default=1)
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    evidence_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    reminder_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")
    assigned_user = relationship("User")
    evidence_document = relationship("Document")
