# Jarvis CRM — Database Schema Specification

**Version:** 1.0 · **Engine:** PostgreSQL 15+ · **ORM:** Prisma (recommended)
**Companion docs:** `01_PRD.md`, `02_SRS.md`, `04_ARCHITECTURE_AND_DEVOPS.md`

---

## 1. Design Principles

1. **Two data universes, one database (MVP)**: `platform.*` (global, owned by super
   admin) and tenant-scoped tables carrying `tenant_id` on every row. Logical separation
   now, physical separation (schema-per-tenant) later if needed — see NFR-31.
2. **Pull = snapshot + reference**, never a live foreign key into the global tables from
   tenant business logic. This means a tenant's leads survive a global record being
   edited/deactivated later, while still keeping a traceable link back to source.
3. **Every sensitive field is masking-aware**: contact fields are stored normally (they
   must be, to power the call/WhatsApp/email proxy), but *all read paths* go through a
   policy layer — masking is an API/service-layer concern, not a column-encryption
   gimmick, except where noted (§7).
4. **Everything is audited**: no destructive updates without a history trail on
   business-critical entities (stage changes, assignment changes, data pulls, reveals).

---

## 2. Platform / Global Schema (`platform_*` tables)

### 2.1 `platform_companies`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| cin | varchar(21) UNIQUE | India Corporate Identification Number; nullable for non-India records (see `registry_type`) |
| registry_type | varchar(20) | `CIN`, `LLPIN`, other-country code — extensibility |
| company_name | text | |
| legal_status | varchar(30) | active/struck-off/dissolved etc. |
| company_type | varchar(50) | Pvt Ltd / Public Ltd / LLP / Proprietorship etc. |
| industry | varchar(100) | normalized industry/category |
| incorporation_date | date | nullable |
| registered_address | text | |
| city | varchar(100) | |
| state | varchar(100) | |
| country | varchar(2) | ISO code, default `IN` |
| pincode | varchar(12) | |
| website | text | |
| email | text | contact-sensitive |
| mobile | varchar(20) | contact-sensitive |
| landline | varchar(20) | contact-sensitive |
| employee_band | varchar(30) | optional firmographic |
| annual_turnover_band | varchar(30) | optional firmographic |
| first_seen_at | timestamptz | |
| last_updated_at | timestamptz | |
| last_updated_by_batch_id | uuid FK → platform_data_upload_batches | |
| is_active | boolean | soft delete/deactivate |
| created_at / updated_at | timestamptz | |

Indexes: `UNIQUE(cin)`, btree on `(city, state)`, `(industry)`, GIN trigram on
`company_name` for fuzzy search, GIN on a computed `search_vector` (tsvector) for
full-text.

### 2.2 `platform_people`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| din | varchar(20) UNIQUE NULLABLE | India Director Identification Number |
| pan | varchar(15) | optional, sensitive |
| full_name | text | |
| email | text | contact-sensitive |
| mobile | varchar(20) | contact-sensitive |
| linkedin_url | text | |
| other_socials | jsonb | `{twitter, facebook, ...}` |
| current_address | text | |
| first_seen_at | timestamptz | |
| last_updated_at | timestamptz | |
| last_updated_by_batch_id | uuid FK | |
| is_active | boolean | |
| created_at / updated_at | timestamptz | |

Indexes: `UNIQUE(din)` (nullable-unique — Postgres allows multiple NULLs), trigram on
`full_name`, btree on `mobile`, `email` (for dedupe lookups, not for public querying).

### 2.3 `platform_company_person_map`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → platform_companies | |
| person_id | uuid FK → platform_people | |
| designation | varchar(100) | Director / CEO / CFO / Authorized Signatory etc. |
| appointment_date | date | nullable |
| resignation_date | date | nullable |
| status | varchar(20) | `active` / `resigned` |
| last_updated_by_batch_id | uuid FK | |
| created_at / updated_at | timestamptz | |

Indexes: `UNIQUE(company_id, person_id, designation)`, btree on `person_id` (to answer
"which companies is this director in" fast).

### 2.4 `platform_data_upload_batches`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| uploaded_by_user_id | uuid FK → users | |
| upload_type | varchar(20) | `COMPANY` / `PEOPLE` / `MAPPING` |
| file_name | text | |
| file_storage_key | text | pointer into Storage Service, for re-download/audit |
| total_rows | int | |
| success_count | int | |
| failed_count | int | |
| status | varchar(20) | `PROCESSING` / `COMPLETED` / `FAILED` |
| started_at / completed_at | timestamptz | |
| created_at | timestamptz | |

### 2.5 `platform_data_upload_errors`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| batch_id | uuid FK → platform_data_upload_batches | |
| row_number | int | |
| raw_row | jsonb | original row as parsed |
| error_message | text | |

---

## 3. Tenant Schema (`tenant_*` tables — every row carries `tenant_id`)

### 3.1 `tenants`
`id, name, slug, plan_id (FK subscription_plans), status (trial/active/suspended/
cancelled), created_at`

### 3.2 `subscription_plans`
`id, name, price_monthly, seat_limit, monthly_pull_quota, feature_flags jsonb,
is_active`

### 3.3 `tenant_subscriptions`
`id, tenant_id, plan_id, status (active/past_due/cancelled), current_period_start,
current_period_end, pulls_used_this_period, seats_used`

### 3.4 `users`
`id, tenant_id (nullable for platform users), platform_role (SUPER_ADMIN/DATA_OPS/null),
tenant_role (TENANT_ADMIN/TENANT_MANAGER/TENANT_AGENT/null), full_name, email
(unique), password_hash, permission_overrides jsonb, status (active/invited/
suspended), invited_by, created_at`

> A `platform` user has `tenant_id = NULL` and a `platform_role`. A tenant user has
> `tenant_id` set and a `tenant_role`. This lets the same `users` table serve both
> universes cleanly.

### 3.5 `leads` (tenant-owned Companies)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tenant_id | uuid FK | |
| source | varchar(20) | `GLOBAL_PULL` / `MANUAL` / `IMPORT` |
| source_global_company_id | uuid NULLABLE | reference only, no FK enforcement across schemas in MVP (app-level integrity) |
| source_pull_log_id | uuid NULLABLE FK → data_pull_log | |
| company_name | text | |
| cin | varchar(21) | copied snapshot, nullable |
| industry, city, state, country, pincode, website | … | snapshot fields, same shapes as `platform_companies` |
| email, mobile, landline | text/varchar | snapshot fields — masking-sensitive |
| pipeline_stage_id | uuid FK → pipeline_stages | |
| assigned_to_user_id | uuid NULLABLE FK → users | |
| created_by_user_id | uuid FK | |
| custom_fields | jsonb | tenant-defined extra fields |
| created_at / updated_at | timestamptz | |

Indexes: `(tenant_id, pipeline_stage_id)`, `(tenant_id, assigned_to_user_id)`, trigram
on `company_name` scoped by `tenant_id`.

### 3.6 `lead_contacts`
`id, tenant_id, lead_id FK, source_global_person_id NULLABLE, full_name, designation,
email, mobile, linkedin_url, custom_fields jsonb, created_at, updated_at`

### 3.7 `pipeline_stages`
`id, tenant_id, name, sort_order, color, is_won boolean, is_lost boolean,
is_default boolean, created_at`

### 3.8 `lead_stage_history`
`id, tenant_id, lead_id FK, from_stage_id NULLABLE, to_stage_id, changed_by_user_id,
note, changed_at`

### 3.9 `lead_assignment_history`
`id, tenant_id, lead_id FK, from_user_id NULLABLE, to_user_id, changed_by_user_id,
changed_at`

### 3.10 `activities` (unified call/whatsapp/email/note/meeting log)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tenant_id | uuid FK | |
| lead_id | uuid FK | |
| contact_id | uuid NULLABLE FK → lead_contacts | |
| user_id | uuid FK | actor |
| type | varchar(20) | `CALL` / `WHATSAPP` / `EMAIL` / `NOTE` / `MEETING` / `STAGE_CHANGE` |
| direction | varchar(10) | `OUTBOUND` / `INBOUND` |
| channel_meta | jsonb | provider message id, call sid, duration, outcome, delivery status |
| body_snippet | text | short preview only (full content may live in provider system, not duplicated for masked channels) |
| occurred_at | timestamptz | |
| created_at | timestamptz | |

Indexes: `(tenant_id, lead_id, occurred_at desc)` — powers the unified timeline.

### 3.11 `followups`
`id, tenant_id, lead_id FK, contact_id NULLABLE, assigned_to_user_id, due_at,
reminder_lead_minutes, status (pending/done/rescheduled/cancelled), notes,
created_by_user_id, created_at, updated_at`

### 3.12 `followup_reschedule_history`
`id, tenant_id, followup_id FK, old_due_at, new_due_at, changed_by_user_id, changed_at`

### 3.13 `data_pull_log`
`id, tenant_id, user_id (who pulled), global_company_id, snapshot_taken_at,
lead_id (resulting lead), plan_id_at_time, created_at`

### 3.14 `documents`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tenant_id | uuid FK | |
| lead_id | uuid NULLABLE FK | |
| uploaded_by_user_id | uuid FK | |
| file_name | text | |
| mime_type | varchar(100) | |
| size_bytes | bigint | |
| storage_provider | varchar(30) | `LOCAL` / `MINIO` / `S3` / `R2` — abstraction marker |
| storage_key | text | opaque key resolved by Storage Service |
| checksum_sha256 | varchar(64) | integrity check, also used by migration job |
| created_at | timestamptz | |

### 3.15 `masking_policies`
`id, tenant_id, role (TENANT_AGENT/…), field_name (email/mobile/linkedin_url/…),
is_masked boolean, allow_export boolean, created_at, updated_at`
— seeded with sane defaults per tenant creation (agents masked, managers unmasked).

### 3.16 `reveal_exceptions`
`id, tenant_id, lead_id NULLABLE, contact_id NULLABLE, granted_to_user_id,
granted_by_user_id, field_name, expires_at, reason, created_at`

### 3.17 `radar_events` (audit + anomaly input)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| tenant_id | uuid FK | |
| actor_user_id | uuid FK | |
| action | varchar(40) | `VIEW_CONTACT` / `EXPORT` / `MASKED_CALL` / `MASKED_WHATSAPP` / `MASKED_EMAIL` / `REVEAL_REQUEST` / `REVEAL_GRANT` / `LOGIN` / … |
| entity_type | varchar(30) | `LEAD` / `CONTACT` / `DOCUMENT` / … |
| entity_id | uuid | |
| ip_address | inet | |
| user_agent | text | |
| metadata | jsonb | action-specific payload |
| occurred_at | timestamptz | |

Indexes: `(tenant_id, actor_user_id, occurred_at)` for rolling-window anomaly queries
(consider partitioning by month at scale).

### 3.18 `radar_alert_rules`
`id, tenant_id, name, rule_type (THRESHOLD_COUNT/OFF_HOURS/…), config jsonb
(e.g. {action:"VIEW_CONTACT", count:200, window_minutes:10}), is_active,
auto_lock_on_trigger boolean`

### 3.19 `radar_alerts`
`id, tenant_id, rule_id FK, actor_user_id, triggered_at, status (open/acknowledged/
dismissed), acknowledged_by_user_id, acknowledged_at, details jsonb`

### 3.20 `audit_log` (generic CRUD audit, distinct from radar behavioral events)
`id, tenant_id NULLABLE (null = platform action), actor_user_id, entity_type,
entity_id, action (CREATE/UPDATE/DELETE), before jsonb, after jsonb, occurred_at`

---

## 4. Entity Relationship Summary (textual ERD)

```
platform_companies 1───* platform_company_person_map *───1 platform_people
        │ (referenced by, snapshot only)                       │
        ▼                                                      ▼
     data_pull_log ─────────────────────────────────────► lead_contacts
        │                                                       ▲
        ▼                                                       │
      leads 1───────────────────────────────────────────────────┘
        │
        ├──1───* lead_stage_history
        ├──1───* lead_assignment_history
        ├──1───* activities ───* (contact_id → lead_contacts)
        ├──1───* followups ───* followup_reschedule_history
        └──1───* documents

tenants 1───* users 1───* radar_events
tenants 1───* masking_policies
tenants 1───* radar_alert_rules 1───* radar_alerts
```

## 5. Multi-Tenancy Enforcement

- Every tenant-scoped query MUST filter by `tenant_id` derived from the authenticated
  session — enforced in a single repository/query-builder layer (see
  `05_DEVELOPMENT_BIBLE.md §Data Access Layer`), never assembled ad hoc per-route.
- Add a Postgres Row-Level Security (RLS) policy per tenant table as a defense-in-depth
  layer for MVP+1: `USING (tenant_id = current_setting('app.current_tenant')::uuid)`,
  set via `SET LOCAL app.current_tenant` at the start of each transaction.
- Automated test suite MUST include cross-tenant access attempts that assert 403/404,
  not silent empty results (NFR-61).

## 6. Indexing & Performance Notes

- Full-text search on `platform_companies.company_name` and `platform_people.full_name`
  via `tsvector` + GIN, refreshed on write (trigger or app-level on upsert).
- Composite indexes for the two hottest paths: global browse-by-filter, and tenant
  lead-list-by-stage/assignee.
- Consider table partitioning (by month) for `radar_events` and `activities` once
  volume passes a few million rows/tenant-month.

## 7. Sensitive Field Handling

- Contact fields (`email`, `mobile`, `pan`, `din`) are stored as plain columns (needed
  for real call/WhatsApp/email proxying) but:
  - Encrypted at rest via PostgreSQL `pgcrypto` column-level encryption OR full-disk/
    volume encryption at minimum (choose column-level for `pan`/`din` specifically —
    high-sensitivity national IDs).
  - Never selected by the ORM layer for a masked-role query — the repository layer
    exposes two explicit read methods, `getForDisplay(role)` and
    `getForProxyAction(action)`, so "forgot to mask" becomes a code-review-visible
    mistake rather than a silent leak.
- All exports go through a single `ExportService` that (a) checks
  `masking_policies.allow_export`, (b) strips disallowed fields server-side, (c)
  watermarks the file, (d) writes a `radar_events` `EXPORT` record — no export path may
  bypass this service.

## 8. Migration & Seed Strategy

- Use Prisma Migrate (or equivalent) with one migration per PR; never hand-edit a
  shipped migration.
- Seed script creates: default pipeline stages, default masking policy set, a demo
  tenant + demo global data sample for local dev — keeps "vibe coding" sessions
  reproducible (`npm run seed`).
