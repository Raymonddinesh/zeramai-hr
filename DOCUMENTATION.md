# Zeramai Enterprise HRMS — Technical Documentation & Module Specifications (v2.1)

---

## 1. System Overview & Purpose

**Zeramai Enterprise HRMS** is an international-standard, multi-tenant Human Resource Management System engineered for enterprise enterprises, multinational corporations, and high-growth organizations. It unifies the entire employee lifecycle—from talent acquisition and preboarding to global multi-country payroll, statutory compliance, workforce planning, learning and competency development, employee engagement, and offboarding.

### Primary Architectural Pillars
- **Strict Multi-Tenant Isolation**: Complete data segregation via server-enforced `tenant_id` context across all 242 relational tables.
- **5-Layer Security & RBAC/ABAC**: Zero-trust API gateway enforcing authentication, tenant boundaries, role-based permissions, attribute-based rules, and object-level IDOR defenses.
- **Global Compliance & Localization**: Native multi-country payroll engine supporting 7 Tier-1 countries (`USA`, `GBR`, `CAN`, `AUS`, `SGP`, `ARE`, `IND`), dynamic foreign exchange (FX) rates, and comprehensive Indian labor law statutory compliance (EPF, ESI, Professional Tax, TDS/Form 16).
- **Enterprise Service & Growth**: Enterprise IAM (SAML/OIDC, SCIM 2.0 RFC 7644), Data Governance (retention schedules, legal holds, DSAR), Workforce Planning scenario models, LMS with competency assessments, and engagement sentiment tracking with anonymity threshold enforcement ($n \ge 5$).

---

## 2. Complete 21 Modules Specification

### Core Platform & Hierarchy (Modules 1–4)
- **Module 1: Multi-Tenant Architecture & Company Profile** (`/api/v3/company-profile`, `/api/organizations`)  
  Root tenant partitioning (`Tenant`), multi-entity statutory configuration (`LegalEntity`), locations, and departments.
- **Module 2: Authentication & Session Lifecycle** (`/api/auth`)  
  JWT bearer token authentication in `HttpOnly`, `SameSite=Lax` cookies, session inspection (`/api/auth/me`), and logout invalidation.
- **Module 3: Role-Based & Attribute-Based Access Control** (`/api/security-admin`)  
  Matrix-based authorization across 5 standard enterprise roles: `SUPER_ADMIN`, `HR_ADMIN`, `HIRING_MANAGER`, `FINANCE`, `EMPLOYEE`.
- **Module 4: Core Organization Architecture & Job Catalog** (`/api/jobs`, `/api/v3/job-architecture`)  
  Job families, job bands, job grades, and interactive organization charts.

### Workforce Operations (Modules 5–8)
- **Module 5: Job Openings & Position Management** (`/api/job-openings`, `/api/v3/positions`)  
  Requisitions, position budgets, and hiring approvals.
- **Module 6: Employee Directory & Effective-Dated History** (`/api/employees`, `/api/history`, `/api/me`)  
  Unified `Person` master identity, effective-dated `Engagement` tracking (promotions, transfers, compensation history), and Employee Self-Service.
- **Module 7: Leave Management & Policy Engine** (`/api/leave`, `/api/v3/leave/policies`)  
  Leave policies, annual accruals, carry-forward rules, compensatory off, and approval workflows.
- **Module 8: Attendance, Time Tracking & Shifts** (`/api/attendance`, `/api/shifts`)  
  Daily clock-in/out, biometric/manual log recording, shift rosters, and shift swapping.

### Talent Acquisition & Offboarding (Modules 9–10)
- **Module 9: ATS & Candidate Pipeline** (`/api/candidates`, `/api/interviews`, `/api/offers`)  
  End-to-end recruitment lifecycle: `APPLIED` → `SCREENING` → `INTERVIEW` → `OFFER` → `SELECTED`, with seamless 1-click conversion into active `Engagement`.
- **Module 10: Exit Management & Offboarding** (`/api/v3/offboarding`, `/api/offboarding-admin`)  
  Resignation submission, multi-department exit clearance checklists (IT, Admin, Finance, HR), asset recovery, and final settlement calculation.

### Compensation, Finance & Compliance (Modules 11–13, 21)
- **Module 11: India Statutory Compliance** (`/api/v3/statutory`, `/api/v3/tax`)  
  Automated compliance engine:
  - **EPF**: 12% employee contribution, employer split (8.33% EPS, 3.67% EPF) with ₹15,000 wage ceiling capping.
  - **ESI**: 0.75% employee, 3.25% employer contribution subject to the ₹21,000 gross monthly wage ceiling.
  - **Professional Tax**: State-specific monthly/annual slabs.
  - **TDS / Income Tax**: Old vs. New tax regime computation, Section 80C/80D/HRA deductions, and quarterly Form 24Q filing preparation.
- **Module 12: Compensation Structures & Benefits** (`/api/v3/compensation`, `/api/v3/benefits`)  
  Salary structures (Base, HRA, DA, Special Allowance), compensation revision cycles with effective dates, and benefit plan enrollments.
- **Module 13: Core Finance, General Ledger & Cost Centers** (`/api/v3/finance`)  
  Cost center allocations, department budget variance tracking, and automated double-entry payroll journal entries ($\sum \text{Debits} == \sum \text{Credits}$).
- **Module 21: Global Multi-Country Payroll & FX Engine** (`/api/v3/global-payroll`)  
  Extensible multi-country gross-to-net payroll engine across 7 Tier-1 countries:
  - **USA**: Federal Income Tax, FICA Social Security (6.2%), Medicare (1.45%), 401(k).
  - **GBR (UK)**: PAYE tax bands, National Insurance Class 1, Auto-Enrolment workplace pensions.
  - **CAN (Canada)**: Federal/Provincial tax brackets, CPP (5.95%), EI (1.66%).
  - **AUS (Australia)**: ATO tax scales, Superannuation Guarantee (11.5%), Medicare levy (2%).
  - **SGP (Singapore)**: CPF age-tiered contribution scales, Skills Development Levy (SDL 0.25%).
  - **ARE (UAE)**: WPS SIF file generation, GPSSA citizen pensions (5%), End of Service Gratuity (EOSG).
  - **IND (India)**: Native statutory integration with EPF, ESI, PT, and Section 192 TDS.
  - **Foreign Exchange (FX)**: Real-time/cached exchange rates across 5 currency pairs.

### Enterprise Governance & Integration (Modules 14–16)
- **Module 14: Enterprise IAM, SSO & SCIM Directory Sync** (`/api/v3/integrations`, `/api/scim/v2`)  
  Identity federation via SAML 2.0 / OIDC (Microsoft Entra ID, Google Workspace, Okta), RFC 7644 SCIM 2.0 user/group provisioning, outbound HMAC-SHA256 webhooks, and automatic credential masking.
- **Module 15: Enterprise Data Governance & Privacy** (`/api/v3/governance`)  
  Data classifications (Public, Internal, Confidential, Restricted), automated document retention schedules, litigation legal hold overrides, and Data Subject Access Requests (DSAR).
- **Module 16: HR Service Desk & Employee Relations** (`/api/v3/hr-requests`, `/api/v3/employee-relations`)  
  Employee helpdesk ticketing with SLA priority queues, category routing, confidential HR internal deliberation notes (hidden from employees), and formal grievance resolution panels.

### Workforce Intelligence & Growth (Modules 17–20)
- **Module 17: Workforce Planning & Organizational Design** (`/api/v3/workforce-planning`)  
  Org unit structures, position management, headcount demand vs. supply forecasting, and confidential restructuring scenario models.
- **Module 18: Enterprise Learning, Competencies & LMS** (`/api/v3/learning`)  
  Course catalog browsing, modular curriculums, employee enrollments, competency assessments, certifications, and secure assessment answer keys.
- **Module 19: Employee Engagement, Culture & Recognition** (`/api/v3/engagement`)  
  Survey templates, scheduled pulse sentiment campaigns, peer recognition programs, cultural values, and strict anonymity threshold protection ($n \ge 5$).
- **Module 20: Enterprise Internal Communications & Knowledge Base** (`/api/v3/communications`, `/api/v3/knowledge`)  
  Targeted enterprise announcements, critical bulletin alerts, categorized knowledge base articles with full-text search, and authoring workflows.

---

## 3. Role-Based Access Control (RBAC) Master Matrix

| Feature / Domain | SUPER_ADMIN | HR_ADMIN | HIRING_MANAGER | FINANCE | EMPLOYEE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **System Dashboard** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Company Legal Profile & Org Units** | ✅ | ✅ | View Only | View Only | View Only |
| **Candidate Creation & Conversion** | ✅ | ✅ | — | — | — |
| **Interviews & Candidate Ratings** | ✅ | ✅ | ✅ | — | — |
| **Employee Self-Service (`/me`, Leave, Clock-in)** | ✅ | ✅ | ✅ | ✅ | ✅ (Own Data) |
| **Manager Self-Service (Team Pulse & Comms)** | ✅ | ✅ | ✅ | — | — |
| **Company Salary Configurations** | ✅ | ✅ | ❌ (403) | ✅ | ❌ (403) |
| **Global Payroll Runs & Calendars** | ✅ | ✅ | ❌ (403) | ✅ | ❌ (403) |
| **India Statutory Compliance Filings** | ✅ | ✅ | ❌ (403) | ✅ | ❌ (403) |
| **General Ledger & Cost Centers** | ✅ | ✅ | ❌ (403) | ✅ | ❌ (403) |
| **Workforce Planning Scenarios** | ✅ | ✅ | ❌ (403) | ❌ (403) | ❌ (403) |
| **Course Catalog & Enrollments** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Engagement Surveys (Participate)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Engagement Team Analytics ($n \ge 5$)** | ✅ | ✅ | ✅ (Aggregated) | — | — |
| **Publish Enterprise Announcements** | ✅ | ✅ | ❌ (403) | ❌ (403) | ❌ (403) |
| **HR Service Desk (Confidential Internal Notes)**| ✅ | ✅ | ❌ (403) | ❌ (403) | ❌ (Hidden) |
| **Data Governance & Legal Holds** | ✅ | ✅ | ❌ (403) | ❌ (403) | ❌ (403) |
| **IAM, SSO & Webhook Management** | ✅ | ✅ | ❌ (403) | ❌ (403) | ❌ (403) |

---

## 4. API Endpoints & Contract Reference

All API routes follow the `/api/v3/...` standard (with core identity and ATS routes at `/api/...`).

### Interactive OpenAPI Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON Schema**: `http://localhost:8000/openapi.json` (625 registered routes)

### Key Route Groups
- **Authentication**: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- **Global Payroll**: `GET /api/v3/global-payroll/countries`, `GET /api/v3/global-payroll/fx-rates`, `POST /api/v3/global-payroll/calculate`, `GET /api/v3/global-payroll/calendars`, `GET /api/v3/global-payroll/results`
- **Statutory**: `GET /api/v3/statutory/schemes`, `GET /api/v3/statutory/rules`, `POST /api/v3/statutory/calculate`, `GET /api/v3/statutory/filings`
- **Finance**: `GET /api/v3/finance/cost-centers`, `GET /api/v3/finance/budgets`, `GET /api/v3/finance/payroll-journals`
- **Workforce Planning**: `GET /api/v3/workforce-planning/org-units`, `GET /api/v3/workforce-planning/positions`, `GET /api/v3/workforce-planning/scenarios`
- **Learning**: `GET /api/v3/learning/courses`, `POST /api/v3/learning/enrollments`, `GET /api/v3/learning/assessments`
- **Engagement**: `GET /api/v3/engagement/templates`, `GET /api/v3/engagement/campaigns`, `GET /api/v3/engagement/recognition/programs`
- **Communications & Knowledge**: `GET /api/v3/communications/announcements`, `GET /api/v3/knowledge/categories`, `GET /api/v3/knowledge/articles`
- **Governance**: `GET /api/v3/governance/data-classifications`, `GET /api/v3/governance/retention-policies`, `GET /api/v3/governance/legal-holds`
- **IAM / Integrations**: `GET /api/v3/integrations/providers`, `GET /api/v3/integrations/connections`, `GET /api/v3/integrations/webhooks`

---

## 5. Security & Verification Quality Standards

- **Unit & Integration Test Suite**: 288 backend tests with 100% pass rate (`pytest -q`).
- **Frontend Build Quality**: 69/69 Next.js pages statically prerendered with 0 TypeScript/ESLint build errors (`npm run build`).
- **Alembic Database Head**: `a31824c94d6e` encompassing 242 relational tables.
- **Tenant Isolation**: Verified zero data leakage across distinct tenant accounts and robust Insecure Direct Object Reference (IDOR) rejection (HTTP 403 / 404).
- **Latency Benchmarks**: Core read operations average under 10ms.
