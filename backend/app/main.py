from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.config import settings
import os
from app import models_ess, models_asset

# Ensure a fresh test database by deleting existing file if present
if settings.database_url.startswith('sqlite:///'):
    db_path = settings.database_url.replace('sqlite:///', '')
    if os.path.isfile(db_path):
        os.remove(db_path)

from app.routers import auth, candidates, documents, attendance, leave, evaluations, stipends, employees, audit_logs, job_openings, workflows, scim, organizations, history, onboarding, interviews, offers, shifts, leave_policies, payroll, performance, lms, analytics, reports, dashboards, notifications, custom_fields, compliance, statutory, compliance_calendar, localization, security_admin, ai_suite, manager_self_service, hr_service_desk, offboarding, employee_self_service, compensation, benefits, hr_policies, employee_relations, tax, company_legal_profile, integrations, scim_v2, governance, finance, workforce_planning, learning, engagement, knowledge, communications, global_payroll

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # V1: create tables directly. Once schema stabilizes, replace with
    # Alembic migrations (scaffolded in alembic/ — see README) so schema
    # changes are versioned instead of implicit.
    # Ensure fresh schema for tests: drop existing tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Zeramai HR & Employee Onboarding Management System",
    version="2.0.0",
    lifespan=lifespan,
    debug=True,
)

app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(documents.router)
app.include_router(attendance.router)
app.include_router(leave.router)
app.include_router(evaluations.router)
app.include_router(stipends.router)
app.include_router(employees.router)
app.include_router(audit_logs.router)
app.include_router(job_openings.router)
app.include_router(workflows.router)
app.include_router(scim.router)
app.include_router(organizations.router)
app.include_router(history.router)
app.include_router(onboarding.router)
app.include_router(interviews.router)
app.include_router(offers.router)
app.include_router(shifts.router)
app.include_router(leave_policies.router)
app.include_router(payroll.router)
app.include_router(performance.router)
app.include_router(lms.router)
app.include_router(analytics.router)
app.include_router(reports.router)
app.include_router(dashboards.router)
app.include_router(notifications.router)
app.include_router(custom_fields.router)
app.include_router(compliance.router)
app.include_router(statutory.router)
app.include_router(compliance_calendar.router)
app.include_router(localization.router)
app.include_router(security_admin.router)
app.include_router(ai_suite.router)
app.include_router(manager_self_service.router)
app.include_router(hr_service_desk.router)
app.include_router(offboarding.router)
app.include_router(employee_self_service.router)
app.include_router(compensation.router)
app.include_router(benefits.router)
app.include_router(hr_policies.router)
app.include_router(employee_relations.router)
app.include_router(tax.router)
app.include_router(company_legal_profile.router)
app.include_router(integrations.router)
app.include_router(scim_v2.router)
app.include_router(governance.router)
app.include_router(finance.router)
app.include_router(workforce_planning.router)
app.include_router(learning.router)
app.include_router(engagement.router)
app.include_router(knowledge.router)
app.include_router(communications.router)
app.include_router(global_payroll.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
