"""
models_analytics.py - Module 13: Enterprise HR Analytics, Workforce Intelligence & Compliance Reporting Models.

Persisted configuration models for:
- AnalyticsReportDefinition
- AnalyticsDashboard
- AnalyticsWidget
- AnalyticsFilter
- ScheduledReport
- ReportExecution
- ReportExport
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ReportType(str, enum.Enum):
    WORKFORCE = "WORKFORCE"
    HEADCOUNT = "HEADCOUNT"
    ATTRITION = "ATTRITION"
    ATTENDANCE = "ATTENDANCE"
    LEAVE = "LEAVE"
    RECRUITMENT = "RECRUITMENT"
    COMPENSATION = "COMPENSATION"
    PAYROLL = "PAYROLL"
    PERFORMANCE = "PERFORMANCE"
    LEARNING = "LEARNING"
    COMPLIANCE = "COMPLIANCE"
    WORKFORCE_COST = "WORKFORCE_COST"
    CUSTOM = "CUSTOM"


class Visibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    ROLE_BASED = "ROLE_BASED"


class DashboardType(str, enum.Enum):
    EXECUTIVE = "EXECUTIVE"
    HR = "HR"
    MANAGER = "MANAGER"
    FINANCE = "FINANCE"
    RECRUITMENT = "RECRUITMENT"
    COMPLIANCE = "COMPLIANCE"
    CUSTOM = "CUSTOM"


class WidgetType(str, enum.Enum):
    KPI_CARD = "KPI_CARD"
    BAR_CHART = "BAR_CHART"
    LINE_CHART = "LINE_CHART"
    PIE_CHART = "PIE_CHART"
    TABLE = "TABLE"
    FUNNEL = "FUNNEL"


class ScheduleFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class ExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExportFormat(str, enum.Enum):
    CSV = "CSV"
    XLSX = "XLSX"
    PDF = "PDF"
    JSON = "JSON"


class AnalyticsReportDefinition(Base):
    """Configurable report definition."""
    __tablename__ = "analytics_report_definitions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False, default=ReportType.WORKFORCE.value)
    
    # Configuration
    metrics = Column(JSON, nullable=True)      # e.g. ["headcount", "active_employees", "exits"]
    dimensions = Column(JSON, nullable=True)   # e.g. ["department", "location", "legal_entity"]
    filters = Column(JSON, nullable=True)      # e.g. {"status": "ACTIVE", "employment_type": "FULL_TIME"}
    grouping = Column(JSON, nullable=True)     # e.g. ["department"]
    sorting = Column(JSON, nullable=True)      # e.g. [{"field": "headcount", "direction": "desc"}]
    
    # Access and Privacy
    visibility = Column(String(50), nullable=False, default=Visibility.PRIVATE.value)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    allowed_roles = Column(JSON, nullable=True) # e.g. ["SUPER_ADMIN", "HR_ADMIN"]
    min_aggregation_threshold = Column(Integer, default=3, nullable=False)  # Privacy threshold
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    executions = relationship("ReportExecution", back_populates="report_definition", cascade="all, delete-orphan")
    schedules = relationship("ScheduledReport", back_populates="report_definition", cascade="all, delete-orphan")


class AnalyticsDashboard(Base):
    """Configurable analytics dashboard."""
    __tablename__ = "analytics_dashboards"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dashboard_type = Column(String(50), nullable=False, default=DashboardType.HR.value)
    layout = Column(JSON, nullable=True)       # Grid / card positioning
    is_default = Column(Boolean, default=False, nullable=False)
    
    visibility = Column(String(50), nullable=False, default=Visibility.PRIVATE.value)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    allowed_roles = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    widgets = relationship("AnalyticsWidget", back_populates="dashboard", cascade="all, delete-orphan")


class AnalyticsWidget(Base):
    """Visual widget attached to an analytics dashboard."""
    __tablename__ = "analytics_widgets"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    dashboard_id = Column(String, ForeignKey("analytics_dashboards.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    widget_type = Column(String(50), nullable=False, default=WidgetType.KPI_CARD.value)
    metric = Column(String(100), nullable=False)
    dimensions = Column(JSON, nullable=True)
    filters = Column(JSON, nullable=True)
    report_definition_id = Column(String, ForeignKey("analytics_report_definitions.id"), nullable=True)
    position = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    dashboard = relationship("AnalyticsDashboard", back_populates="widgets")


class AnalyticsFilter(Base):
    """Reusable global or dashboard filter configuration."""
    __tablename__ = "analytics_filters"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    filter_key = Column(String(100), nullable=False)   # e.g. "department_id", "legal_entity_id"
    filter_type = Column(String(50), default="DROPDOWN", nullable=False)
    options = Column(JSON, nullable=True)
    default_value = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ScheduledReport(Base):
    """Scheduled automated generation of an analytics report."""
    __tablename__ = "scheduled_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    report_definition_id = Column(String, ForeignKey("analytics_report_definitions.id"), nullable=False, index=True)
    frequency = Column(String(50), nullable=False, default=ScheduleFrequency.MONTHLY.value)
    recipients = Column(JSON, nullable=False)   # ["admin@zeramai.com", "hr_leads"]
    format = Column(String(20), nullable=False, default=ExportFormat.CSV.value)
    status = Column(String(50), nullable=False, default="ACTIVE")   # ACTIVE, PAUSED
    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    report_definition = relationship("AnalyticsReportDefinition", back_populates="schedules")
    executions = relationship("ReportExecution", back_populates="scheduled_report")


class ReportExecution(Base):
    """Record of a report execution run."""
    __tablename__ = "report_executions"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    report_definition_id = Column(String, ForeignKey("analytics_report_definitions.id"), nullable=False, index=True)
    scheduled_report_id = Column(String, ForeignKey("scheduled_reports.id"), nullable=True, index=True)
    executed_by = Column(String, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default=ExecutionStatus.PENDING.value)
    format = Column(String(20), nullable=False, default=ExportFormat.CSV.value)
    row_count = Column(Integer, default=0, nullable=False)
    execution_time_ms = Column(Integer, default=0, nullable=False)
    parameters = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report_definition = relationship("AnalyticsReportDefinition", back_populates="executions")
    scheduled_report = relationship("ScheduledReport", back_populates="executions")
    exports = relationship("ReportExport", back_populates="execution", cascade="all, delete-orphan")


class ReportExport(Base):
    """Downloadable export artifact of a completed report run."""
    __tablename__ = "report_exports"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    execution_id = Column(String, ForeignKey("report_executions.id"), nullable=False, index=True)
    export_format = Column(String(20), nullable=False, default=ExportFormat.CSV.value)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="READY", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution = relationship("ReportExecution", back_populates="exports")
