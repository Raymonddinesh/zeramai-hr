"""
models_learning.py - Module 18: Enterprise Learning, Skills & Career Development Models
Zeramai Enterprise HRMS
"""
import uuid
import enum
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LearningType(str, enum.Enum):
    COURSE = "COURSE"
    WORKSHOP = "WORKSHOP"
    WEBINAR = "WEBINAR"
    BOOTCAMP = "BOOTCAMP"
    SELF_PACED = "SELF_PACED"
    INSTRUCTOR_LED = "INSTRUCTOR_LED"
    ON_THE_JOB = "ON_THE_JOB"
    CONFERENCE = "CONFERENCE"


class DeliveryMode(str, enum.Enum):
    ONLINE = "ONLINE"
    CLASSROOM = "CLASSROOM"
    HYBRID = "HYBRID"
    SELF_PACED = "SELF_PACED"


class CourseLifecycleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ProviderType(str, enum.Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    UNIVERSITY = "UNIVERSITY"
    CERTIFICATION_BODY = "CERTIFICATION_BODY"
    VENDOR = "VENDOR"


class ContentType(str, enum.Enum):
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    ARTICLE = "ARTICLE"
    LINK = "LINK"
    LAB = "LAB"
    QUIZ = "QUIZ"
    ASSIGNMENT = "ASSIGNMENT"
    LIVE_SESSION = "LIVE_SESSION"


class EnrollmentType(str, enum.Enum):
    SELF = "SELF"
    ASSIGNED = "ASSIGNED"
    MANDATORY = "MANDATORY"
    PATH = "PATH"


class LearningEnrollmentStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    ENROLLED = "ENROLLED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"
    OPEN_TEXT = "OPEN_TEXT"
    ESSAY = "ESSAY"


class CertificationVerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OpportunityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CareerApplicationStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    SELECTED = "SELECTED"


class MentoringStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class SkillActionType(str, enum.Enum):
    COURSE = "COURSE"
    MENTORING = "MENTORING"
    PROJECT = "PROJECT"
    COACHING = "COACHING"
    CERTIFICATION = "CERTIFICATION"
    ASSESSMENT = "ASSESSMENT"
    JOB_ROTATION = "JOB_ROTATION"


class SkillEvidenceType(str, enum.Enum):
    COURSE = "COURSE"
    ASSESSMENT = "ASSESSMENT"
    CERTIFICATION = "CERTIFICATION"
    PROJECT = "PROJECT"
    MANAGER_VERIFICATION = "MANAGER_VERIFICATION"
    EXTERNAL_CREDENTIAL = "EXTERNAL_CREDENTIAL"


# ---------------------------------------------------------------------------
# 1. Training Providers
# ---------------------------------------------------------------------------

class TrainingProvider(Base):
    __tablename__ = "training_providers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), default=ProviderType.INTERNAL.value, nullable=False)
    website = Column(String(255), nullable=True)
    contact_reference = Column(String(255), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    courses = relationship("LearningCourse", back_populates="provider")


# ---------------------------------------------------------------------------
# 2. Learning Catalog Courses & Modules
# ---------------------------------------------------------------------------

class LearningCourse(Base):
    __tablename__ = "learning_courses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    course_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="GENERAL", nullable=False)
    learning_type = Column(String(50), default=LearningType.COURSE.value, nullable=False)
    difficulty = Column(String(50), default="INTERMEDIATE", nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    provider_id = Column(String(36), ForeignKey("training_providers.id"), nullable=True, index=True)
    delivery_mode = Column(String(50), default=DeliveryMode.ONLINE.value, nullable=False)
    language = Column(String(20), default="en", nullable=False)
    status = Column(String(32), default=CourseLifecycleStatus.DRAFT.value, nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    provider = relationship("TrainingProvider", back_populates="courses")
    modules = relationship("LearningModule", back_populates="course", cascade="all, delete-orphan", order_by="LearningModule.sequence")
    skill_mappings = relationship("CourseSkillMapping", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("LearningEnrollment", back_populates="course")
    assessments = relationship("LearningAssessment", back_populates="course", cascade="all, delete-orphan")


class LearningModule(Base):
    __tablename__ = "learning_modules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sequence = Column(Integer, default=1, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    mandatory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("LearningCourse", back_populates="modules")
    contents = relationship("CourseContent", back_populates="module", cascade="all, delete-orphan", order_by="CourseContent.sequence")


class CourseContent(Base):
    __tablename__ = "course_contents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    module_id = Column(String(36), ForeignKey("learning_modules.id"), nullable=False, index=True)
    content_type = Column(String(50), default=ContentType.DOCUMENT.value, nullable=False)
    title = Column(String(255), nullable=False)
    content_reference = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=10, nullable=False)
    sequence = Column(Integer, default=1, nullable=False)
    required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    module = relationship("LearningModule", back_populates="contents")


# ---------------------------------------------------------------------------
# 3. Learning Paths
# ---------------------------------------------------------------------------

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_role = Column(String(255), nullable=True)
    target_job_family = Column(String(100), nullable=True)
    status = Column(String(32), default=CourseLifecycleStatus.DRAFT.value, nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    path_courses = relationship("LearningPathCourse", back_populates="learning_path", cascade="all, delete-orphan", order_by="LearningPathCourse.sequence")


class LearningPathCourse(Base):
    __tablename__ = "learning_path_courses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    learning_path_id = Column(String(36), ForeignKey("learning_paths.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=False, index=True)
    sequence = Column(Integer, default=1, nullable=False)
    mandatory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    learning_path = relationship("LearningPath", back_populates="path_courses")
    course = relationship("LearningCourse")


# ---------------------------------------------------------------------------
# 4. Course Skill Mapping
# ---------------------------------------------------------------------------

class CourseSkillMapping(Base):
    __tablename__ = "course_skill_mappings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False, index=True)
    target_skill_level_id = Column(String(36), ForeignKey("skill_levels.id"), nullable=True)
    proficiency_gain = Column(Float, default=0.5, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("LearningCourse", back_populates="skill_mappings")
    skill = relationship("Skill")
    target_skill_level = relationship("SkillLevel")


# ---------------------------------------------------------------------------
# 5. Enrollments & Progress
# ---------------------------------------------------------------------------

class LearningEnrollment(Base):
    __tablename__ = "learning_enrollments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=True, index=True)
    learning_path_id = Column(String(36), ForeignKey("learning_paths.id"), nullable=True, index=True)
    enrollment_type = Column(String(50), default=EnrollmentType.SELF.value, nullable=False)
    status = Column(String(32), default=LearningEnrollmentStatus.ENROLLED.value, nullable=False, index=True)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    completion_score = Column(Float, nullable=True)
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("LearningCourse", back_populates="enrollments")
    learning_path = relationship("LearningPath")
    person = relationship("Person")
    progress_records = relationship("LearningProgress", back_populates="enrollment", cascade="all, delete-orphan")


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    enrollment_id = Column(String(36), ForeignKey("learning_enrollments.id"), nullable=False, index=True)
    module_id = Column(String(36), ForeignKey("learning_modules.id"), nullable=False, index=True)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    time_spent_minutes = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    enrollment = relationship("LearningEnrollment", back_populates="progress_records")
    module = relationship("LearningModule")


# ---------------------------------------------------------------------------
# 6. Assessments & Questions
# ---------------------------------------------------------------------------

class LearningAssessment(Base):
    __tablename__ = "learning_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    passing_score = Column(Float, default=70.0, nullable=False)
    attempts_allowed = Column(Integer, default=3, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("LearningCourse", back_populates="assessments")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.sequence")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("learning_assessments.id"), nullable=False, index=True)
    question_type = Column(String(32), default=QuestionType.MULTIPLE_CHOICE.value, nullable=False)
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)  # JSON-encoded options
    correct_answer = Column(Text, nullable=False)  # Hidden from normal employee queries
    sequence = Column(Integer, default=1, nullable=False)
    points = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    assessment = relationship("LearningAssessment", back_populates="questions")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    assessment_id = Column(String(36), ForeignKey("learning_assessments.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    enrollment_id = Column(String(36), ForeignKey("learning_enrollments.id"), nullable=True, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    answers_json = Column(Text, nullable=True)
    score = Column(Float, default=0.0, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    assessment = relationship("LearningAssessment", back_populates="attempts")
    person = relationship("Person")
    enrollment = relationship("LearningEnrollment")


# ---------------------------------------------------------------------------
# 7. Certifications & Expiry Tracking
# ---------------------------------------------------------------------------

class Certification(Base):
    __tablename__ = "certifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    issuing_body = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    validity_months = Column(Integer, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee_certifications = relationship("EmployeeCertification", back_populates="certification", cascade="all, delete-orphan")


class EmployeeCertification(Base):
    __tablename__ = "employee_certifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    certification_id = Column(String(36), ForeignKey("certifications.id"), nullable=False, index=True)
    credential_number = Column(String(100), nullable=True)
    issued_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True, index=True)
    verification_status = Column(String(32), default=CertificationVerificationStatus.UNVERIFIED.value, nullable=False, index=True)
    document_reference = Column(Text, nullable=True)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    certification = relationship("Certification", back_populates="employee_certifications")
    person = relationship("Person")


# ---------------------------------------------------------------------------
# 8. Mandatory & Compliance Training Requirements
# ---------------------------------------------------------------------------

class TrainingRequirement(Base):
    __tablename__ = "training_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=False, index=True)
    applicability_rule = Column(String(255), default="ALL_EMPLOYEES", nullable=False)
    due_days = Column(Integer, default=30, nullable=False)
    recurrence = Column(String(50), default="ANNUAL", nullable=False)
    mandatory = Column(Boolean, default=True, nullable=False)
    compliance_reference = Column(String(100), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("LearningCourse")
    assignments = relationship("TrainingAssignment", back_populates="requirement", cascade="all, delete-orphan")


class TrainingAssignment(Base):
    __tablename__ = "training_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    requirement_id = Column(String(36), ForeignKey("training_requirements.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(32), default="ASSIGNED", nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    requirement = relationship("TrainingRequirement", back_populates="assignments")
    person = relationship("Person")


# ---------------------------------------------------------------------------
# 9. Learning Plans
# ---------------------------------------------------------------------------

class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String(32), default=PlanStatus.DRAFT.value, nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    items = relationship("LearningPlanItem", back_populates="plan", cascade="all, delete-orphan")


class LearningPlanItem(Base):
    __tablename__ = "learning_plan_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("learning_plans.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=True, index=True)
    learning_path_id = Column(String(36), ForeignKey("learning_paths.id"), nullable=True, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=True, index=True)
    target_skill_level_id = Column(String(36), ForeignKey("skill_levels.id"), nullable=True)
    target_date = Column(Date, nullable=False)
    priority = Column(String(32), default="MEDIUM", nullable=False)
    status = Column(String(32), default="PLANNED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("LearningPlan", back_populates="items")
    course = relationship("LearningCourse")
    learning_path = relationship("LearningPath")
    skill = relationship("Skill")


# ---------------------------------------------------------------------------
# 10. Individual Development Plans (IDP) & Goals
# ---------------------------------------------------------------------------

class DevelopmentPlan(Base):
    __tablename__ = "development_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    current_role = Column(String(255), nullable=False)
    target_role = Column(String(255), nullable=True)
    career_direction = Column(Text, nullable=True)
    review_period = Column(String(100), default="FY27", nullable=False)
    status = Column(String(32), default=PlanStatus.DRAFT.value, nullable=False, index=True)
    employee_notes = Column(Text, nullable=True)
    manager_notes = Column(Text, nullable=True)  # Confidential: hidden from employee unless authorized
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    goals = relationship("DevelopmentGoal", back_populates="development_plan", cascade="all, delete-orphan")


class DevelopmentGoal(Base):
    __tablename__ = "development_goals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    development_plan_id = Column(String(36), ForeignKey("development_plans.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=True, index=True)
    target_level_id = Column(String(36), ForeignKey("skill_levels.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(32), default=PlanStatus.DRAFT.value, nullable=False)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    development_plan = relationship("DevelopmentPlan", back_populates="goals")
    skill = relationship("Skill")


# ---------------------------------------------------------------------------
# 11. Career Frameworks, Levels & Paths
# ---------------------------------------------------------------------------

class CareerFramework(Base):
    __tablename__ = "career_frameworks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    job_family = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    levels = relationship("CareerLevel", back_populates="framework", cascade="all, delete-orphan", order_by="CareerLevel.sequence")
    paths = relationship("CareerPath", back_populates="framework", cascade="all, delete-orphan")


class CareerLevel(Base):
    __tablename__ = "career_levels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    framework_id = Column(String(36), ForeignKey("career_frameworks.id"), nullable=False, index=True)
    code = Column(String(32), nullable=False)
    name = Column(String(100), nullable=False)
    sequence = Column(Integer, default=1, nullable=False)
    description = Column(Text, nullable=True)
    expected_skill_profile = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    framework = relationship("CareerFramework", back_populates="levels")


class CareerPath(Base):
    __tablename__ = "career_paths"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    framework_id = Column(String(36), ForeignKey("career_frameworks.id"), nullable=False, index=True)
    from_level_id = Column(String(36), ForeignKey("career_levels.id"), nullable=False, index=True)
    to_level_id = Column(String(36), ForeignKey("career_levels.id"), nullable=False, index=True)
    typical_requirements = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    framework = relationship("CareerFramework", back_populates="paths")
    from_level = relationship("CareerLevel", foreign_keys=[from_level_id])
    to_level = relationship("CareerLevel", foreign_keys=[to_level_id])


# ---------------------------------------------------------------------------
# 12. Internal Career Opportunities & Applications
# ---------------------------------------------------------------------------

class CareerOpportunity(Base):
    __tablename__ = "career_opportunities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)
    required_level = Column(String(50), nullable=True)
    eligibility_rules = Column(Text, nullable=True)
    application_deadline = Column(Date, nullable=True)
    status = Column(String(32), default=OpportunityStatus.OPEN.value, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    position = relationship("Position")
    applications = relationship("CareerApplication", back_populates="opportunity", cascade="all, delete-orphan")


class CareerApplication(Base):
    __tablename__ = "career_applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    opportunity_id = Column(String(36), ForeignKey("career_opportunities.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    status = Column(String(32), default=CareerApplicationStatus.SUBMITTED.value, nullable=False, index=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    withdrawn_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    opportunity = relationship("CareerOpportunity", back_populates="applications")
    person = relationship("Person")


# ---------------------------------------------------------------------------
# 13. Mentoring Programs & Relationships
# ---------------------------------------------------------------------------

class MentoringProgram(Base):
    __tablename__ = "mentoring_programs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_months = Column(Integer, default=6, nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    relationships = relationship("MentoringRelationship", back_populates="program", cascade="all, delete-orphan")


class MentoringRelationship(Base):
    __tablename__ = "mentoring_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    program_id = Column(String(36), ForeignKey("mentoring_programs.id"), nullable=False, index=True)
    mentor_person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    mentee_person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    start_date = Column(Date, default=date.today, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(32), default=MentoringStatus.ACTIVE.value, nullable=False)
    goals = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    program = relationship("MentoringProgram", back_populates="relationships")
    mentor = relationship("Person", foreign_keys=[mentor_person_id])
    mentee = relationship("Person", foreign_keys=[mentee_person_id])


# ---------------------------------------------------------------------------
# 14. Skill Gap Remediation & Skill Evidence
# ---------------------------------------------------------------------------

class SkillDevelopmentAction(Base):
    __tablename__ = "skill_development_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False, index=True)
    skill_gap_reference = Column(String(100), nullable=True)
    action_type = Column(String(50), default=SkillActionType.COURSE.value, nullable=False)
    course_id = Column(String(36), ForeignKey("learning_courses.id"), nullable=True)
    mentoring_program_id = Column(String(36), ForeignKey("mentoring_programs.id"), nullable=True)
    target_level_id = Column(String(36), ForeignKey("skill_levels.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(32), default="PLANNED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    skill = relationship("Skill")
    course = relationship("LearningCourse")


class SkillEvidence(Base):
    __tablename__ = "skill_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False, index=True)
    evidence_type = Column(String(50), default=SkillEvidenceType.COURSE.value, nullable=False)
    source_reference = Column(String(255), nullable=True)
    evidence_date = Column(Date, default=date.today, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person")
    skill = relationship("Skill")
