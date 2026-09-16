from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth, candidates, documents, attendance, leave, evaluations, stipends, employees, audit_logs, job_openings, workflows, scim, organizations, history, onboarding

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


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
