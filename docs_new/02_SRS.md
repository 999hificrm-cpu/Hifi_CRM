# Jarvis CRM — Software Requirements Specification (SRS)

**Version:** 1.0 · **Format:** IEEE-830 style, adapted for AI-assisted ("vibe coding") build
**Companion docs:** `01_PRD.md`, `03_DATABASE_SCHEMA.md`, `04_ARCHITECTURE_AND_DEVOPS.md`, `05_DEVELOPMENT_BIBLE.md`

---

## 1. Introduction

### 1.1 Purpose
Defines functional and non-functional requirements for Jarvis CRM so that an AI coding
agent or a human developer can implement modules independently against a single
unambiguous contract. Every functional requirement has a stable ID (`FR-xxx`) referenced
in code comments, PR descriptions, and test names.

### 1.2 Scope
Covers: Global Data Layer (super admin), Tenant CRM Layer, Data Masking & Radar,
Activities/Communication, File Storage, Dashboards, and platform Auth/RBAC/Billing.

### 1.3 Definitions
- **Tenant**: one paying customer organization.
- **Global Record**: a Company or Person row owned by the platform (super admin).
- **Pull**: the act of a tenant importing/licensing a Global Record into their own Lead
  data.
- **Lead**: a tenant-owned Company-shaped record in their CRM (may reference a Global
  Record, or be fully tenant-authored).
- **Masked Field**: a field whose raw value is withheld from the UI/API response for a
  given role; only a proxied action (masked call/WhatsApp/email) is available.
- **Radar Event**: a logged data-access or communication action, scored by the anomaly
  engine.

---

## 2. Overall Description

### 2.1 System Context
Two logical tenants of the same codebase:
- `platform` schema/scope — super admin + global data.
- `tenant:{id}` scope — one row per organization, isolated via `tenant_id` on every
  table plus row-level authorization checks (see `03_DATABASE_SCHEMA.md §5`).

### 2.2 User Classes
`SUPER_ADMIN`, `DATA_OPS` (platform sub-role), `TENANT_ADMIN`, `TENANT_MANAGER`
(optional mid-tier, can see unmasked data, cannot manage billing), `TENANT_AGENT`
(telecaller — masked by default).

### 2.3 Operating Environment
- Server: Dockerized Node.js services on a single Hostinger VPS (MVP), Ubuntu LTS,
  behind Nginx + Let's Encrypt TLS.
- Client: modern evergreen browsers, installable PWA, mobile-first responsive layout.
- Data: PostgreSQL 15+, Redis 7+, S3-compatible object storage (self-hosted MinIO on VPS
  for MVP, swappable).

---

## 3. Functional Requirements

### 3.1 Authentication & RBAC
- **FR-001** System shall support email+password login with JWT access token (short
  TTL) + refresh token (httpOnly cookie) per user.
- **FR-002** System shall support role assignment at two levels: platform role
  (`SUPER_ADMIN`/`DATA_OPS`) and tenant role (`TENANT_ADMIN`/`TENANT_MANAGER`/
  `TENANT_AGENT`), stored per user with an optional per-user permission override set
  (JSON) for granular exceptions.
- **FR-003** System shall enforce field-level and action-level permission checks
  server-side (never trust client) via a central policy module (see `05_DEVELOPMENT_BIBLE.md`).
- **FR-004** System shall support inviting sub-users by email with a role pre-assigned;
  invite expires in 72h.

### 3.2 Global Data Layer (Super Admin)
- **FR-010** Super Admin shall upload an Excel/CSV of Companies; system parses,
  validates required columns (CIN, company_name at minimum), and upserts by CIN.
- **FR-011** Super Admin shall upload an Excel/CSV of People (Directors); system
  validates required columns (name + at least one of DIN/email/mobile) and upserts by
  DIN when present, else by (name + mobile) fuzzy match flagged for manual review.
- **FR-012** Super Admin shall upload/maintain a Company↔Person mapping (designation,
  appointment date, status) either embedded in the People sheet (a `CIN` column) or as
  a separate mapping sheet.
- **FR-013** Every upload shall create an immutable `data_upload_batches` record
  (uploader, filename, counts, timestamp) and per-row error entries for failed rows,
  downloadable as an error report.
- **FR-014** Every Company/Person record shall track `first_seen_at`, `last_updated_at`,
  and `last_updated_by_batch_id`.
- **FR-015** Super Admin shall be able to soft-delete/deactivate a global record without
  breaking tenants who already pulled it (tenant's pulled copy is a snapshot + reference,
  see `03_DATABASE_SCHEMA.md §3`).
- **FR-016** Data Ops sub-users shall have upload-only access (no delete, no tenant
  visibility).

### 3.3 Global Data Browsing & Pull
- **FR-020** Tenant Admin/Manager shall browse the Global Company registry with filters:
  city, state, industry, company type, incorporation date range, has-website,
  has-email/mobile, free-text search (name/CIN).
- **FR-021** Search results shall be paginated (cursor-based) and shall NOT expose raw
  contact fields (email/mobile) until pulled — list view shows company identity +
  firmographic fields only; a "Preview" shows masked contact indicators (e.g.
  "email on file: yes").
- **FR-022** Tenant Admin shall select one or more Global Companies and "Pull" them into
  their tenant's Leads; system checks remaining monthly pull quota (per plan) before
  committing.
- **FR-023** A Pull operation shall copy a snapshot of Company + associated People into
  tenant-scoped tables and record a `data_pull_log` entry (who pulled what, when, from
  which global version).
- **FR-024** Pulled leads shall be flagged `source = GLOBAL_PULL` and retain a reference
  to the originating global record for future "refresh from source" action (Phase 1).
- **FR-025** If a tenant's subscription lapses/downgrades, previously pulled leads
  remain in their account (already "owned" by the pull), but further pulls are blocked
  until quota/plan is restored.

### 3.4 Tenant CRM — Leads & Pipeline
- **FR-030** Tenant Admin shall define custom pipeline stages (name, order, color,
  is-won/is-lost flags); a sensible default stage set is seeded on tenant creation.
- **FR-031** A Lead shall always belong to exactly one pipeline stage; every stage
  change is recorded in `lead_stage_history` (from, to, by, at, optional note).
- **FR-032** Tenant users shall create Leads manually (form) or via bulk import
  (tenant's own Excel/CSV, independent of the Global Data Layer), using a
  column-mapping UI.
- **FR-033** A Lead shall support one-to-many Contacts (people at that company), each
  contact carrying its own masking status.
- **FR-034** Tenant Admin shall assign a Lead (and/or individual Contacts) to one
  `TENANT_AGENT`/`TENANT_MANAGER`; assignment change is logged.
- **FR-035** Agents shall only see Leads assigned to them (or team, if configured);
  Admin/Manager see all tenant leads by default (configurable).

### 3.5 Data Masking (core differentiator)
- **FR-040** System shall support a per-tenant Masking Policy: which fields (phone,
  email, address, LinkedIn, etc.) are masked for which role, with `TENANT_AGENT` masked
  by default out of the box.
- **FR-041** For a masked phone field, the UI shall render a "Call" action instead of
  the number; clicking it shall initiate a masked/proxied call via the telephony
  provider (click-to-call bridging agent's registered number and the lead's number
  without either seeing the other's raw number), OR — if no telephony provider is
  configured — degrade to a same-tenant "Request number reveal" workflow requiring
  Admin approval, never a silent raw-number leak.
- **FR-042** For a masked email field, the system shall send email via a
  platform-relayed address/API (agent composes, system sends, raw address never shown
  in the UI) or, as an MVP fallback without an email provider wired, opens a
  pre-filled compose action without exposing the raw address string in the DOM/API
  response payload sent to a masked role.
- **FR-043** For masked WhatsApp, the system shall use WhatsApp Business API to send
  from a tenant-registered number without exposing the lead's raw number to the agent;
  MVP fallback (no WABA configured) shall still avoid rendering the raw number to a
  masked role — showing a disabled state with an explanation rather than leaking it.
- **FR-044** Export (CSV/Excel download) and copy-to-clipboard of masked fields shall be
  disabled at the API layer (not just hidden in UI) for roles without export
  permission — the API must never return the raw field to an unauthorized caller,
  masked or not.
- **FR-045** Any export a role IS permitted to perform shall be watermarked (embedded
  requester identity + timestamp in the file) and logged.
- **FR-046** Tenant Admin shall be able to grant a temporary "reveal" exception to a
  specific agent for a specific lead, with an expiry, fully audit-logged.

### 3.6 Lead Intelligence Radar (Audit + Anomaly)
- **FR-050** Every read of a contact-bearing record, every export, every masked-call/
  WhatsApp/email action shall write a Radar Event (actor, action, entity, entity type,
  timestamp, IP, user agent).
- **FR-051** System shall provide configurable threshold rules (e.g. "> N contact views
  in T minutes", "export attempts by role X", "activity outside business hours") that
  generate an Alert visible to Tenant Admin.
- **FR-052** Tenant Admin shall be able to view a per-user Radar timeline and, from
  there, suspend the user's session/account.
- **FR-053** (Phase 1) Alerts may trigger an automated soft-lock of the acting user
  pending Admin review, per tenant-configurable policy.

### 3.7 Activities & Communication
- **FR-060** System shall log Call activities (manual entry, or auto-created from
  click-to-call webhook: duration, outcome, recording link if provider supports it).
- **FR-061** System shall log WhatsApp activities (message direction, template used,
  delivery status via webhook where available).
- **FR-062** System shall log Email activities (sent, opened [if tracked], replied
  [if inbound parsing wired]).
- **FR-063** Users shall create Follow-ups with a due date/time; system generates a
  reminder (in-app + push if PWA notification permission granted) at a configurable
  lead time before due.
- **FR-064** Follow-ups shall be editable/reschedulable at any time; history of
  reschedules retained.
- **FR-065** A Lead detail page shall show a unified, chronological Activity Timeline
  merging calls/WhatsApp/email/stage-changes/follow-ups/notes.

### 3.8 Files & Documents
- **FR-070** Users shall upload files/images against a Lead (contract, ID proof, etc.)
  up to a configurable size limit.
- **FR-071** Files shall be stored via an abstracted Storage Service (not directly
  coupled to a single provider SDK in business logic) so the backing store can be
  swapped (local disk → MinIO → S3/R2) via configuration.
- **FR-072** Storage Service shall expose an internal API sufficient to support a
  future one-click "migrate all files to new endpoint" background job (list, stream
  copy, verify, repoint, delete-old).
- **FR-073** File access shall be permission-checked per Lead visibility rules; file
  URLs shall be short-lived signed URLs, not permanently public.

### 3.9 Dashboards & Reporting
- **FR-080** Tenant dashboard shall show: leads by stage (funnel), activity volume by
  type/day, conversion rate, leads by source (global-pull/manual/import), rep
  leaderboard (activities + conversions).
- **FR-081** Super Admin dashboard shall show: global DB size/growth, upload batch
  history, active tenants, tenant pull-quota utilization, platform-wide radar alert
  counts.
- **FR-082** Dashboards shall be filterable by date range and (tenant-side) by
  team/user.

### 3.10 Subscriptions & Billing (MVP: structural, payment gateway swappable)
- **FR-090** System shall model Plans (seats, monthly pull quota, feature flags) and a
  Tenant Subscription (plan, status, renewal date).
- **FR-091** System shall enforce seat limits and pull quota at the API layer, not just
  UI.
- **FR-092** Payment capture is abstracted behind a Billing Provider interface (Razorpay
  first, swappable) — MVP may ship with manual/admin-set subscription status while the
  interface is stubbed.

### 3.11 PWA
- **FR-100** App shall be installable (manifest + service worker), with an offline
  shell for the last-viewed lead list.
- **FR-101** Click-to-call shall use `tel:` as a baseline fallback and the masked
  telephony provider flow as the primary path when configured.
- **FR-102** Click-to-WhatsApp shall use `wa.me` deep links as baseline fallback and
  WABA-relayed send as the primary path when configured.
- **FR-103** Push notifications (Web Push) shall be supported for follow-up reminders
  and radar alerts where the browser/OS permits.

### 3.12 API & MCP Readiness
- **FR-110** All functional capabilities above shall be reachable via a documented
  REST API (OpenAPI/Swagger spec auto-generated from code) using the same permission
  policy module as the web UI — no shadow/undocumented endpoints.
- **FR-111** API responses shall never include masked raw fields to a caller whose
  resolved permissions don't allow it, regardless of client type (browser, API key,
  future MCP agent).
- **FR-112** System shall reserve a namespace/service boundary (`services/mcp-gateway`)
  for a future MCP server that wraps the same permissioned API — no MVP requirement to
  ship it, but routes/DTOs should be agent-friendly (typed, documented, idempotent
  where possible).

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-01** Global Company search with filters shall return first page (≤50 rows) in
  < 800ms at 5M-row scale (requires proper indexing — see `03_DATABASE_SCHEMA.md §6`).
- **NFR-02** Lead list/dashboard pages shall render meaningful content < 2s on 4G.

### 4.2 Security
- **NFR-10** All traffic over HTTPS (TLS via Let's Encrypt/Certbot).
- **NFR-11** Passwords hashed with bcrypt/argon2; no plaintext secret storage.
- **NFR-12** Secrets/config via environment variables + `.env` excluded from VCS;
  production secrets managed via CI/CD secret store.
- **NFR-13** All masking/authorization decisions enforced server-side; client-side
  hiding is a UX nicety only, never the security boundary.
- **NFR-14** Full audit trail (Radar Events + standard audit log) retained per tenant's
  configured retention (default 12 months).
- **NFR-15** Rate limiting on auth endpoints and on masked-contact-reveal-adjacent
  actions.

### 4.3 Reliability & Availability
- **NFR-20** Target 99.5% uptime for MVP single-VPS deployment; documented planned
  maintenance windows.
- **NFR-21** Automated daily DB backups (retained 14 days minimum) with a documented
  restore runbook.
- **NFR-22** Reminder/notification jobs must be idempotent and survive a service
  restart (queue-backed, not in-memory timers).

### 4.4 Scalability
- **NFR-30** Codebase organized as a modular monolith with clear service boundaries
  (Auth, GlobalData, TenantCRM, Radar, Storage, Notifications) so any module can be
  extracted into its own deployable service later without a data-model rewrite.
- **NFR-31** Database schema designed multi-tenant-safe from day one (tenant_id on
  every tenant-scoped table + composite indexes) to support moving from shared-schema
  to schema-per-tenant or DB-per-tenant later if a large tenant needs isolation.

### 4.5 Maintainability / Vibe-Coding Support
- **NFR-40** Every module ships with: a `README.md` (purpose, boundaries), typed
  DTOs/interfaces, and unit + integration tests runnable in isolation.
- **NFR-41** Structured logging (JSON) with a `request_id`/`trace_id` propagated through
  every layer for one-click log correlation during debugging.
- **NFR-42** Centralized error taxonomy (error codes, not free-text) so both humans and
  an AI coding agent can grep/handle errors deterministically.
- **NFR-43** OpenAPI spec is the source of truth for the API; code and docs generated/
  validated against it in CI (spec drift fails the build).

### 4.6 Portability
- **NFR-50** No business logic directly calls a cloud-SDK for storage/telephony/
  WhatsApp/email — always through an internal adapter interface, enabling provider
  swap and the one-click storage migration requirement.
- **NFR-51** Entire stack runs via Docker Compose so the same definition works on a
  developer laptop, staging VPS, and production VPS.

### 4.7 Compliance / Data Governance
- **NFR-60** Global Data Layer maintains provenance (source batch, uploader, timestamp)
  for every record to support data-lineage and takedown requests.
- **NFR-61** Tenant data is logically isolated; cross-tenant data access is impossible
  through the API even with a crafted request (verified by automated tests).

---

## 5. External Interface Requirements

- **Telephony**: Exotel / Knowlarity / Twilio (India) — click-to-call bridging + call
  status webhooks.
- **WhatsApp**: Meta WhatsApp Cloud API (or BSP like Interakt/Gupshup) — template send +
  delivery webhooks.
- **Email**: SMTP relay / Postmark / SES — transactional send + open tracking (optional).
- **Payments**: Razorpay (India-first) behind a Billing Provider interface.
- **Object Storage**: S3-compatible API (MinIO self-hosted MVP; AWS S3/Cloudflare R2
  later) behind a Storage Service interface.
- **Push**: Web Push (VAPID) for PWA notifications.

## 6. Constraints

- Single Hostinger VPS for MVP — architecture must not assume a multi-node cluster is
  available, but must not preclude one later (see NFR-30/31, NFR-51).
- India-first data model (CIN/DIN) generalized via a `registry_type`/`country` field so
  other jurisdictions' identifiers can be added without a schema rewrite.

## 7. Traceability

Every `FR-xxx`/`NFR-xx` ID must appear in: (a) the relevant module's test file names,
(b) its PR description, (c) the OpenAPI `x-requirement` extension field on the endpoint
it satisfies. This closes the loop between PRD → SRS → code → tests, which is what
lets an AI coding agent be handed one ID and implement/verify it end-to-end.

## 14. Data-model amendment — 2026-09-08

### FR-DM-001 Lead contactability
The system SHALL persist primary lead contact name, email and phone directly on the `leads` record.

### FR-DM-002 Pipeline normalization
The system SHALL persist only `pipeline_stage_id` on a lead. The pipeline SHALL be resolved through `pipeline_stages.pipeline_id`. The system SHALL NOT persist a redundant `pipeline_id` on `leads`.

### FR-DM-003 Stage history
Every initial stage and subsequent stage transition SHALL be represented in `lead_stage_history`.

### FR-TEN-001 Tenant provisioning
Creating a customer organization SHALL provision a tenant, initial Tenant Admin, default pipeline and default stages atomically.

### FR-GI-001 Tenant Global Registry access
Authenticated tenant users SHALL be able to search Global Registry companies and people. They may copy records into their own CRM, but SHALL NOT mutate platform-owned records.

### FR-GI-002 Provenance
CRM records created from Global Registry SHALL retain source provenance (`source_global_company_id` / `source_global_person_id`) where applicable.
