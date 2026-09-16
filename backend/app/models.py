import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models_v2 import (  # noqa: F401
    JobOpening, CandidateApplication, WorkflowTemplate, WorkflowInstance, SAMLProvider,
    JobStatus, ApplicationStage, WorkflowType, WorkflowStatus
)
from app.models_v3 import (  # noqa: F401
    Tenant, LegalEntity, Location, Department, CostCenter, EmploymentHistory, HistoryChangeType
)
from app.models_v4 import (  # noqa: F401
    OnboardingTemplate, OnboardingProcess, OnboardingTask, OnboardingStatus, TaskCategory, TaskAssigneeRole, TaskStatus
)


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    HR_ADMIN = "hr_admin"
    HIRING_MANAGER = "hiring_manager"
    EMPLOYEE = "employee"          # self-service role, includes trainees
    FINANCE = "finance"


class CandidateStatus(str, enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    SELECTED = "selected"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"
    CONVERTED_TO_TRAINEE = "converted_to_trainee"
    CONVERTED_TO_EMPLOYEE = "converted_to_employee"


class EngagementType(str, enum.Enum):
    INTERN = "intern"
    ENGINEERING_TRAINEE = "engineering_trainee"
    GRADUATE_TRAINEE = "graduate_trainee"
    PROBATIONARY_EMPLOYEE = "probationary_employee"
    FULL_TIME_EMPLOYEE = "full_time_employee"
    CONTRACTOR = "contractor"
    CONSULTANT = "consultant"


class EngagementStatus(str, enum.Enum):
    PENDING_JOINING = "pending_joining"
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    NOTICE_PERIOD = "notice_period"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    RESIGNED = "resigned"
    ARCHIVED = "archived"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class AuditResult(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class User(Base):
    """
    A login account. Deliberately separate from Person: not every Person
    (e.g. a not-yet-joined candidate) has login credentials, and not every
    User necessarily maps 1:1 to an HR record (future: service accounts).
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)  # legacy enum role
    person_id = Column(String, ForeignKey("persons.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    person = relationship("Person", back_populates="user_account")
    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
    )


# ---------------------------------------------------------------------------
# Unified person identity
# ---------------------------------------------------------------------------

class Person(Base):
    """
    The single identity record for a human, regardless of what stage they're
    at. A Candidate, an Engagement (trainee/employee/etc.), and Documents all
    hang off Person. This is what lets one human have multiple historical
    engagements (candidate -> trainee -> employee -> ... ) without losing
    history and without duplicating identity data across tables.
    """
    __tablename__ = "persons"

    id = Column(String, primary_key=True, default=gen_uuid)
    full_name = Column(String, nullable=False)
    preferred_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String, nullable=True)  # free-text/configurable, not an enum by design
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    current_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)
    emergency_contact = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user_account = relationship("User", back_populates="person", uselist=False)
    candidate = relationship("Candidate", back_populates="person", uselist=False)
    engagements = relationship("Engagement", back_populates="person")
    documents = relationship("Document", back_populates="person")


# ---------------------------------------------------------------------------
# RBAC models
# ---------------------------------------------------------------------------

class Role(Base):
    """Role definition – e.g. super_admin, hr_admin, etc."""
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, nullable=False)

    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )
    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
    )


class Permission(Base):
    """Fine‑grained permission, identified by a code like 'candidate:create'."""
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=gen_uuid)
    code = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.id"), primary_key=True)


class UserRoleAssociation(Base):
    __tablename__ = "user_roles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)


class Candidate(Base):
    """
    Recruitment-stage data. One-to-one with Person. Kept separate from
    Person because most of these fields (interview score, recruiter,
    application date) are meaningless once someone becomes a trainee/employee
    — they don't belong polluting the core identity record.
    """
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, unique=True)

    applied_position = Column(String, nullable=True)
    department = Column(String, nullable=True)
    recruiter = Column(String, nullable=True)
    hiring_manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    application_date = Column(Date, nullable=True)
    interview_status = Column(String, nullable=True)
    interview_score = Column(Integer, nullable=True)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.APPLIED, nullable=False)

    resume_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    highest_qualification = Column(String, nullable=True)
    college_university = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person", back_populates="candidate")


class Engagement(Base):
    """
    One period of engagement with the company: trainee, employee, contractor,
    etc. A Person can have MULTIPLE Engagement rows over time (this is how
    "candidate -> trainee -> employee" and re-hires are represented without
    ever mutating/destroying history). Exactly one engagement per person
    should normally be ACTIVE at a time, but that's an application-level
    invariant, not a DB constraint, since e.g. NOTICE_PERIOD overlaps exist.
    """
    __tablename__ = "engagements"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False)
    converted_from_candidate_id = Column(String, ForeignKey("candidates.id"), nullable=True)

    engagement_type = Column(Enum(EngagementType), nullable=False)
    designation = Column(String, nullable=False)
    department = Column(String, nullable=False)
    reporting_manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    work_location = Column(String, nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # auto-calculated for fixed-duration engagements (e.g. trainee + 6mo)

    # Stipend is deliberately separate from any future "salary" field, and the
    # PRD requires the UI/documents to never blur the two.
    stipend_amount = Column(Numeric(10, 2), nullable=True)
    stipend_currency = Column(String, default="INR", nullable=False)

    status = Column(Enum(EngagementStatus), default=EngagementStatus.PENDING_JOINING, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person", back_populates="engagements")


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class Document(Base):
    """
    Metadata only. The actual bytes live in private object storage, never
    served via a public/permanent URL — see storage.py. `storage_key` is an
    internal reference, not something ever returned directly to a browser.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False)

    document_type = Column(String, nullable=False)  # e.g. "pan", "engagement_letter", "nda"
    file_name = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)  # opaque path/key in the storage backend

    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    upload_date = Column(DateTime, nullable=True)
    verified_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    expiry_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person", back_populates="documents")


# ---------------------------------------------------------------------------
# Audit log — append-only
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """
    Append-only by convention at the application layer: no UPDATE/DELETE
    endpoint or service method exists for this table anywhere in the app.
    (Production hardening: also revoke UPDATE/DELETE grants on this table
    for the application's DB role, so a bug or SQLi can't rewrite history —
    see SECURITY.md once we write it.)
    """
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    entity_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    result = Column(Enum(AuditResult), nullable=False)
    metadata_json = Column(JSON, nullable=True)


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------

class LeaveType(str, enum.Enum):
    CASUAL = "casual"
    SICK = "sick"
    EARNED = "earned"
    UNPAID = "unpaid"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    OTHER = "other"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    leave_type = Column(Enum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Numeric(4, 1), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), nullable=False, default=LeaveStatus.PENDING)
    reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

class EvaluationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True)
    evaluator_id = Column(String, ForeignKey("users.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    overall_rating = Column(Numeric(3, 1), nullable=True)   # e.g. 4.5 / 5.0
    comments = Column(Text, nullable=True)
    status = Column(Enum(EvaluationStatus), nullable=False, default=EvaluationStatus.DRAFT)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    evaluator = relationship("User", foreign_keys=[evaluator_id])


# ---------------------------------------------------------------------------
# Stipends
# ---------------------------------------------------------------------------

class StipendStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class Stipend(Base):
    __tablename__ = "stipends"

    id = Column(String, primary_key=True, default=gen_uuid)
    person_id = Column(String, ForeignKey("persons.id"), nullable=False, index=True)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True)
    month = Column(String, nullable=False)       # "2026-09" format
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="INR", nullable=False)
    status = Column(Enum(StipendStatus), nullable=False, default=StipendStatus.PENDING)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    payment_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")

