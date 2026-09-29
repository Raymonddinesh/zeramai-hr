# Zeramai Enterprise HRMS — Complete Step-by-Step Setup & Operations Guide (v2.1)

This comprehensive guide takes you step-by-step from zero to a fully operational **Zeramai Enterprise HRMS (Modules 1–21)** environment on your local machine or staging server.

---

## Table of Contents
1. [Prerequisites & System Requirements](#1-prerequisites--system-requirements)
2. [Step 1: Clone & Inspect Repository](#step-1-clone--inspect-repository)
3. [Step 2: Backend Setup & Python Environment](#step-2-backend-setup--python-environment)
4. [Step 3: Database Migrations & Initial Seeding](#step-3-database-migrations--initial-seeding)
5. [Step 4: Frontend Setup & Node.js Environment](#step-4-frontend-setup--nodejs-environment)
6. [Step 5: Starting the Application Servers](#step-5-starting-the-application-servers)
7. [Step 6: Verifying Health & Opening the Browser](#step-6-verifying-health--opening-the-browser)
8. [Step 7: Demo Login Accounts & Role Matrix](#step-7-demo-login-accounts--role-matrix)
9. [Step 8: End-to-End Workflow Testing Guide (Modules 1–21)](#step-8-end-to-end-workflow-testing-guide-modules-121)
10. [Step 9: Running Full Test & Quality Assurance Suites](#step-9-running-full-test--quality-assurance-suites)
11. [Step 10: Stopping the Application](#step-10-stopping-the-application)
12. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## 1. Prerequisites & System Requirements

Ensure the following tools are installed on your workstation:
- **Operating System:** Windows 10/11, macOS, or Linux (Ubuntu 22.04+ recommended)
- **Python:** Version **3.11** or **3.12** (`python --version`)
- **Node.js:** Version **18.x** or **20.x LTS** (`node --version`)
- **Package Managers:** `pip` (Python) and `npm` (Node.js)
- **Git:** Version 2.30+ (`git --version`)

---

## Step 1: Clone & Inspect Repository

Open your terminal or PowerShell and navigate to your workspace:
```bash
git clone https://github.com/Raymonddinesh/zeramai-hr.git
cd zeramai-hr
```

The repository structure:
```
zeramai-hr/
├── backend/            # FastAPI Python 3.11 Backend (625 routes, 242 tables)
│   ├── alembic/        # Alembic database migration versions
│   ├── app/            # Application routers, models, schemas, services
│   ├── tests/          # Pytest suite (288 tests)
│   ├── requirements.txt
│   └── .env.example
├── frontend/           # Next.js 14 App Router Frontend (69 pages)
│   ├── app/            # Next.js routes & page layouts
│   ├── components/     # Reusable UI components & Sidebar
│   ├── package.json
│   └── next.config.mjs # API rewrite proxy to backend
├── ARCHITECTURE.md     # Production architecture specification
├── DOCUMENTATION.md    # Module specifications & reference
└── STEP_BY_STEP.md     # This setup & operations manual
```

---

## Step 2: Backend Setup & Python Environment

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. *(Recommended)* Create and activate a Python virtual environment:
   - **Windows:**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *(For local testing with SQLite, the default values in `.env` require no changes).*

---

## Step 3: Database Migrations & Initial Seeding

1. Apply the latest database schema migrations (Alembic head `a31824c94d6e`):
   ```bash
   alembic upgrade head
   ```

2. Seed the 5 standard demo accounts and enterprise module seed data:
   ```bash
   python -m app.seed
   ```
   *Output: `Seeded 5 demo users, integrations catalog, Module 15 governance policies, Module 16 finance defaults, Module 17 workforce models, Module 18 learning catalog, Module 19 engagement platform, Module 20 knowledge/communications, and Module 21 global payroll.`*

3. Seed the RBAC role-permission authorization matrix:
   ```bash
   python -m app.seed_rbac
   ```
   *Output: `RBAC seed completed successfully.`*

---

## Step 4: Frontend Setup & Node.js Environment

Open a new terminal window and navigate to the `frontend` directory:
```bash
cd frontend
```

1. Install frontend npm dependencies:
   ```bash
   npm install
   ```

2. Verify that Next.js proxy rewrites point to `http://localhost:8000` (configured in `next.config.mjs`).

---

## Step 5: Starting the Application Servers

### Terminal 1 — Start the Backend Server:
From the `backend` directory:
```bash
python -m uvicorn app.main:app --port 8000 --reload
```
You should see:
```
INFO:     Started server process
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

> **Important Note for SQLite Dev:** Because the development lifespan reinitializes SQLite tables upon fresh startup, run the seed scripts if you restart the server:
> ```bash
> python -m app.seed
> python -m app.seed_rbac
> ```

### Terminal 2 — Start the Frontend Server:
From the `frontend` directory:
```bash
npm run dev
```
You should see:
```
▲ Next.js 14.2.35
- Local: http://localhost:3000
✓ Ready in 2-3s
```

---

## Step 6: Verifying Health & Opening the Browser

1. Verify backend health:
   - Open [http://localhost:8000/api/health](http://localhost:8000/api/health) — returns `{"status": "ok"}`
   - Open [http://localhost:8000/docs](http://localhost:8000/docs) — interactive Swagger UI for all 625 routes
2. Open the frontend login page in your browser:
   👉 **[http://localhost:3000/login](http://localhost:3000/login)**

---

## Step 7: Demo Login Accounts & Role Matrix

The login page includes **one-click demo buttons** for immediate credential autofill:

| Role | Email / Username | Password | Purpose & Access Boundary |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin@zeramai.com` | `ChangeMe123!` | Unrestricted access across all 21 modules, system audits, and integrations. |
| **HR Admin** | `hr@zeramai.com` | `ChangeMe123!` | Full HR suite: Core HR, Global Payroll, Statutory Compliance, Workforce Planning, LMS, Service Desk, Governance. |
| **Hiring Manager** | `manager@zeramai.com` | `ChangeMe123!` | Manager Self-Service (MSS): Team Engagement, Team Announcements, Candidates, Evaluations. Blocked from company salary configs and retention policies. |
| **Finance** | `finance@zeramai.com` | `ChangeMe123!` | Financial Ledgers, Cost Centers, Budgets, Payroll Journal Entries, Compensation Revisions. |
| **Employee Self-Service** | `employee@example.com` | `ChangeMe123!` | Employee Self-Service (ESS): Personal Profile, Payslips, Attendance punch, Leave requests, Assigned Courses, Helpdesk tickets. Strict IDOR protection. |

---

## Step 8: End-to-End Workflow Testing Guide (Modules 1–21)

Log in to [http://localhost:3000/login](http://localhost:3000/login) with the recommended role to exercise each major workflow:

### 1. Global Multi-Country Payroll & Compliance (Module 21 & 11)
- **Role:** `HR Admin` or `Super Admin`
- **Navigation:** Sidebar → **Global Payroll** (`/global-payroll` & `/admin/global-payroll`)
- **What to test:**
  - View supported Tier-1 countries (`USA`, `GBR`, `CAN`, `AUS`, `SGP`, `ARE`, `IND`).
  - Inspect foreign exchange (FX) rates across USD, GBP, CAD, AUD, SGD, AED, INR.
  - Review pay groups and multi-country pay period calendars.
  - Check India Statutory Compliance (`/statutory` and `/tax`) for EPF (12%), ESI (0.75%), Professional Tax slabs, and TDS calculations.

### 2. Workforce Planning & Scenario Modeling (Module 17)
- **Role:** `HR Admin`
- **Navigation:** Sidebar → **Workforce Planning** (`/workforce-planning`)
- **What to test:**
  - View organizational units and position hierarchies.
  - Review headcount demand vs. supply forecasts.
  - Test confidential restructuring scenario modeling.

### 3. Enterprise Learning & Competency Assessments (Module 18)
- **Role:** `HR Admin` or `Employee`
- **Navigation:** Sidebar → **Learning** (`/learning`)
- **What to test:**
  - Browse course catalog and learning paths.
  - Check competency assessment tracking and certificates.
  - Verify assessment answer keys remain protected and hidden from candidates.

### 4. Employee Engagement, Culture & Anonymity (Module 19)
- **Role:** `HR Admin` or `Hiring Manager`
- **Navigation:** Sidebar → **Engagement** (`/engagement`)
- **What to test:**
  - View survey campaigns, templates, and pulse sentiment tracking.
  - Explore peer recognition programs and cultural values.
  - Verify manager team dashboard enforces anonymity threshold ($n \ge 5$) before aggregating scores.

### 5. Enterprise Communications & Knowledge Base (Module 20)
- **Role:** `HR Admin` or `Employee`
- **Navigation:** Sidebar → **Communications** (`/communications`) & **Knowledge** (`/knowledge`)
- **What to test:**
  - Read enterprise announcements and critical bulletins.
  - Browse categorized knowledge base articles with full-text search.
  - Verify employees are blocked from publishing unapproved corporate announcements.

### 6. HR Service Desk & Incident Privacy (Module 16)
- **Role:** `Employee` then `HR Admin`
- **Navigation:** Sidebar → **HR Service Desk** (`/hr-service-desk` & `/hr-requests`)
- **What to test:**
  - As `Employee`: Submit a new HR service ticket.
  - As `HR Admin`: View ticket and add a confidential internal deliberation note (`is_internal: true`).
  - As `Employee`: Refresh ticket to confirm the internal note is strictly hidden.

### 7. Core Finance & General Ledger Mapping (Module 13)
- **Role:** `Finance`
- **Navigation:** Sidebar → **Finance** (`/finance`)
- **What to test:**
  - View cost center master lists and budget variance tracking.
  - Review automated double-entry payroll journal entries ($\sum \text{Debits} == \sum \text{Credits}$).

### 8. Enterprise Governance, Retention & Legal Holds (Module 15)
- **Role:** `HR Admin` or `Super Admin`
- **Navigation:** Sidebar → **Governance** (`/governance`)
- **What to test:**
  - View data classifications (Public, Internal, Confidential, Restricted).
  - Inspect automated retention schedules and legal hold overrides.
  - Review Data Subject Access Requests (DSAR).

### 9. Enterprise IAM, SSO & Webhooks (Module 14)
- **Role:** `Super Admin`
- **Navigation:** Sidebar → **Settings** → **Integrations** (`/settings/integrations`)
- **What to test:**
  - Inspect configured Identity Providers (Microsoft Entra ID, Google Workspace, Okta).
  - Review SCIM 2.0 user sync logs and outbound webhook subscriptions.
  - Verify sensitive secrets and API keys are masked.

### 10. Employee Self-Service (ESS) & Offboarding (Modules 6 & 10)
- **Role:** `Employee`
- **Navigation:** Sidebar → **My Profile** (`/me`), **Leave** (`/leave`), **Attendance** (`/attendance`)
- **What to test:**
  - Punch in/out attendance and view personal balance ledger.
  - Submit casual or earned leave requests.
  - Test resignation submission and exit clearance checklist progression (`/offboarding`).

---

## Step 9: Running Full Test & Quality Assurance Suites

### Run Backend Pytest Suite (288 Tests):
From the `backend` directory:
```bash
pytest -q
```
*Expected result:* **`288 passed in ~140-150s (0 failed, 0 errors)`**

### Run Frontend Production Build (69 Pages):
From the `frontend` directory:
```bash
npm run build
```
*Expected result:* **`Generating static pages (69/69) — Compiled successfully`**

---

## Step 10: Stopping the Application

To shut down the servers cleanly:
1. In the backend terminal window, press `Ctrl + C`.
2. In the frontend terminal window, press `Ctrl + C`.

*(Or in PowerShell to kill any remaining background listeners on ports 3000 & 8000)*:
```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3000, 8000 } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

---

## Troubleshooting & FAQ

### Q: Why do I see "Invalid email or password" after restarting backend?
**A:** In local SQLite mode, backend startup creates a fresh schema. Run:
```bash
python -m app.seed
python -m app.seed_rbac
```
Then refresh [http://localhost:3000/login](http://localhost:3000/login) and log in again.

### Q: Why does port 8000 or 3000 say "Address already in use"?
**A:** A previous server process is still running. Free the ports:
- **Windows:**
  ```powershell
  Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3000, 8000 } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
  ```
- **Linux/macOS:**
  ```bash
  kill -9 $(lsof -t -i:8000) $(lsof -t -i:3000)
  ```

### Q: Can I run this with Docker Compose?
**A:** Yes. From the root directory:
```bash
docker compose up -d
```
This boots PostgreSQL on 5432, backend on 8000, and frontend on 3000 with persistent volumes.
