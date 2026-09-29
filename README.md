# Zeramai Enterprise HRMS (v2.1.0)
### International Multi-Tenant Human Capital Management & Global Payroll Platform

[![Backend Tests](https://img.shields.io/badge/Backend%20Pytest-288%20Passed-brightgreen)](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/backend/tests)
[![Frontend Pages](https://img.shields.io/badge/Next.js%2014-69%20Pages%20Verified-blue)](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/frontend)
[![OpenAPI Routes](https://img.shields.io/badge/OpenAPI%20Routes-625-purple)](http://localhost:8000/docs)
[![Database Tables](https://img.shields.io/badge/Database%20Tables-242-orange)](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/backend/app/models.py)
[![Alembic Head](https://img.shields.io/badge/Alembic%20Head-a31824c94d6e-teal)](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/backend/alembic)

---

## 🌟 Executive Summary

**Zeramai Enterprise HRMS** is an international-standard, production-ready enterprise Human Resource Management System. It delivers an end-to-end, multi-tenant digital workplace covering twenty-one integrated modules—from talent acquisition and effective-dated organizational management to global multi-country payroll, statutory compliance, workforce planning, enterprise learning, and data governance.

---

## 🚀 Key Modules & Capabilities (Modules 1–21)

| Category | Modules | Core Functionality |
| :--- | :--- | :--- |
| **Core & Hierarchy** | Modules 1–4 | Multi-Tenant Data Isolation, Legal Entities, Departments, Locations, RBAC/ABAC Matrix, Job Architecture. |
| **Workforce Operations**| Modules 5–8 | Position Management, Employee Directory, Effective-Dated History, Leave Policy Engine, Biometric/Manual Attendance & Shift Swapping. |
| **Talent Lifecycle** | Modules 9–10 | Full ATS Pipeline (`APPLIED` → `SELECTED`), 1-Click Trainee Conversion, Resignation Workflow, Multi-Department Exit Clearances & Final Settlement. |
| **Compensation & Tax** | Modules 11–12 | Salary Structures, Effective-Dated Compensation Revisions, India Statutory (EPF, ESI, Professional Tax, TDS Section 192 Form 16/24Q). |
| **Finance & Ledgers** | Module 13 | Cost Centers, Department Budget Variance, Automated Double-Entry Payroll Journal Entries ($\sum \text{Debits} == \sum \text{Credits}$). |
| **Enterprise Security** | Modules 14–15 | SAML 2.0 / OIDC SSO (Entra ID, Google, Okta), RFC 7644 SCIM 2.0 Directory Sync, Outbound Webhooks, Data Classification, Retention Schedules, Legal Holds & DSAR. |
| **Service & Relations** | Module 16 | HR Helpdesk Ticketing, Priority SLA Queues, Confidential Internal Deliberation Notes, Whistleblower Grievance Resolution. |
| **Workforce Strategy** | Module 17 | Org Unit Hierarchy, Position Budgeting, Headcount Demand vs. Supply Forecasting, Confidential Restructuring Scenarios. |
| **Learning & Growth** | Module 18 | Course Catalog, Modular Curriculums, Employee Enrollments, Competency Assessments, Certifications & Protected Answer Keys. |
| **Engagement & Culture**| Module 19 | Scheduled Survey Campaigns, Pulse Sentiment Tracking, Peer Recognition & Anonymity Threshold Enforcement ($n \ge 5$). |
| **Comms & Knowledge** | Module 20 | Targeted Enterprise Announcements, Critical Bulletins, Categorized Knowledge Base Articles with Full-Text Search. |
| **Global Operations** | Module 21 | Multi-Country Gross-to-Net Engine across 7 Tier-1 Countries (**USA, GBR, CAN, AUS, SGP, ARE, IND**), Multi-Currency FX Engine, Global Pay Calendars & Encrypted Payslips. |

---

## ⚡ Quickstart Guide (Local Development)

### 1. Prerequisites
- Python 3.11 or 3.12
- Node.js 18.x or 20.x LTS
- Git

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
python -m app.seed_rbac
python -m uvicorn app.main:app --port 8000 --reload
```

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```

### 4. Access the Application
- **Frontend App:** [http://localhost:3000/login](http://localhost:3000/login)
- **Backend API & Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🔑 Demo Login Accounts

All demo accounts use the standard password: `ChangeMe123!`

| Role | Username / Email | Recommended Exploration Tabs |
| :--- | :--- | :--- |
| **Super Admin** | `superadmin@zeramai.com` | Full Administrative Suite, IAM / Integrations, Audit Logs |
| **HR Admin** | `hr@zeramai.com` | Organization, Global Payroll, Statutory Compliance, Workforce Planning, LMS |
| **Hiring Manager** | `manager@zeramai.com` | Team Communications, Team Culture / Engagement, Candidates, Evaluations |
| **Finance** | `finance@zeramai.com` | Cost Centers, Budgets, Payroll Journal Entries, Compensation Revisions |
| **Employee** | `employee@example.com` | Self-Service (`/me`), Leave Balances, Clock-in, My Learning, Helpdesk |

*(Note: The login page includes one-click demo login buttons for rapid switching).*

---

## 🧪 Testing & Quality Assurance

```bash
# Run backend pytest suite (288 tests, 0 failures, 0 errors)
cd backend
pytest -q

# Run frontend production build (69 pages compiled cleanly)
cd frontend
npm run build
```

---

## 📚 Architectural & Operational Documentation

- [**ARCHITECTURE.md**](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/ARCHITECTURE.md) — Master System Architecture, 5-Layer Security, Multi-Tenant Data Schema, Global Payroll Adapter Pipeline, Kubernetes Topology.
- [**STEP_BY_STEP.md**](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/STEP_BY_STEP.md) — End-to-end setup manual, module-by-module workflow walkthroughs, environment config, and troubleshooting.
- [**DOCUMENTATION.md**](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/DOCUMENTATION.md) — Technical specifications for all 21 modules, RBAC authorization matrix, and API route index.
- [**RELEASE_NOTES_v2.0.md**](file:///c:/Users/DELL/Downloads/zeramai-hr1/zeramai-hr/RELEASE_NOTES_v2.0.md) — Historical release baseline notes.
