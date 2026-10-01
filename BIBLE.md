# [OBSOLETE] - THIS DOCUMENT IS NO LONGER ACCURATE

**Please refer to docs/SOURCE_OF_TRUTH.md and ARCHITECTURE.md for current accurate information.**

# JARVIS CRM — The Bible (Source of Truth)

This document is the master blueprint of the JARVIS CRM platform. It contains the complete system architecture, data models, business rules, and feature summaries built up through Phase 4. A new developer should be able to rebuild the entire application from scratch using only this document.

---

## 1. System Architecture & Tech Stack

JARVIS CRM is a **Modular Monolith** designed for multi-tenancy at scale, featuring background processing, tenant data isolation, and robust security.

### Core Technologies
- **Backend Framework**: FastAPI (Python 3.10+)
- **Database ORM**: SQLAlchemy 2.0 (Declarative Models, async-ready constructs)
- **Database Engine**: PostgreSQL 15 (Single database, tenant isolation via `organization_id` & app-level Row Level Security)
- **Background Jobs**: Celery with Redis broker (for imports, data quality scans, telemetry)
- **Frontend Framework**: React 18 with TypeScript (Vite bundler)
- **Frontend Routing & State**: `react-router-dom`, React Context/Hooks
- **UI & Styling**: Vanilla CSS with a glassmorphic, modern design system (`index.css`), Lucide React for iconography.
- **Containerization**: Docker Compose (`backend`, `frontend`, `postgres`, `redis`, `worker`, `beat`)

### Directory Structure
```
jarvis/
├── backend/
│   ├── app/
│   │   ├── core/         # DB config, Security, JWT Auth, FastAPI Dependencies
│   │   ├── models/       # SQLAlchemy tables
│   │   ├── schemas/      # Pydantic v2 validation DTOs (Request/Response)
│   │   ├── services/     # Pure Business Logic (No HTTP/Request objects here)
│   │   ├── api/v1/       # REST API Routers
│   │   ├── tasks/        # Celery Background Tasks
│   │   └── main.py       # FastAPI Entrypoint
│   ├── tests/            # Pytest test suite
│   ├── alembic/          # Migrations
│   └── schema.sql        # Master DDL
├── frontend/
│   ├── src/
│   │   ├── components/   # React Components (Kanban, Telecaller Desk, SuperAdmin)
│   │   ├── services/     # Axios API Client
│   │   ├── utils/        # Formatters, helpers
│   │   ├── index.css     # Global Glassmorphic Styles
│   │   └── App.tsx       # Root App & Routing logic
├── docker-compose.yml    # Infra definitions
└── BIBLE.md              # THIS FILE
```

---

## 2. Core Architectural Principles

1. **Service-Layer Dominance**: Business logic resides *exclusively* in `backend/app/services/`. API endpoints in `backend/app/api/` handle only HTTP serialization and calling the correct service.
2. **Multi-Tenancy & Isolation**: 
   - Every tenant-owned row MUST carry an `organization_id`.
   - `tenant_id` is always derived server-side from the JWT token via a FastAPI dependency. It is **never** trusted from a client payload payload.
3. **Domain Entity Integrity**:
   - `contacts` belong to `organizations` and optionally `companies`.
   - `leads` represent sales opportunities linked to a `contact_id`, a `company_id`, and a `pipeline_stage_id`.
   - There are no generic `crm_people` tables.
4. **Data Masking & Anti-Theft**:
   - The API automatically masks PII (e.g., `+91 98**** 1234`) for specific roles (like `TELECALLER`) before sending it to the client.
   - Raw data never reaches the browser unless the user has permission.
5. **Asynchronous Processing**:
   - Heavy operations (importing 10k rows, checking for duplicates, calculating metrics) run on Celery. The API returns a `job_id` or an "accepted" status immediately.
6. **Immutable Pipelines**:
   - Moving a lead generates an immutable row in `lead_stage_history`.
   - Imports map to existing pipelines; they never mutate pipeline configurations.

---

## 3. Database Schema Overview (Key Entities)

### Tenant & Access Control
- `organizations`: Tenant boundary.
- `users`: Includes `platform_role` (e.g. SUPER_ADMIN, DATA_ENTRY) and `tenant_role` (ORG_ADMIN, TELECALLER, SALES).
- `plans` & `subscriptions`: Controls billing limits and feature flags.

### Core CRM Domain
- `pipelines` & `pipeline_stages`: The sales flow.
- `companies`: Tenant-specific company records.
- `contacts`: Tenant-specific contact records.
- `leads`: Opportunities representing the combination of a contact, company, and product intent at a specific pipeline stage.
- `activities`: Interactions (calls, emails, meetings) logged against leads/contacts.
- `tasks`: Action items assigned to users with deadlines.
- `lead_assignments`: Tracks who owns which lead.
- `lead_stage_history`: Audit trail of a lead moving through the pipeline.

### Global Data Engine
- `global_companies` & `global_contacts`: A master registry of data accessible (read-only) by all tenants.
- `global_company_contact_map`: M2M relationship for the global intelligence graph.
- `global_data_pull_logs`: Tracks when a tenant "pulls" global data into their own `companies`/`contacts` tables (lineage). Tenant tables use `source_global_company_id` to trace back to the master.

### Operations & Observability
- `audit_logs`: Tracks every consequential mutation (who, what, when, old values, new values).
- `radar_events`: High-velocity telemetry (e.g., a telecaller logging 50 calls an hour).
- `import_jobs` & `import_row_errors`: Asynchronous data ingestion state and row-level error tracking.
- `dedupe_candidates`: Detected duplicate pairs awaiting manual or automated merging.

---

## 4. Phase Summaries

### Phase 1: Security & Tenant Foundation
- **What was built**: The absolute bedrock. Organization models, User RBAC (Platform vs Tenant roles), JWT Authentication, Row-Level isolation enforcement in API dependencies, initial Audit logging.
- **Key Files**: `backend/app/models/rbac.py`, `backend/app/core/security.py`, `backend/app/api/v1/auth.py`.

### Phase 2: Organization Control
- **What was built**: Super Admin dashboards, Tenant Management, Radar (telemetry visualization), and health monitoring.
- **Key Files**: `frontend/src/components/SuperAdminView.tsx`, `backend/app/api/v1/admin.py`, `backend/app/services/radar_service.py`.

### Phase 3: Billing & Global Intelligence
- **What was built**: Subscriptions, plans, limits. The "Global Data" registry (Companies and People) allowing tenants to enrich their CRM without polluting a shared space. Implementation of `GlobalDataPullLog` to ensure lineage. 
- **Key Files**: `backend/app/services/billing_service.py`, `backend/app/services/global_registry_service.py`, `frontend/src/components/GlobalIntelligenceView.tsx`.

### Phase 4: Data Governance (Current)
- **What is being built**: 
  - **Celery Infrastructure**: Redis broker and worker setup via Docker Compose.
  - **Scalable Imports**: Chunked processing of CSVs using SQLAlchemy `bulk_insert`. Validation pipelines (Schema -> Normalization -> Business Logic -> Deduplication).
  - **Duplicate Engine**: Celery Beat scheduled tasks that scan `leads`, `contacts`, and `companies` for matches (GSTIN, Domain, Phone) and populate `dedupe_candidates`. Endpoints to resolve these duplicates.
  - **Data Quality Engine**: Background tasks scanning for anomalies (missing emails, malformed phones) to create `DataQualityIssue` records.
  - **Change Requests**: Controlled `GlobalDataChangeRequest` mechanism so users can't arbitrarily overwrite master data.

---

## 5. UI/UX Paradigm

The frontend is a single-page React app styled with a **glassmorphic** design system (`index.css`):
- Vibrant gradients, semi-transparent panels, and subtle blurs (`backdrop-filter: blur()`).
- **Role-based Rendering**: The UI heavily adapts to the user's role. A `TELECALLER` sees a focused dialer desk; a `SUPER_ADMIN` sees a global control plane; a `DATA_ENTRY` agent sees the global registry.
- **Major Components**:
  - `KanbanBoard`: Drag-and-drop pipeline visualization.
  - `TelecallerDesk`: High-speed calling interface for agents.
  - `GlobalIntelligenceView`: Network graph and registry explorer for pulling data.
  - `SuperAdminView`: Tabbed layout for managing tenants, billing, and platform audit logs.

