# Zeramai HRMS — Release v2.0.0

## Master Product Requirements Document Implementation

**Release Version:** `v2.0.0` (Git Tag: `v2.0.0` / Branch: `v2`)  
**Architecture Baseline:** Master PRD v3.0  
**Target Market:** International SMB, Mid-Market & Enterprise Workforce Management  
**Release Date:** September 2026  

---

### Key Capabilities Included in v2.0.0

#### 1. Core Platform & Multi-Tenant Organization (`/organization`)
- Multi-Tenant SaaS isolation architecture with row-level and object-level security.
- Comprehensive Organization Tree hierarchy: Tenants → Legal Entities → Locations → Departments → Cost Centers.
- Interactive Org-Chart visualization and department management.

#### 2. Preboarding & Onboarding Checklist Engine (`/onboarding`)
- Dynamic Onboarding Checklist templates with automated task spawning across IT, HR, and Compliance.
- Real-time task progress recalculation and milestone completion tracking.

#### 3. Global ATS & Talent Acquisition (`/jobs`)
- Full requisition lifecycle: Draft → Open → On Hold → Closed.
- AI Resume Match Scoring engine with skill parsing and match rationale extraction.
- Structured interview scheduling, scoring matrix, and offer letter management.

#### 4. Attendance & Shift Rostering Engine (`/shifts`)
- Flexible Shift Templates (Day, Morning, Afternoon, Night, Rotational).
- Conflict-detected scheduling (prevents overlapping worker allocations).
- Peer-to-peer shift swap requests with supervisor approval workflow.

#### 5. Global Leave Policy Engine (`/leave`)
- Configurable leave policies with customizable annual quotas and accrual cadences.
- Real-time leave balance tracking with carry-forward rules.
- Compensatory off (Comp-Off) lifecycle for weekend/holiday overtime.

#### 6. Global Payroll & Compensation Core (`/payroll`)
- Earning and statutory deduction components (PF, ESI, Tax).
- Employee CTC salary structure mappings.
- Automated batch payroll compute with Loss-of-Pay (LOP) calculations and detailed payslips.

#### 7. Performance Management & OKRs (`/performance`)
- Review cycles (Quarterly, Half-yearly, Annual).
- Cascading company, department, and team OKR objectives.
- Key results with automated progress recalculation upon value updates.

#### 8. Learning Management System & Skills (`/learning`)
- Modular training course catalog with capacity enforcement.
- Learner enrollment progress tracking.
- Automated certificate generation with unique verification identifiers upon completion.

#### 9. People Analytics & Reporting (`/analytics`)
- Live executive workforce KPIs.
- Headcount breakdown by legal entity and department.
- Pre-computed analytics snapshots for longitudinal headcount trend analysis.

#### 10. Compliance, Policy Center & Whistleblower Desk (`/compliance`)
- Company compliance policy center with mandatory e-acknowledgments and IP stamping.
- Confidential and anonymous whistleblower grievance submission and resolution tracking.

#### 11. Multi-Country Localization & Currencies (`/settings`)
- Country-specific holiday calendars (Public and Regional holidays).
- FX exchange rate management with live multi-currency conversion.

#### 12. Enterprise IAM, Security & Governed AI Suite (`/settings`)
- Configurable password complexity, lockout thresholds, and session timeouts.
- Active session registry with instant remote kill-switch revocation.
- Governed AI Attrition Risk Predictor evaluating absence and tenure indicators.
- AI HR Helpdesk knowledge search for instant policy answers.

---

### Verification
- **Unit Tests**: 18/18 passing (`pytest`)
- **API Integration Tests**: 138/138 passing across all operational endpoints
- **Frontend Build**: Next.js production build compiled with 0 errors
- **Routes**: All 17 frontend routes verified responding HTTP 200
