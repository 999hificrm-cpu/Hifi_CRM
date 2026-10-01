# Jarvis CRM --- Master Build Plan

Version: 1.0 Status: Execution Plan Planning horizon: 12 weeks / 60
working days Product: Jarvis CRM --- Lead Intelligence Radar +
Controlled Outbound CRM

## 0. Executive Decision

Jarvis is being built as a **modular-monolith SaaS**, not as
microservices.

The product loop is:

DISCOVER → UNDERSTAND → SELECT → CONTROL → ASSIGN → CONTACT → TRACK →
LEARN → PRIORITIZE → CONVERT

The MVP must prove three things:

1.  Global data can be standardized and safely pulled into a tenant CRM.
2.  Employees can work leads without receiving unauthorized raw contact
    data.
3.  Management can see exactly what happened to every important record.

The attached specifications already establish the core boundaries:
Global Intelligence, Customer CRM, Control/RBAC/Audit, Communications,
File Engine, and future Intelligence/AI. The build plan below follows
that architecture rather than attempting to build every future feature
at once.

## 1. Critical Architecture Freeze Before Coding

There is one contradiction in the supplied documents that must be
resolved deliberately:

-   The Development Bible says TypeScript everywhere and describes a
    NestJS/Prisma-oriented repository.
-   The architecture recommendation in the supplied master PDF
    recommends React + TypeScript on the frontend and FastAPI +
    Pydantic + SQLAlchemy + Alembic on the backend.

### Recommended decision

For Jarvis, use:

-   Frontend: React + TypeScript + Vite
-   UI: Tailwind CSS + shadcn/ui
-   Routing: React Router
-   Server state: TanStack Query
-   PWA: service worker + manifest
-   Backend: FastAPI + Python
-   Validation: Pydantic
-   ORM: SQLAlchemy
-   Migrations: Alembic
-   Database: PostgreSQL
-   Queue/cache: Redis
-   Worker: Celery or an equivalent Redis-backed worker abstraction
-   Object storage: MinIO/S3-compatible API
-   Reverse proxy: Nginx
-   Containers: Docker Compose
-   CI/CD: GitHub Actions
-   Tests: Pytest + HTTP client/integration tests + Playwright
-   Observability: structured JSON logs + request_id + trace_id;
    provider-neutral integration for Sentry/OpenTelemetry later

Reason: Jarvis has unusually heavy CSV/Excel processing, entity
resolution, data quality, analytics, and future AI work. Python gives a
cleaner path for those workloads.

### Required action

Before Day 1 coding:

-   Create ADR-008: FastAPI backend decision.
-   Update the Development Bible so the selected stack is authoritative.
-   Remove conflicting framework references.
-   Never allow an AI coding agent to decide the stack again.

## 2. MVP Boundary

### P0 --- Must ship

-   Multi-tenancy
-   Authentication
-   Sessions
-   RBAC
-   Organizations
-   Platform admin
-   Global Company Registry
-   Global People Registry
-   Company ↔ Person relationships
-   Global CSV/Excel imports
-   Validation and deduplication
-   Import history/error reports
-   Global search/filter
-   Global record preview
-   Pull global records into tenant
-   Pull quota
-   Tenant CRM companies/leads/contacts
-   Manual lead creation
-   Tenant CSV import
-   Lead assignment
-   Custom pipeline stages
-   Stage history
-   Activities
-   Tasks
-   Follow-ups
-   Calendar/reminders
-   Basic call/WhatsApp/email action layer
-   Data masking v1
-   Audit logging
-   Export restrictions
-   Admin dashboards
-   PWA shell
-   File metadata + MinIO object storage
-   Dockerized deployment
-   GitHub CI/CD
-   Backup/restore procedure
-   Health checks
-   Structured logs
-   Automated tests
-   Documentation/source-of-truth system

### P1 --- Do not block MVP

-   Advanced Radar anomaly engine
-   Configurable risk rules
-   Watermarked exports
-   Advanced analytics
-   Full WhatsApp Business integration
-   Transactional email provider
-   Notification engine
-   Data quality dashboard
-   Campaigns
-   Advanced file migration
-   Rich source ROI analytics

### P2 --- Future AI platform

-   AI lead summaries
-   AI lead scoring
-   Next-best action
-   AI message drafting
-   Conversation intelligence
-   AI data cleaning
-   AI enrichment
-   MCP server
-   External connectors
-   Predictive conversion
-   Autonomous workflows

## 3. Architecture

``` text
                        JARVIS PLATFORM
                              |
             +----------------+----------------+
             |                |                |
       GLOBAL DATA        TENANT CRM       PLATFORM
       INTELLIGENCE       WORKSPACE        SERVICES
             |                |                |
       Companies         Leads/Contacts   Auth/RBAC
       People            Pipeline         Billing
       Relationships     Activities       Audit
       Sources           Tasks            Analytics
       Imports           Followups        Settings
             |                |                |
             +----------------+----------------+
                              |
                       CONTROL / POLICY
                    RBAC + Masking + Audit
                              |
                       EVENT / JOB LAYER
                         Redis + Workers
                              |
             +----------------+----------------+
             |                |                |
        Communications     File Service      Future AI
        Call/WA/Email      MinIO/S3          Domain Tools
```

### Data principle

Keep these logically separate:

-   Global Intelligence
-   Tenant CRM
-   CRM Activity/Audit
-   File/Object Storage

A global record is never treated as a live tenant CRM foreign key. A
pull creates a tenant snapshot plus a source reference.

## 4. Repository Target

``` text
jarvis-crm/
├── apps/
│   ├── web/
│   └── api/
├── workers/
├── packages/
│   └── shared-types/
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── scripts/
├── prisma/                         # only if legacy Prisma is retained; otherwise remove
├── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── e2e/
├── docs/
│   ├── 00-BIBLE/
│   ├── 01-PRD/
│   ├── 02-SRS/
│   ├── 03-ARCHITECTURE/
│   ├── 04-DATABASE/
│   ├── 05-SECURITY/
│   ├── 06-UX/
│   ├── 07-API/
│   ├── 08-TESTING/
│   ├── 09-DEPLOYMENT/
│   ├── 10-CHANGELOG/
│   ├── 11-PROGRESS/
│   └── adr/
├── .github/workflows/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── AGENTS.md
├── AI_RULES.md
├── ARCHITECTURE.md
└── README.md
```

## 5. Development Method

Every AI coding task follows:

READ DOCS → INSPECT REPO → PLAN → IMPLEMENT SMALL CHANGE → TEST → LINT →
TYPECHECK → BUILD → UPDATE DOCS → REPORT

Never ask an AI agent to "build the whole CRM."

Use one FR or one tightly coupled feature cluster per task.

Every feature must contain:

-   UI
-   API
-   Database
-   Authorization
-   Validation
-   Audit where applicable
-   Tests
-   Error handling
-   Loading state
-   Empty state
-   Responsive state
-   Documentation

## 6. 12-Week Build Roadmap

### Week 1 --- Foundation

Goal: repository is runnable locally and in CI.

Build: - monorepo structure - Docker Compose - PostgreSQL - Redis -
FastAPI - React/Vite - environment configuration - health endpoint -
structured logging - request/trace IDs - error taxonomy - GitHub
Actions - test harness - documentation skeleton - seed framework

Exit criteria: - one command starts the stack - CI runs
lint/type/test/build - `/health` reports DB and Redis status - no
secrets committed - baseline docs exist

### Week 2 --- Auth, Organization, RBAC

Build: - users - organizations - invitations - login - refresh tokens -
sessions - password reset foundation - platform roles - tenant roles -
permission registry - tenant context middleware - route authorization

Security tests: - tenant A cannot read tenant B - agent cannot access
admin APIs - suspended user cannot operate - expired invite rejected

Exit criteria: - Super Admin and Tenant Admin can log in - Tenant Agent
has restricted access - cross-tenant tests pass

### Week 3 --- Global Intelligence Data Model

Build: - global companies - global people - relationships - sources -
data update metadata - import batches - import errors - provenance -
indexes - search fields

Build first: - company CRUD/read service - people read service -
relationship service - source service

Exit criteria: - seeded global dataset browsable - CIN/DIN uniqueness
works - company/person relationships query correctly

### Week 4 --- Import Engine

Build: - CSV upload - Excel upload - column detection - mapping -
validation - normalization - company upsert by CIN - person upsert by
DIN - fallback duplicate review - relationship mapping - async job
processing - progress state - failed-row report - import history

Performance requirement: - large imports never block the browser request

Exit criteria: - test import with representative large file - successful
and failed rows are separately reported - rerunning the same dataset
does not create duplicates

### Week 5 --- Global Explorer + Pull

Build: - global company search - global people search - filters -
pagination - company detail - people detail - relationship view - masked
contact indicators - select records - quota validation - pull
transaction - pull history - tenant snapshot creation

Exit criteria: - tenant can search - tenant can select - quota is
enforced - pulled records appear in private CRM - global changes do not
silently mutate tenant snapshots

### Week 6 --- Tenant CRM Core

Build: - CRM companies - leads - contacts - manual creation - tenant CSV
import - assignment - assignment history - ownership - custom fields -
lead detail - lead list - search/filter

Exit criteria: - Tenant Admin can create/import leads - Admin can
assign - Agent sees only authorized leads - every assignment is
auditable

### Week 7 --- Pipeline + Activities + Tasks

Build: - custom pipelines - stages - stage ordering - won/lost flags -
stage history - notes - calls - WhatsApp activity records - email
activity records - meetings - tasks - follow-ups - calendar events -
reminder scheduling

Exit criteria: - lead can travel through a complete pipeline - every
stage transition is preserved - follow-up creates
task/calendar/reminder - timeline shows chronological activity

### Week 8 --- Controlled Communications + Masking

Build: - field masking policy - role-based field visibility -
click-to-call adapter - WhatsApp adapter - email adapter - provider
interfaces - mock providers - action logging - reveal request workflow -
export restriction - copy protection at API layer

Critical rule: Raw contact data must never be returned to an
unauthorized role merely because the frontend hides it.

Exit criteria: - Telecaller sees masked phone/email - click-to-call
works against a mock provider - action is logged - unauthorized API
request cannot obtain raw data - provider can be swapped without
changing business logic

### Week 9 --- Audit + Radar Foundation

Build: - audit event service - sensitive access events - record view
events - export events - communication events - assignment events -
permission changes - data pulls - per-user timeline - security dashboard
foundation - basic threshold rules

Initial Radar rules: - excessive contact views - excessive export
attempts - off-hours access - repeated failed actions - unusual bulk
access

Exit criteria: - management can answer who/what/when - threshold event
produces alert - suspicious user can be suspended

### Week 10 --- Dashboards + PWA + Notifications

Build: - platform dashboard - tenant admin dashboard - manager
dashboard - agent dashboard - telecaller dashboard - funnel metrics -
activity metrics - source metrics - PWA installation - mobile responsive
UX - notification service - follow-up reminders - push notification
foundation

Exit criteria: - critical journeys work on desktop and mobile -
dashboard numbers reconcile with underlying data

### Week 11 --- File Engine + Deployment Hardening

Build: - file metadata model - File Service - MinIO adapter - signed
URLs - MIME validation - size limits - access control -
upload/download/delete audit - checksum - backup scripts - restore
scripts - production Docker Compose - Nginx - TLS - staging deployment -
production deployment

Exit criteria: - upload file against lead - file is private - direct
public URL is impossible - backup can be restored - staging deployment
is automated

### Week 12 --- Security, UAT, Performance, Release

Build: - end-to-end Playwright journeys - tenant isolation suite -
masking suite - import load test - dashboard performance checks -
error-path testing - rate limiting - session revocation - security
review - backup/restore drill - production smoke tests - changelog -
release notes - UAT fixes

Release gate: - no P0 security defects - cross-tenant suite green -
masked-role suite green - import pipeline stable - backup restore
verified - CI green - production health green - UAT signed off

## 7. Recommended Feature Dependency Order

``` text
Foundation
   ↓
Auth/RBAC
   ↓
Global Data Model
   ↓
Import Engine
   ↓
Global Explorer
   ↓
Pull Engine
   ↓
Tenant CRM
   ↓
Pipeline
   ↓
Activities/Tasks
   ↓
Masking + Communications
   ↓
Audit
   ↓
Radar
   ↓
Dashboards/PWA
   ↓
Files
   ↓
Deployment Hardening
   ↓
UAT
   ↓
MVP Release
```

Do not reverse this order casually. In particular, do not build AI
before the domain services and authorization boundaries are stable.

## 8. AI Vibe-Coding Protocol

Every prompt to an AI coding agent should include:

-   exact FR/NFR IDs
-   exact module
-   relevant Bible section
-   expected files
-   constraints
-   tests required
-   documentation updates required
-   explicit "inspect existing code before creating anything"

Example:

> Implement FR-041 in the Communications module. First inspect the
> existing auth, permission, lead, adapter, and audit services. Do not
> create duplicate abstractions. Implement masked click-to-call through
> the TelephonyProvider interface. Raw contact data may only be obtained
> inside the proxy-action service. Add unit and integration tests
> proving a TENANT_AGENT cannot retrieve the raw phone number. Add the
> FR ID to the test and OpenAPI contract. Run lint, typecheck, tests,
> and update module README.

## 9. Definition of Done

A feature is Done only when:

-   code merged
-   migrations applied
-   API contract updated
-   permissions enforced
-   audit added where required
-   tests green
-   cross-tenant test added where tenant data is involved
-   loading/error/empty states implemented
-   responsive UI verified
-   documentation updated
-   CI green
-   staging smoke test passed
-   progress tracker updated

## 10. MVP Release Gates

### Security gate

-   zero known cross-tenant access paths
-   zero unauthorized raw contact API exposure
-   exports permission-controlled
-   sessions revocable
-   secrets absent from repository

### Data gate

-   deterministic CIN/DIN dedupe
-   import errors downloadable
-   provenance preserved
-   pull snapshots traceable

### CRM gate

-   lead assignment works
-   pipeline history works
-   activity timeline works
-   follow-ups/reminders work

### Operations gate

-   Docker production stack works
-   GitHub deploy works
-   backup works
-   restore works
-   health endpoint works
-   logs contain request_id/trace_id

### Product gate

A fresh tenant should be able to:

1.  sign up/login
2.  configure organization
3.  invite telecaller
4.  search global data
5.  pull a lead
6.  assign it
7.  open it as telecaller
8.  see masked contact fields
9.  contact through supported action
10. record outcome
11. create follow-up
12. move pipeline stage
13. see activity in admin dashboard
14. inspect audit history

## 11. Post-MVP Sequence

Phase 1: - Radar rules - advanced data usage analytics - watermarked
exports - real WhatsApp Business API - transactional email - advanced
notifications - data quality

Phase 2: - AI service - domain AI tools - MCP server - lead summaries -
next-best action - AI scoring - AI message drafting

Phase 3: - enrichment - intent signals - predictive conversion -
autonomous workflows - global data marketplace

## 12. Product North Star

Primary metric:

**Qualified Opportunities Converted Per Unit of Data**

Secondary metrics:

-   global data → CRM pull rate
-   CRM → contacted rate
-   contacted → interested rate
-   interested → opportunity rate
-   opportunity → won rate
-   unauthorized exposure incidents
-   import dedupe accuracy
-   call-log capture rate
