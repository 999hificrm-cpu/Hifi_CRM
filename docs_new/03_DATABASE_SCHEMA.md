# JARVIS CRM — Canonical Database Schema

**Version:** 2.0 · **Updated:** 2026-09-08 · **Engine:** PostgreSQL 14+
**Migration head:** `20260908_0007`

This document supersedes the earlier schema draft. The executable source of truth is the Alembic migration chain under `apps/api/migrations/versions/`.

## 1. Core architectural decision

Jarvis uses **shared-schema multi-tenancy** for the MVP:

- `tenants` is the customer isolation boundary.
- Every customer-owned row carries `tenant_id`.
- A user belongs to either a tenant (`tenant_id != NULL`, `tenant_role`) or the platform (`tenant_id = NULL`, `platform_role`).
- Creating an organization provisions a tenant, initial Tenant Admin and a private default sales pipeline/stages in one transaction.
- We do **not** create a PostgreSQL schema/database for every user. That would create operational overhead without improving the normal SaaS isolation model. Physical database/schema isolation remains an enterprise deployment option later.

### Organization vs tenant

In product language, a customer "organization" is the tenant. The current implementation uses `tenants` consistently. Do not introduce a second `organizations` table merely to rename this concept.

## 2. Global vs tenant data

```text
PLATFORM / GLOBAL
  platform_companies
  platform_people
  platform_company_person_map
  platform_data_upload_batches
  platform_data_upload_errors

TENANT / CUSTOMER CRM
  tenants
  users
  crm_companies
  crm_people
  pipelines
  pipeline_stages
  leads
  lead_stage_history
  lead_assignments
  activities
  tasks
  calendar_events
  notifications
```

Global data is a reusable intelligence registry. Tenant CRM data is owned by the customer. Pulling a global record into CRM is a **copy/snapshot operation**, not a live ownership transfer.

## 3. Leads are opportunities, not pipelines

The canonical `leads` row contains:

| Field | Purpose |
|---|---|
| `id` | Lead/opportunity identity |
| `tenant_id` | Customer ownership/isolation |
| `company_id` | Optional tenant CRM company |
| `crm_person_id` | Optional tenant CRM contact |
| `pipeline_stage_id` | **Current stage only** |
| `source_global_company_id` | Optional provenance from Global Registry |
| `source_global_person_id` | Optional provenance from Global Registry |
| `owner_id` | Current owner |
| `title` | Opportunity title |
| `contact_name` | Primary contact snapshot |
| `contact_email` | Primary contact email snapshot |
| `contact_phone` | Primary contact phone snapshot |
| `source` | MANUAL / IMPORT / GLOBAL_PULL / etc. |
| `score` | Qualification/radar score |
| `value` | Estimated deal value |
| `priority` | LOW / MEDIUM / HIGH / URGENT |
| `status` | OPEN / other lifecycle states |
| `notes` | Opportunity notes |

### Why there is no `pipeline_id` on `leads`

A lead's pipeline is determined by `pipeline_stage_id → pipeline_stages.pipeline_id → pipelines`. Storing both `pipeline_id` and `pipeline_stage_id` duplicates state and allows contradictory combinations.

Changing a lead from one stage to another updates **one lead row** and appends a row to `lead_stage_history`. It does not rewrite or overwrite the pipeline table, and 1,000 imported leads do not cause the pipeline definition to be recreated 1,000 times.

## 4. Contact model

Lead contact information is intentionally available on the lead for fast CRM list/detail queries and communication workflows.

`crm_people` is the normalized tenant contact entity for reusable people and links to `platform_people` when the contact originated in Global Registry.

This gives Jarvis both:

1. a practical primary-contact snapshot on the opportunity; and
2. a reusable contact entity for future multi-contact CRM workflows.

## 5. Pipeline model

```text
tenants
  └── pipelines
        └── pipeline_stages
              └── leads.pipeline_stage_id
```

`pipelines` and `pipeline_stages` are **configuration tables**. They are not per-lead data.

`lead_stage_history` records every stage transition. `lead_assignments` records every ownership assignment.

## 6. Global Registry → CRM flow

```text
Global Registry
     │
     ├── Browse company/person
     │
     ├── Add to CRM
     │      └── creates tenant-owned crm_company/crm_person
     │
     └── Create lead
            └── creates tenant-owned lead
                 ├── copies contact data
                 ├── records source_global_* provenance
                 ├── records initial stage history
                 └── records initial assignment
```

A tenant user cannot mutate the platform/global record.

## 7. File ingestion

The file-import lifecycle is:

```text
Upload
 → platform_data_upload_batches
 → Redis/Celery
 → Parse
 → Normalize
 → Validate
 → Deduplicate / Upsert
 → row errors
 → batch totals
 → COMPLETED / PARTIAL / FAILED
```

Supported formats: CSV, XLSX, XLSM.

- Platform admins: COMPANY, PEOPLE, and targeted LEADS imports.
- Tenant users: LEADS imports into their own tenant only.
- A Super Admin importing leads must explicitly select the target tenant.
- The worker resolves a tenant-local active user as owner/creator; a tenantless platform user is never written into tenant lead ownership fields.

## 8. Tenant provisioning

Creating a customer provisions, atomically:

1. `tenants` row
2. subscription plan reference
3. initial `TENANT_ADMIN` user
4. default `Sales Pipeline`
5. six default stages
6. audit record

Subsequent users are always created with the target tenant ID. There is no unscoped customer user.

## 9. Security invariants

- Tenant endpoints derive `tenant_id` from the authenticated user, never from arbitrary request data.
- Platform users can have read-only cross-tenant lead visibility for operational oversight.
- Platform visibility does not grant tenant mutation permissions.
- Global Registry tenant endpoints are read/copy operations; global source records remain platform-owned.
- Contact email/phone are protected data and must be handled through authorization/masking policies as those policies mature.

## 10. Migration history

```text
0001_phase2
  ↓
20260908_0002
  ↓
20260908_0003_phase3_execution
  ↓
20260908_0004_phase3_data_ingestion
  ↓
20260908_0005_phase3_import_hardening
  ↓
20260908_0006_crm_normalization
  ↓
20260908_0007_crm_people_and_links
```

Never edit an already-applied migration. Add a new migration for schema changes.

## 11. Important repair from the earlier supplied SQL

The earlier `jarvis_crm_phase2_schema.sql` draft mixed a different `organizations`-based model with the application's `tenants`-based model and ended with `DROP SCHEMA public CASCADE`. That file must **not** be treated as the executable production schema.

The canonical runtime schema is now defined by Alembic and this document. The earlier file is retained only as historical design material.
