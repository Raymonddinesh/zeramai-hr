# Zeramai Enterprise HRMS — Release v2.1.0

## Full Enterprise Multi-Country Platform (Modules 11–21 Integration)

**Release Version:** `v2.1.0` (Git Tag: `v2.1.0` / Branch: `main`)  
**Architecture Baseline:** Master Production Specification (Modules 1–21)  
**Target Market:** Global Enterprise Multi-Tenant Workforce & International Payroll  
**Release Date:** September 2026  
**Alembic Head:** `a31824c94d6e` (242 relational tables)  
**Full Test Suite:** 288 Passed, 0 Failed, 0 Errors (100% Pass Rate)  
**Frontend Surface:** 69/69 Pages Compiled Successfully  

---

### Key Capabilities Introduced in v2.1.0

#### 1. Module 11: India Statutory Compliance Engine (`/statutory`, `/tax`)
- **Employee Provident Fund (EPF)**: 12% employee contribution with 8.33% EPS / 3.67% EPF employer split subject to ₹15,000 statutory limit.
- **Employee State Insurance (ESI)**: 0.75% employee and 3.25% employer contribution subject to ₹21,000 wage ceiling.
- **Professional Tax (PT)**: State-by-state monthly/semi-annual slab computations.
- **TDS / Income Tax**: Old vs. New tax regime calculation, Chapter VI-A deductions, and quarterly Form 24Q preparation.

#### 2. Module 12: Advanced Workforce Analytics & Insights (`/analytics/*`)
- Attendance, compensation, compliance, performance, recruitment, and workforce cost analytics.
- Snapshot history generation and predictive headcount metrics.

#### 3. Module 13: Core Financial Ledgers, Cost Centers & Payroll Journals (`/finance`)
- Cost center structure, department budget variance analysis, and vendor invoice tracking.
- Automated double-entry payroll general ledger journal entries ($\sum \text{Debits} == \sum \text{Credits}$).

#### 4. Module 14: Enterprise IAM, SSO & SCIM Directory Provisioning (`/settings/integrations`)
- Identity federation via SAML 2.0 / OIDC (Microsoft Entra ID, Google Workspace, Okta).
- RFC 7644 SCIM 2.0 user and group provisioning endpoints.
- Outbound HMAC-SHA256 event webhooks and irreversible credential masking.

#### 5. Module 15: Enterprise Data Governance, Retention & Legal Holds (`/governance`)
- Data classifications (Public, Internal, Confidential, Restricted).
- Automated retention policy enforcement and litigation legal hold overrides.
- Data Subject Access Requests (DSAR) fulfillment workflows.

#### 6. Module 16: HR Service Desk & Employee Relations (`/hr-service-desk`, `/employee-relations`)
- Helpdesk incident ticketing with priority SLA queues and category routing.
- Confidential HR internal notes strictly hidden from employee view.
- Formal grievance panels, investigation records, and whistleblower resolutions.

#### 7. Module 17: Workforce Planning & Organizational Design (`/workforce-planning`)
- Org unit structuring and position management.
- Headcount demand vs. supply forecasting.
- Confidential restructuring scenario modeling with financial impact projections.

#### 8. Module 18: Enterprise Learning & Competency Assessments (`/learning`)
- Modular training catalog, learning paths, and learner progress tracking.
- Competency assessments, certifications, and protected grading keys.

#### 9. Module 19: Employee Engagement, Culture & Anonymized Surveys (`/engagement`)
- Survey campaign scheduler, question banks, and pulse sentiment tracking.
- Peer recognition programs and company cultural values.
- Strict anonymity threshold enforcement ($n \ge 5$ respondents) preventing individual de-anonymization.

#### 10. Module 20: Enterprise Internal Communications & Knowledge Base (`/communications`, `/knowledge`)
- Targeted enterprise announcements with critical alert bulletins.
- Categorized knowledge base articles with full-text search and draft-approval lifecycle.

#### 11. Module 21: Global Multi-Country Payroll & FX Currency Engine (`/global-payroll`)
- Native Gross-to-Net payroll engines across 7 Tier-1 countries:
  - **USA**: Federal FIT, FICA (Social Security & Medicare), 401(k).
  - **GBR (UK)**: PAYE bands, National Insurance Class 1, Auto-Enrolment Pensions.
  - **CAN (Canada)**: Federal/Provincial tax, CPP, Employment Insurance.
  - **AUS (Australia)**: ATO Resident Scales, Superannuation Guarantee (11.5%), Medicare.
  - **SGP (Singapore)**: CPF age-tiered contribution scales, Skills Development Levy (SDL).
  - **ARE (UAE)**: WPS SIF file generation, GPSSA citizen pensions, End of Service Gratuity.
  - **IND (India)**: Full statutory integration with EPF, ESI, PT, and Section 192 TDS.
- Multi-currency Foreign Exchange (FX) service across 5 major currency pairs.
- Multi-country pay groups, pay period calendars, and encrypted employee payslips.

---

### Quality Assurance & Verification Highlights
- **Backend Tests:** 288 passed, 0 failed, 0 errors.
- **Frontend Pages:** 69/69 pages statically prerendered with Next.js 14.
- **OpenAPI Schema:** 625 registered routes.
- **Security Audit:** Zero cross-tenant leakage, 100% IDOR defense pass rate.
