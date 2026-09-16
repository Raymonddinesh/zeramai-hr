# Zeramai HRMS — Master System Architecture Document (v3.0 Baseline)

**Document Version:** 3.0.0  
**Target Platform:** Zeramai HRMS Enterprise Multi-Tenant Platform  
**Authors:** Enterprise Software Architecture Team  
**Status:** Baseline Production Architecture Specification  

---

## 1. High-Level System Architecture & Topology

Zeramai HRMS is architected as an **international-standard, multi-tenant SaaS platform**. It utilizes a decoupled presentation and business API model with enterprise-grade isolation, automated workflow orchestration, and governed AI intelligence.

```mermaid
graph TD
    Client[Next.js 14 App Router\nTypeScript + Tailwind CSS\nhttp://localhost:3000] -->|HTTPS / WSS / REST API| Ingress[Ingress Gateway / NGINX / Cloudflare]
    Ingress -->|Session / Cookie Proxy| API[FastAPI Application Services\nPython 3.11+ / Async Lifespan\nhttp://localhost:8000]
    
    API -->|Tenant-Keyed Queries| DB[(PostgreSQL Primary DB\nRelational & Tenant Data)]
    API -->|Distributed Cache / Session| Cache[(Redis Cluster\nRate Limiting & Token Cache)]
    API -->|Event Bus / Async Tasks| Queue[(RabbitMQ / Service Bus\nAsync Workflows & Emails)]
    API -->|Private Blob Storage| ObjectStore[(Azure Blob / AWS S3\nEncrypted Document Vault)]
    API -->|Search & Analytics Index| Search[(OpenSearch / Elasticsearch\nPeople Analytics Index)]

    AuditEngine[Append-Only Audit Engine] -->|SIEM Stream| SIEM[Datadog / Splunk SIEM]
    API --> AuditEngine
```

---

## 2. 5-Layer Security & Authorization Architecture

Security is enforced at platform boundaries before any business logic executes. Every request passes through 5 distinct evaluation checkpoints:

```mermaid
flowchart LR
    Req[Incoming HTTP Request] --> Layer1[1. Authentication\nJWT Cookie / OAuth2 / SAML]
    Layer1 --> Layer2[2. Tenant Isolation Context\nServer-Derived tenant_id]
    Layer2 --> Layer3[3. Role-Based Access Control\nRBAC Permissions]
    Layer3 --> Layer4[4. Attribute-Based Access Control\nABAC Context Rules]
    Layer4 --> Layer5[5. Object Ownership Check\nPerson / Resource Owner ID]
    Layer5 --> Audit[6. Immutable Audit Log\nAuditResult.SUCCESS / DENIED]
```

### Security Layer Definitions

1. **Layer 1 — Authentication**: Decodes JWT `access_token` from HTTP-only, `SameSite=Lax` cookie. Supports SAML 2.0 / Okta / Entra ID SSO.
2. **Layer 2 — Tenant Isolation Context**: Resolves tenant identity from authenticated session (`current_user.tenant_id`). Client-supplied `tenant_id` query parameters are strictly forbidden from overriding server context.
3. **Layer 3 — Role-Based Access Control (RBAC)**: Checks assigned permission codes (`has_permission(user, code, db)`) via `Role` → `RolePermission` → `Permission` join.
4. **Layer 4 — Attribute-Based Access Control (ABAC)**: Evaluates dynamic environmental attributes (e.g., location, IP range, business unit).
5. **Layer 5 — Object-Level Ownership**: Enforces `person_id == current_user.person_id` for self-service operations to prevent Insecure Direct Object Reference (IDOR) vulnerabilities.
6. **Layer 6 — Append-Only Audit Logging**: Automatically logs all success and denial events to an immutable `audit_logs` ledger.

---

## 3. Data Architecture & Tenant Isolation Strategy

### 3.1 Multi-Tenant Data Schema Design
The application uses a **Shared Database, Tenant-Keyed Schema** model. Every tenant-owned table contains an indexed `tenant_id` column linked to `tenants.id`.

```mermaid
erDiagram
    TENANTS ||--o{ LEGAL_ENTITIES : owns
    TENANTS ||--o{ USERS : contains
    LEGAL_ENTITIES ||--o{ LOCATIONS : operates
    LEGAL_ENTITIES ||--o{ DEPARTMENTS : structures
    DEPARTMENTS ||--o{ EMPLOYMENT_HISTORY : tracks
    PERSONS ||--o{ EMPLOYMENT_HISTORY : maintains
    PERSONS ||--o{ DOCUMENTS : stores
    PERSONS ||--o{ ATTENDANCE : records
    PERSONS ||--o{ LEAVE_REQUESTS : applies
    PERSONS ||--o{ STIPENDS : receives
```

### 3.2 Effective-Dated HR Master Data
To preserve historical accuracy across promotions, transfers, compensation revisions, and manager reassignments, the core HR module enforces **Effective-Dated Records**:

```
EmploymentHistory
├── tenant_id (FK)
├── person_id (FK)
├── effective_date (DATE)
├── change_type (JOINING | PROMOTION | TRANSFER | COMPENSATION_REVISION)
├── designation (VARCHAR)
├── department_id (FK)
├── manager_id (FK)
└── salary_amount (NUMERIC)
```

---

## 4. Modular Global Payroll Adapter Architecture

To support multi-country payroll compliance without rewriting core business domain logic, payroll is structured into a **Global Core + Country Rule Adapters**:

```mermaid
graph TD
    Core[Global Payroll Core Engine\nPeriods, Runs, Base Compensation] --> AdapterPattern{Country Rule Adapter Interface}
    AdapterPattern --> India[India Country Adapter\nPF, ESI, PT, Form 16, TDS]
    AdapterPattern --> UAE[UAE Country Adapter\nWPS, Gratuity, No Income Tax]
    AdapterPattern --> USA[USA Country Adapter\n401k, W-2, Federal/State Tax]
    AdapterPattern --> UK[UK Country Adapter\nPAYE, National Insurance, P60]
    AdapterPattern --> SG[Singapore Country Adapter\nCPF, FWL, IR8A]
```

---

## 5. Governed AI HR Intelligence Architecture

Artificial Intelligence capabilities in Zeramai HRMS operate under a **Human-in-the-Loop Governance Framework**:

```mermaid
flowchart TD
    Data[Candidate Resume / Employee Profile] --> Parser[OCR & Text Parser]
    Parser --> LLM[AI Match & Summarization Engine]
    LLM --> Score[Deterministic Match Score & Evidence Breakdown]
    Score --> Review{Human HR Reviewer}
    Review -->|Approve| Action[Proceed to Interview / Offer]
    Review -->|Override| Manual[Manual Score Adjustment]
    Score --> Audit[Audit Trail: Model Version & Prompt Logged]
```

- **No Autonomous Employment Decisions**: AI generates match scores, skill extractions, and policy summaries with clear evidence rationale.
- **Traceability**: All prompt inputs, model versions, and outputs are audit-logged for bias monitoring.

---

## 6. DevOps, Infrastructure & Kubernetes Deployment Strategy

zeramai HRMS scales horizontally from single-node Docker containers to multi-region Kubernetes clusters.

```mermaid
graph TD
    K8s[Kubernetes Cluster / AKS / EKS]
    K8s --> IngressController[Ingress NGINX Controller]
    IngressController --> FE_Pods[Next.js Frontend Pods\nAutoscaled HPA]
    IngressController --> BE_Pods[FastAPI Backend Pods\nAutoscaled HPA]
    BE_Pods --> Worker_Pods[RabbitMQ Celery/Task Workers]
    
    BE_Pods --> PG_HA[(PostgreSQL High-Availability Cluster\nPrimary + Read Replicas)]
    BE_Pods --> Redis_HA[(Redis Sentinel / Cluster)]
    BE_Pods --> AzureBlob[(Azure Blob Storage / S3)]
```

---

## 7. API Versioning & Integration Standards

- **RESTful Endpoints**: Versioned path structure `/api/v3/...`
- **Identity Provisioning**: SCIM 2.0 RFC 7644 endpoints (`/api/scim/v2/Users`)
- **Documentation**: Automatic OpenAPI 3.0 Swagger UI (`/docs`) & JSON schema (`/openapi.json`)
- **Webhooks**: Signed HMAC-SHA256 event notifications for downstream enterprise integrations.
