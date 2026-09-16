# Zeramai HR & Employee Onboarding Management System
## Software Specification, Purpose & Architecture Documentation

---

### 1. Executive Summary

**Zeramai HR** is an enterprise-grade **Human Resource & Employee Onboarding Management System**. It provides a secure, role-based platform designed to manage the full lifecycle of human capital—from initial candidate recruitment and onboarding to active employee management, document compliance, attendance, leave tracking, performance evaluations, and stipend disbursements.

---

### 2. Primary Purpose & Business Value

The platform solves core operational challenges faced by HR departments, finance teams, hiring managers, and employees:

| Business Need | How Zeramai HR Fulfills It |
|---|---|
| **Recruitment to Onboarding** | Tracks candidate pipelines from application to selection, and seamlessly converts selected candidates into formal engineering/graduate trainees without destroying historical recruitment records. |
| **Strict Security & Compliance** | Protects sensitive identity documents (PAN, Aadhaar, Bank Proofs) using object-level authorization and private, non-public streaming proxy downloads (no public S3 URLs). |
| **Fine-Grained Governance (RBAC)** | Enforces a matrix-based Role-Based Access Control model across 5 distinct roles (`SUPER_ADMIN`, `HR_ADMIN`, `HIRING_MANAGER`, `FINANCE`, `EMPLOYEE`). |
| **Full Auditability & Anti-Repudiation** | Automatically records an append-only audit trail of every sensitive action, login attempt, data update, and permission denial for regulatory compliance. |
| **Employee Self-Service** | Empowers employees and trainees to view their profile, log attendance, request leaves, upload required onboarding documents, and track their stipend status. |

---

### 3. Software Architecture & Technology Stack

Zeramai HR is architected as a decoupled, multi-tier system with modern web technologies:

```mermaid
graph TD
    Client[Next.js 14 Frontend\nApp Router + Tailwind CSS\nhttp://localhost:3000] -->|Proxy Rewrites /api/*| Backend[FastAPI Backend\nPython 3.11/3.12\nhttp://localhost:8000]
    Backend -->|SQLAlchemy ORM| DB[(Database Layer\nSQLite Dev / PostgreSQL Prod)]
    Backend -->|Local / S3 Provider| Storage[(Private Object Storage\nNo Public URLs)]
    Backend -->|Append-Only Logs| Audit[(Audit Trail Table)]
```

#### Tech Stack Detail
- **Frontend Framework**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **State & Data Fetching**: SWR + Axios (proxying via `next.config.mjs`)
- **Backend Framework**: FastAPI (Python 3.11+) with Async Lifespan Handler
- **Database ORM**: SQLAlchemy 2.0 (Compatible with SQLite for dev & PostgreSQL for production)
- **Authentication**: JWT stored in `HttpOnly`, `SameSite=Lax` session cookies
- **Containerization**: Docker & Docker Compose (`db`, `backend`, `frontend`)

---

### 4. Core Features & Module Breakdown

#### A. Authentication & Session Security (`/api/auth`)
- Public login endpoint (`POST /api/auth/login`) with brute-force resistance.
- Token issued in secure `HttpOnly` cookie to eliminate XSS token theft risks.
- Session verification endpoint (`GET /api/auth/me`).

#### B. Recruitment & Candidate Pipeline (`/api/candidates`)
- Create candidate records linked to unified human `Person` records.
- Transition status: `APPLIED` → `SCREENING` → `INTERVIEW` → `SELECTED`.
- One-click conversion from `SELECTED` candidate to active `Engagement` (Engineering Trainee).

#### C. Secure Document Management (`/api/documents`)
- Private file storage using opaque, non-guessable storage keys (`storage.py`).
- Streaming proxy endpoint (`GET /api/documents/{id}/download`) — authorization re-checked on every request.
- Classification of sensitive identity documents (`pan`, `aadhaar`, `bank_proof`) with elevated permission requirements.

#### D. Attendance Tracking (`/api/attendance`)
- Daily attendance logging (`PRESENT`, `ABSENT`, `HALF_DAY`, `ON_LEAVE`, `HOLIDAY`).
- Multi-role support: HR/Admin can record for any person; Employees can log their own status.

#### E. Leave Management (`/api/leave`)
- Leave application submission with type classification (`CASUAL`, `SICK`, `EARNED`, `UNPAID`, etc.).
- Approval workflow: HR/Admin can review, approve, or reject leave requests with review notes.

#### F. Performance Evaluations (`/api/evaluations`)
- Evaluation cycle creation (`DRAFT` → `SUBMITTED` → `ACKNOWLEDGED`).
- Rating scale (1.0 to 5.0) with detailed performance comments.

#### G. Stipend & Payroll Management (`/api/stipends`)
- Monthly stipend issuance for trainees and interns (`PENDING` → `APPROVED` → `PAID`).
- Finance & HR authorization for approval and disbursement tracking.

#### H. Immutable Audit Logging (`/api/audit-logs`)
- Automatic entry creation for every key business event and access denial.
- Filterable by entity, action, date, and result (`SUCCESS`, `FAILURE`, `DENIED`).

---

### 5. Role-Based Access Control (RBAC) Matrix

| Module / Permission | SUPER_ADMIN | HR_ADMIN | HIRING_MANAGER | FINANCE | EMPLOYEE |
|---|:---:|:---:|:---:|:---:|:---:|
| **Dashboard View** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Candidate Create & Convert** | ✅ | ✅ | — | — | — |
| **Candidate View & Select** | ✅ | ✅ | ✅ | — | — |
| **Document Upload (Any)** | ✅ | ✅ | — | — | — |
| **Document Download (Any)** | ✅ | ✅ | — | — | — |
| **Self-Service Upload/Download** | — | — | — | — | ✅ |
| **Attendance Log & View** | ✅ | ✅ | — | — | ✅ (Own) |
| **Leave Apply & Approve** | ✅ | ✅ | — | — | ✅ (Apply) |
| **Evaluations Create & Submit** | ✅ | ✅ | ✅ | — | — |
| **Stipend Create & Approve** | ✅ | ✅ | — | ✅ | — |
| **Audit Logs View** | ✅ | ✅ | — | — | — |

---

### 6. Summary of Operational Interfaces

- **Web Application URL**: [http://localhost:3000](http://localhost:3000)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI Specification**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
