# JARVIS CRM — Master Project Delivery & Error Resolution Checklist

This document is the definitive delivery and verification checklist for **JARVIS CRM**. Every task, architecture rule, feature implementation, and problem resolution is represented with checkboxes `[x]`, detailing the problem faced, root cause diagnosed, and engineering solution implemented.

---

## 1. Problem & Error Resolution Checklist (Problems Faced & Fixed)

The following checklist tracks every technical issue and runtime error encountered during development, along with its diagnosis and resolution:

- [x] **Problem 1: Windows Socket Access Forbidden (`[WinError 10013]`)**
  - **Symptom**: Starting Uvicorn failed with `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`.
  - **Root Cause**: An orphaned background Python process from a prior run was locked onto port 8000, causing Windows socket binding rejection.
  - **Resolution Applied**: Diagnosed using `Get-NetTCPConnection -LocalPort 8000`, terminated the orphaned process PID via PowerShell, and explicitly bound Uvicorn to `127.0.0.1:8000`.

- [x] **Problem 2: Login Failure with HTTP 422 Unprocessable Entity**
  - **Symptom**: Submitting login credentials returned `422 (Unprocessable Entity)` with `Field required: username`.
  - **Root Cause**: FastAPI's `OAuth2PasswordBearer` requires standard `application/x-www-form-urlencoded` format with `username` and `password`, but the React frontend was sending a raw JSON payload (`{ email, password }`).
  - **Resolution Applied**: Updated `login` in [api.ts](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/services/api.ts) to transmit `URLSearchParams` with `Content-Type: application/x-www-form-urlencoded`, mapping `email` to `username`.

- [x] **Problem 3: Super Admin Login & Multi-Tenant Context Failure**
  - **Symptom**: Super Admin could not access platform modules or global data; API requests returned HTTP 400 Bad Request.
  - **Root Cause**: The `get_tenant_id` FastAPI dependency strictly mandated the presence of an `X-Tenant-Id` header on all protected endpoints, failing platform-level Super Admins who have cross-tenant scope and no tenant header.
  - **Resolution Applied**: Implemented `get_optional_tenant_id` in [deps.py](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/backend/app/core/deps.py) to allow Super Admins platform-wide access while enforcing tenant isolation for Org Admins and Telecallers.

- [x] **Problem 4: Database Path Inconsistency / Empty DB on Startup**
  - **Symptom**: Logging in with seeded credentials occasionally reported user not found.
  - **Root Cause**: Relative SQLite connection path `sqlite:///./jarvis_crm.db` resolved differently depending on whether commands ran from workspace root or `backend/`, generating duplicate unseeded DB files.
  - **Resolution Applied**: Standardized [config.py](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/backend/app/core/config.py) to resolve the database path dynamically to the absolute file path of `backend/jarvis_crm.db`.

- [x] **Problem 5: Import Leads Blank Screen Runtime Crash**
  - **Symptom**: Selecting a CSV file in the Lead Ingestion wizard caused the entire screen to turn blank white.
  - **Root Cause**: `backend/app/schemas/import_job.py` stripped dictionary preview fields (`headers`, `preview_rows`) in `ImportPreviewResponse`. In [ImportModal.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/ImportModal.tsx), calling `previewData.headers.map(...)` caused an unhandled JavaScript `TypeError: Cannot read properties of undefined (reading 'map')`.
  - **Resolution Applied**:
    1. Updated `ImportPreviewResponse` and `ImportJobOut` schemas to include `headers`, `preview_rows`, `total_rows_estimate`, and `file_path`.
    2. Added defensive fallback chaining in [ImportModal.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/ImportModal.tsx) (`previewData.headers || previewData.detected_headers || []`).

- [x] **Problem 6: Dormant Telecaller Actions (Dummy Browser Alert Dialogs)**
  - **Symptom**: In the Telecaller Desk, clicking "Simulate Call" or "WhatsApp" produced a static browser `alert()` and did nothing else.
  - **Root Cause**: Buttons were bound to placeholder `alert("Simulated...")` callbacks without state machines or backend action proxies.
  - **Resolution Applied**: Built an interactive **Live VoIP Calling Cockpit** with a live ticking timer (`00:01`, `00:02`...), mute toggle, End Call button, automatic duration calculation, pre-filled call notes, and direct WhatsApp Web link generation.

- [x] **Problem 7: Super Admin Duplicate Modules ("Organizations" & "Platform Audit")**
  - **Symptom**: Clicking "Organizations" and "Platform Audit" in the Super Admin dashboard opened the identical page.
  - **Root Cause**: `SuperAdminView.tsx` was a monolithic single view without distinct routing branches for the two tabs.
  - **Resolution Applied**: Refactored [SuperAdminView.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/SuperAdminView.tsx) with a `viewMode?: "organizations" | "audit"` prop and decoupled the routing in [App.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/App.tsx) into two distinct screens.

- [x] **Problem 8: Super Admin Lacked Global Enterprise Ingestion**
  - **Symptom**: Super Admin had no way to bulk-import enterprise directories into the global database.
  - **Root Cause**: The ingestion service only supported tenant-scoped leads (`TENANT_LEADS`) requiring an `organization_id`.
  - **Resolution Applied**: Built the `GLOBAL_COMPANIES` ingestion mode in [import_service.py](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/backend/app/services/import_service.py), added an **"Import to Global Database"** button in [GlobalRegistryView.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/GlobalRegistryView.tsx), and implemented CIN/legal name deduplication with director mapping.

- [x] **Problem 9: Static Pipeline Kanban (No Drag & Drop)**
  - **Symptom**: Moving leads across stages in the pipeline required clicking sequential "Move" buttons without drag-and-drop capability.
  - **Root Cause**: Cards and column containers lacked HTML5 drag-and-drop event bindings and visual drop zones.
  - **Resolution Applied**: Rebuilt [KanbanBoard.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/KanbanBoard.tsx) with native HTML5 drag-and-drop, drag handles (`GripVertical`), column hover highlights, pulsing drop indicators, optimistic local state updates, and real-time search/priority filters.

- [x] **Problem 10: Missing Single Lead Manual Creation in ORG Admin**
  - **Symptom**: ORG Admins could only create leads via batch CSV imports; there was no button to quickly add a single lead.
  - **Root Cause**: `LeadsTable.tsx` and `Navbar.tsx` lacked trigger buttons connected to `NewLeadModal`.
  - **Resolution Applied**: Added primary **"+ Add Lead"** buttons in the table header and top navigation bar, wired them to `NewLeadModal.tsx`, replaced browser `alert()` with an in-modal dismissible error banner, and confirmed instant table re-fetching.

---

## 2. Core Architecture & Multi-Tenancy Checklist

- [x] **Modular Monolith Structure**: Clean domain isolation across `organizations`, `users`, `companies`, `contacts`, `leads`, `pipelines`, `activities`, `tasks`, `imports`, and `radar`.
- [x] **Server-Enforced Multi-Tenancy**: `organizations` table acts as the tenant boundary. Every tenant row carries `organization_id`. `tenant_id` is derived server-side from JWT tokens via `get_tenant_id` and never accepted from unauthenticated client payloads.
- [x] **Domain Entity Integrity**: Strict single source of truth without duplicate person registries (`crm_people`). Contacts belong to `contacts` (linking to `organization_id` and optional `company_id`). Leads represent sales opportunities linking to `contact_id`, `company_id`, and `pipeline_stage_id`.
- [x] **Pipeline Immutability During Batch Ingestion**: High-volume imports create lead rows referencing existing pipeline stages. Imports never mutate, duplicate, or delete pipeline or stage configurations.
- [x] **Immutable Lead Stage History**: Every stage movement writes an immutable audit row to `lead_stage_history` tracking `from_stage_id`, `to_stage_id`, `changed_by`, `reason`, and `duration_seconds`.
- [x] **Asynchronous Ingestion Engine**: Background file processing with progress tracking, row-level error isolation (`import_row_errors`), and deduplication.

---

## 3. Frontend UI & Structured Light Theme Checklist

- [x] **Design System Overhaul**: Complete transition to a structured, modern light theme using custom CSS tokens (`--bg-surface`, `--bg-canvas`, `--primary`, `--emerald`, `--amber`, `--rose`).
- [x] **High-Contrast Typography**: Implemented readable font hierarchy with dark slate text (`#0f172a`), subtle muted metadata (`#94a3b8`), and monospace values for scores and currency.
- [x] **Elevation & Depth**: Structured card containers with subtle borders (`--border-subtle`) and 5-level shadow tokens (`--shadow-xs` through `--shadow-xl`).
- [x] **Responsive Navigation Bar**: Top navigation featuring tenant context, active tab pill indicators, role badge, user profile meta, mobile hamburger menu, and quick logout.
- [x] **Interactive Micro-Animations**: Smooth card hover elevation (`translateY(-1px)`), pulsing calling dot, and animated drop zone targets.

---

## 4. Sales Pipeline Kanban Board Checklist

- [x] **Native HTML5 Drag and Drop**: Drag any card across stage columns with active drag grip handles (`GripVertical`).
- [x] **Column Drop Zones**: Hovering over target columns highlights the column border and activates a pulsing drop target indicator (`kanban-drop-indicator`).
- [x] **Optimistic UI Updates**: Cards snap to destination columns immediately upon drop, recalculating stage counters and total deal revenue instantly.
- [x] **Safe Click Debounce**: Prevents accidental opening of the 360° Lead Detail Drawer when releasing a drag.
- [x] **Real-Time Search & Priority Filter Bar**: Added search input (filtering by title, company, or contact) and priority chips (`All`, `Hot / Urgent`, `Medium`, `Low`).
- [x] **All Existing UI Options Preserved**:
  - [x] Stage color dot (`stage.color || "var(--primary)"`).
  - [x] Uppercase stage name and lead count pill.
  - [x] Stage total revenue calculation in Indian denominations (`₹...k`, `₹...L`, `₹...Cr`).
  - [x] Priority badges (`badge-hot`, `badge-medium`).
  - [x] Radar flame score (`Flame` icon + score).
  - [x] Anti-theft phone masking indicator.
  - [x] Direct Gmail compose launcher.
  - [x] Quick stage advance button (`Move to [Next Stage] &rarr;`).
  - [x] "+ Create New Lead" button opening lead creation modal.

---

## 5. Leads Directory & 360° Lead Drawer Checklist

- [x] **Manual Single Lead Creation**: Primary **"+ Add Lead"** button in [LeadsTable.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/LeadsTable.tsx) header and [Navbar.tsx](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/components/Navbar.tsx).
- [x] **In-Modal Validation**: In-dialog dismissible error alert banner replacing native browser `alert()` popups.
- [x] **Structured Leads Table**: Sortable, filterable directory with contact chips, stage pills, priority badges, and quick actions.
- [x] **360° Lead Detail Slide-Over Drawer**:
  - [x] Deal Overview: Stage selector, deal value, currency, and win probability.
  - [x] Contact Profile: Primary phone, email, company association, and job title.
  - [x] Activity Timeline: Chronological audit of calls, emails, notes, and system updates.
  - [x] Stage History Log: Immutable table of previous stages and elapsed durations.
  - [x] Task Scheduler: Pending and completed follow-up action items.

---

## 6. Super Admin Console & Module Separation Checklist

- [x] **Organizations Module (`viewMode="organizations"`)**:
  - [x] Dedicated tenant management dashboard.
  - [x] 4 Key Performance Indicator (KPI) cards: Total Tenants, Active Workspaces, Ingested Companies, Global Directors.
  - [x] Search bar and status filter dropdown (`ALL`, `ACTIVE`, `SUSPENDED`).
  - [x] Full Tenants Table displaying organization name, slug, subscription tier, and creation date.
  - [x] "+ Provision New Tenant" modal with validation.
- [x] **Platform Security Audit Module (`viewMode="audit"`)**:
  - [x] Dedicated security audit trail dashboard.
  - [x] 4 Audit KPI cards: Total Logged Events, Outbound Calls, Direct Emails, Stage Transitions.
  - [x] Action Type dropdown filter (`ALL`, `CALL_TRIGGERED`, `EMAIL_TRIGGERED`, `WHATSAPP_TRIGGERED`, `CONTACT_VIEW`, `STAGE_CHANGED`, `LOGIN_SUCCESS`, `ORGANIZATION_CREATED`).
  - [x] Tenant filter dropdown to inspect individual organization activities.
  - [x] Real-time search filter across event metadata and user IPs.
  - [x] Chronological security event table with timestamp, actor, organization, action badge, and payload context.
- [x] **Global Database Registry & Bulk Ingestion**:
  - [x] Browse 70,000+ master company records and verified directors.
  - [x] **"Import to Global Database"** button in header.
  - [x] Re-uses the smart auto-detection column mapping wizard for global company CSV files.
  - [x] Deduplicates against existing companies by CIN or legal name.
  - [x] Automatically associates contacts/directors in `GlobalCompanyContactMap`.

---

## 7. Anti-Theft Data Masking & Communication Cockpit Checklist

- [x] **Server-Enforced Data Masking**:
  - [x] Phone masking for `TELECALLER` role: `+91 98**** 1234`.
  - [x] Email masking for `TELECALLER` role: `ex****@domain.com`.
  - [x] Raw database exports blocked for telecallers.
- [x] **Live VoIP Outbound Calling Cockpit**:
  - [x] Active call status bar with pulsing indicator dot.
  - [x] Real-time ticking call timer (`00:01`, `00:02`, `00:03`...).
  - [x] Audio channel status and microphone Mute/Unmute toggle.
  - [x] **End Call** button with automatic elapsed duration calculation.
  - [x] Pre-fills discussion outcome: `Connected outbound call (22s). Notes: `.
- [x] **Proxied WhatsApp Action**:
  - [x] Backend endpoint `POST /leads/{id}/action/whatsapp` records audit event in `radar_events`.
  - [x] Generates WhatsApp Web URL with pre-populated contextual prospect greeting.
- [x] **Universal Gmail Composer Integration**:
  - [x] Shared utility [mailHelper.ts](file:///c:/Users/Lokesh/Downloads/Jarvis_CRM_New/frontend/src/utils/mailHelper.ts) generating pre-filled Gmail compose URLs.
  - [x] Added clickable Gmail compose button to **Telecaller Desk**.
  - [x] Added clickable Gmail compose button to **Pipeline Kanban** cards.
  - [x] Added clickable Gmail chip to **Leads Table** contact rows.
  - [x] Added clickable Gmail buttons to **360° Lead Detail Drawer** (Quick Action Bar + Contact Profile).

---

## 8. Verification & Quality Assurance Checklist

- [x] **Frontend TypeScript & Bundle Build**:
  - Command: `cmd /c npm run build` (`tsc -b && vite build`)
  - Result: **Passed with 0 errors** (1,861 modules transformed, built in 401ms).
- [x] **Backend API & Route Registration**:
  - Command: `python -c "import app.main; print('API OK')"`
  - Result: **Passed** (FastAPI app, dependencies, routes, and DB models loaded cleanly).
- [x] **Database Engine & Persistence**:
  - SQLite foreign key constraints, organization partitioning, and stage history immutability verified.
- [x] **Role-Based Permissions (RBAC)**:
  - Verified `SUPERADMIN` (`superadmin@jarvis.local`), `ADMIN` (`admin@apex.com`), and `TELECALLER` (`telecaller@apex.com`).
- [x] **Live Browser Subagent Verification**:
  - Automated Playwright browser recordings captured for Kanban drag-and-drop, module switching, lead creation, and VoIP calling.
