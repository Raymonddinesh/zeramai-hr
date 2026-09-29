# Zeramai Enterprise HRMS — Master System Architecture Document (v2.1 Production Baseline)

**Document Version:** 2.1.0  
**Target Platform:** Zeramai Enterprise Multi-Tenant HRMS Platform  
**Architecture Scope:** Complete Modules 1–21 Integration  
**Alembic Head:** `a31824c94d6e`  
**Database Schema:** 242 Relational Tables (PostgreSQL / SQLite)  
**API Surface:** 625 OpenAPI Endpoints (`/api/v3/...`)  
**Frontend Compilation:** Next.js 14.2.35 App Router (69 Verified Pages)  
**Status:** Certified Production Architecture Specification  

---

## 1. High-Level System Architecture & Topology

Zeramai HRMS is architected as an **international-standard, multi-tenant SaaS platform** designed for enterprise human capital management, statutory compliance, workforce planning, and multi-country payroll. It adopts a decoupled presentation and business API topology with enterprise-grade tenant isolation, granular RBAC/ABAC authorization, automated workflow orchestration, and immutable audit logging.

```mermaid
graph TD
    Client[Next.js 14 App Router\nTypeScript + Tailwind CSS\n69 Pages / Port 3000] -->|HTTPS / REST API / SWR| Ingress[Ingress Gateway / NGINX / Cloudflare]
    Ingress -->|Session / Cookie Proxy /api/*| API[FastAPI Application Services\nPython 3.11+ / 625 Routes\nPort 8000]
    
    API -->|Tenant-Keyed Queries| DB[(PostgreSQL Primary DB\n242 Relational Schemas & Tables)]
    API -->|Distributed Cache / Session| Cache[(Redis Cluster\nRate Limiting, FX Rates & Token Cache)]
    API -->|Event Bus / Async Workflows| Queue[(RabbitMQ / Celery\nAsync Workflows & Webhooks)]
    API -->|Encrypted Document Vault| ObjectStore[(Azure Blob / AWS S3 / Local\nHMAC-Verified Proxy Streaming)]
    API -->|People Analytics Index| Search[(OpenSearch / Elasticsearch\nWorkforce Intelligence Index)]

    AuditEngine[Append-Only Audit Engine] -->|SIEM Log Stream| SIEM[Datadog / Splunk / CloudWatch]
    API --> AuditEngine
```

---

## 2. Platform Core Architecture & The 21 Modules

The platform is structured into twenty-one specialized, loosely-coupled modules sharing a unified tenant and identity foundation:

```mermaid
flowchart TD
    subgraph CoreFoundation ["Core Foundation (Modules 1–4)"]
        M1["1. Multi-Tenant Identity & Legal Profile"]
        M2["2. Authentication & Session Store"]
        M3["3. RBAC/ABAC Security Matrix"]
        M4["4. Core Organization Architecture"]
    end

    subgraph WorkforceOps ["Workforce Operations (Modules 5–8)"]
        M5["5. Job Architecture & Catalog"]
        M6["6. Employee Directory & Profile"]
        M7["7. Leave Management Engine"]
        M8["8. Attendance & Shift Tracking"]
    end

    subgraph TalentLifecycle ["Talent Lifecycle (Modules 9–10)"]
        M9["9. ATS & Candidate Pipeline"]
        M10["10. Exit Management & Offboarding"]
    end

    subgraph CompFinance ["Compensation, Finance & Payroll (Modules 11–13, 21)"]
        M11["11. India Statutory Compliance"]
        M12["12. Compensation & Benefits"]
        M13["13. General Ledger & Cost Centers"]
        M21["21. Global Multi-Country Payroll"]
    end

    subgraph EnterpriseService ["Service & Relations (Modules 14–16)"]
        M14["14. Enterprise IAM & SSO"]
        M15["15. Data Governance & Privacy"]
        M16["16. HR Service Desk & Relations"]
    end

    subgraph IntelligenceGrowth ["Growth & Intelligence (Modules 17–20)"]
        M17["17. Workforce Planning & Scenarios"]
        M18["18. Enterprise LMS & Competencies"]
        M19["19. Engagement & Anonymized Surveys"]
        M20["20. Comms & Knowledge Base"]
    end

    CoreFoundation --> WorkforceOps
    CoreFoundation --> TalentLifecycle
    CoreFoundation --> CompFinance
    CoreFoundation --> EnterpriseService
    CoreFoundation --> IntelligenceGrowth
```

### Module Breakdown Matrix

| Module | Functional Domain | Primary Entities & Models | API Routes Prefix |
| :--- | :--- | :--- | :--- |
| **M1** | Identity & Hierarchy | `Tenant`, `LegalEntity`, `Person`, `User` | `/api/v3/company-profile`, `/api/organizations` |
| **M2** | Auth & Session | `User`, `AuditLog`, `Session` | `/api/auth/login`, `/api/auth/me` |
| **M3** | RBAC / ABAC | `Role`, `Permission`, `RolePermission` | `/api/security-admin`, `/api/auth` |
| **M4** | Org Structure | `Department`, `Location`, `Position` | `/api/organizations`, `/api/departments` |
| **M5** | Job Architecture | `JobBand`, `JobGrade`, `JobProfile` | `/api/jobs`, `/api/v3/job-architecture` |
| **M6** | Employee Directory | `Engagement`, `PersonDocument`, `History` | `/api/employees`, `/api/me`, `/api/history` |
| **M7** | Leave Engine | `LeavePolicy`, `LeaveBalance`, `LeaveRequest`| `/api/leave`, `/api/v3/leave/policies` |
| **M8** | Attendance & Shifts | `AttendanceRecord`, `Shift`, `ShiftRoster`| `/api/attendance`, `/api/shifts` |
| **M9** | Recruitment / ATS | `Candidate`, `Interview`, `Offer` | `/api/candidates`, `/api/interviews`, `/api/offers` |
| **M10** | Exit & Offboarding | `Resignation`, `ExitClearance`, `Settlement` | `/api/v3/offboarding`, `/api/offboarding-admin` |
| **M11** | India Statutory | `EPFScheme`, `ESIScheme`, `PTRule`, `TDSFiling` | `/api/v3/statutory`, `/api/v3/tax` |
| **M12** | Comp & Benefits | `SalaryStructure`, `CompRevision`, `BenefitPlan`| `/api/v3/compensation`, `/api/v3/benefits` |
| **M13** | Finance & GL | `CostCenter`, `Budget`, `PayrollJournal` | `/api/v3/finance` |
| **M14** | IAM, SSO & SCIM | `IdPConfig`, `DirectoryConnection`, `Webhook` | `/api/v3/integrations`, `/api/scim/v2` |
| **M15** | Governance & DSAR | `DataClassification`, `RetentionPolicy`, `LegalHold` | `/api/v3/governance` |
| **M16** | HR Service Desk | `HRServiceRequest`, `InternalNote`, `Grievance` | `/api/v3/hr-requests`, `/api/v3/employee-relations` |
| **M17** | Workforce Planning | `OrgUnit`, `Position`, `Scenario`, `Headcount`| `/api/v3/workforce-planning` |
| **M18** | LMS & Career | `Course`, `Enrollment`, `Assessment`, `Skill` | `/api/v3/learning` |
| **M19** | Engagement & Culture | `SurveyTemplate`, `Campaign`, `Recognition` | `/api/v3/engagement` |
| **M20** | Comms & Knowledge | `Announcement`, `KnowledgeArticle`, `Category`| `/api/v3/communications`, `/api/v3/knowledge` |
| **M21** | Global Payroll | `CountryConfig`, `FXRate`, `PayGroup`, `Calendar` | `/api/v3/global-payroll` |

---

## 3. 5-Layer Security & Multi-Tenant Defense Architecture

Security is enforced at platform boundaries before business logic executes. Every request passes through 5 distinct evaluation checkpoints:

```mermaid
flowchart LR
    Req[Incoming HTTP Request] --> Layer1[1. Authentication\nJWT Cookie / OAuth2 / SAML]
    Layer1 --> Layer2[2. Tenant Isolation Context\nServer-Derived tenant_id]
    Layer2 --> Layer3[3. Role-Based Access Control\nRBAC Permissions]
    Layer3 --> Layer4[4. Attribute-Based Access Control\nABAC Context & Anonymity]
    Layer4 --> Layer5[5. Object Ownership Check\nPerson / Resource Owner ID]
    Layer5 --> Audit[6. Immutable Audit Log\nAuditResult.SUCCESS / DENIED]
```

### Security Layer Definitions

1. **Layer 1 — Authentication**: Decodes JWT `access_token` from HTTP-only, `SameSite=Lax` cookie. Supports SAML 2.0 / Okta / Entra ID SSO.
2. **Layer 2 — Tenant Isolation Context**: Resolves tenant identity from authenticated session (`current_user.tenant_id`). Client-supplied `tenant_id` query parameters are strictly forbidden from overriding server context.
3. **Layer 3 — Role-Based Access Control (RBAC)**: Checks assigned permission codes (`has_permission(user, code, db)`) via `Role` → `RolePermission` → `Permission` join across standard enterprise roles (`SUPER_ADMIN`, `HR_ADMIN`, `HIRING_MANAGER`, `FINANCE`, `EMPLOYEE`).
4. **Layer 4 — Attribute-Based Access Control (ABAC)**: Evaluates dynamic attributes (department, office location, supervisory hierarchy) and enforces survey anonymity thresholds ($n \ge 5$ respondents).
5. **Layer 5 — Object-Level Ownership (IDOR Defense)**: Enforces `person_id == current_user.person_id` for self-service operations (payslips, tax declarations, performance records) to prevent Insecure Direct Object Reference vulnerabilities.
6. **Layer 6 — Immutable Audit Logging**: Automatically records all operations (Actor, IP, Entity, Action, Changeset, Result: `SUCCESS`, `DENIED`, `FAILURE`) into the append-only `audit_logs` table.

---

## 4. Multi-Tenant Data Architecture & Relational Model

The system enforces a **Shared Database, Tenant-Keyed Isolation Schema** model across all 242 relational tables:

```mermaid
erDiagram
    TENANT ||--o{ LEGAL_ENTITY : owns
    LEGAL_ENTITY ||--o{ ORG_UNIT : structures
    ORG_UNIT ||--o{ POSITION : defines
    TENANT ||--o{ USER : contains
    USER ||--o| PERSON : links
    PERSON ||--o{ ENGAGEMENT : employs
    ENGAGEMENT ||--o{ COMPENSATION_RECORD : pays
    ENGAGEMENT ||--o{ GLOBAL_PAYROLL_ASSIGNMENT : assigns
    ENGAGEMENT ||--o{ ATTENDANCE_RECORD : logs
    ENGAGEMENT ||--o{ LEAVE_REQUEST : requests
    ENGAGEMENT ||--o{ LEARNING_ENROLLMENT : completes
    ENGAGEMENT ||--o{ HR_SERVICE_REQUEST : submits
```

### Core Hierarchy Design
- **`Tenant`**: Root SaaS account partition (e.g., *Zeramai Enterprise*).
- **`LegalEntity`**: Statutory corporate entity registered in a specific jurisdiction (country code, tax ID, registration number, base currency).
- **`Person`**: Unified human master identity preserving lifelong personal records across multiple roles, re-hires, or subsidiary transfers.
- **`User`**: System authentication principal (credentials, MFA, linked `person_id`, assigned roles).
- **`Engagement`**: Effective-dated employment contract (designation, department, manager, employment status, compensation tier).

---

## 5. Global Multi-Country Payroll & Compliance Architecture

The Global Payroll Engine (Module 21) operates as an extensible calculation pipeline supporting **7 Tier-1 countries**:

```mermaid
graph TD
    Input[Gross Earnings, Base Salary, Overtime, Allowances] --> Engine{Country Engine Resolver}
    
    Engine --> IND[India Statutory Adapter\nEPF 12%, ESI 0.75%, PT, TDS Section 192]
    Engine --> USA[USA Adapter\nFederal FIT, FICA Social Security 6.2%, Medicare 1.45%, 401k]
    Engine --> GBR[UK Adapter\nPAYE Tax Bands, National Insurance Class 1, Auto-Enrolment Pension]
    Engine --> CAN[Canada Adapter\nFederal/Provincial Tax, CPP 5.95%, EI 1.66%]
    Engine --> AUS[Australia Adapter\nATO Resident Scales, Superannuation Guarantee 11.5%, Medicare 2%]
    Engine --> SGP[Singapore Adapter\nCPF Age-Tiered Citizen/PR, SDL 0.25%, Non-resident Flat/Progressive]
    Engine --> ARE[UAE Adapter\nWPS SIF Generation, GPSSA 5% Citizen, End of Service Gratuity]

    IND --> Calc[Gross-to-Net Engine\nStatutory Deductions, Net Pay, Employer Taxes]
    USA --> Calc
    GBR --> Calc
    CAN --> Calc
    AUS --> Calc
    SGP --> Calc
    ARE --> Calc

    Calc --> FX[Multi-Currency FX Converter\nUSD, GBP, CAD, AUD, SGD, AED, INR]
    FX --> Ledger[Double-Entry General Ledger Journal Generator]
    Ledger --> GL[(Finance GL: Sum Debits == Sum Credits)]
    Calc --> Payslip[PDF & Web Payslip Generator\nEncrypted Employee Self-Service Archive]
```

---

## 6. Frontend Architecture & Next.js 14 App Router

The user interface is built on **Next.js 14 App Router** with TypeScript and Tailwind CSS, featuring **69 fully static/prerendered pages**:

```mermaid
flowchart TD
    subgraph UI ["Frontend Layout Structure (frontend/app)"]
        AUTH["/login (Public Auth & Demo Switcher)"]
        APP["/(app) Authenticated Root Layout"]
        
        APP --> DASH["/dashboard (Executive KPI Cards)"]
        APP --> ESS["/me, /attendance, /leave (Employee Portal)"]
        APP --> MSS["/communications/team, /engagement/team (Manager Hub)"]
        APP --> HR["/organization, /jobs, /candidates, /offboarding (HR Core)"]
        APP --> PAY["/global-payroll, /admin/global-payroll, /statutory, /tax (Payroll)"]
        APP --> FIN["/finance (Cost Centers, Budgets, GL Journals)"]
        APP --> WF["/workforce-planning (Org Design & Headcount Scenarios)"]
        APP --> LMS["/learning (Course Catalog, My Learning, Certifications)"]
        APP --> ENG["/engagement (Surveys, Pulse, Recognition, Culture)"]
        APP --> COM["/communications, /knowledge (Enterprise Announcements & Wiki)"]
        APP --> GOV["/governance (Retention, Legal Holds, DSAR)"]
        APP --> IAM["/settings/integrations (SSO, SCIM, Webhooks, API Keys)"]
    end

    subgraph ClientLayer ["Client State & Communication"]
        AUTHCTX["AuthContext (JWT Session & Active Role)"]
        PROXY["Next.js Proxy Rewrites (next.config.mjs -> Port 8000)"]
        SWR["SWR Caching & Revalidation"]
    end

    UI --> AUTHCTX
    UI --> SWR
    SWR --> PROXY
```

---

## 7. Infrastructure, Containerization & CI/CD Deployment

```mermaid
graph TD
    subgraph Host ["Containerized Infrastructure (Docker Compose / Kubernetes)"]
        FE[frontend: Next.js 14 Node.js Container\nPort 3000]
        BE[backend: FastAPI Uvicorn Container\nPort 8000]
        DB[(db: PostgreSQL 16 Alpine\nPort 5432)]
        CACHE[(cache: Redis 7 Alpine\nPort 6379)]
    end

    ClientBrowser[Web Browser / Mobile Viewport] -->|Port 3000| FE
    FE -->|Internal Network /api/*| BE
    BE --> DB
    BE --> CACHE
```

### Production Deployment Standards
- **Stateless Application Tier**: Backend pods scale horizontally behind a load balancer; session state is managed via signed JWTs and Redis token blacklist.
- **Database Migrations**: Managed via Alembic (`alembic upgrade head`) before traffic shift.
- **Zero-Trust Network**: Database and cache instances are unreachable from public networks; ingress routes exclusively through reverse proxies with TLS 1.3 encryption.
