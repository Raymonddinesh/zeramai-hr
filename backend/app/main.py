from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth, candidates, documents, attendance, leave, evaluations, stipends, employees, audit_logs, job_openings, workflows, scim, organizations, history, onboarding, interviews, offers, shifts, leave_policies, payroll, performance, lms, analytics, notifications, custom_fields, compliance

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # V1: create tables directly. Once schema stabilizes, replace with
    # Alembic migrations (scaffolded in alembic/ — see README) so schema
    # changes are versioned instead of implicit.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Zeramai HR & Employee Onboarding Management System",
    lifespan=lifespan,
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
app.include_router(notifications.router)
app.include_router(custom_fields.router)
app.include_router(compliance.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
