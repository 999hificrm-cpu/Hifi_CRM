# AI Engineering Guidelines & Architecture Bible

## Core Architecture Principles
1. **Modular Monolith**: Clean domain boundaries (`organizations`, `users`, `companies`, `contacts`, `leads`, `pipelines`, `activities`, `tasks`, `imports`, `radar`, `ai`).
2. **Multi-Tenancy & Isolation**:
   - `organizations` is the tenant boundary.
   - Every tenant-owned row MUST carry `organization_id`.
   - `tenant_id` is always derived server-side from JWT token via `get_tenant_id` dependency, NEVER from unauthenticated client payloads.
3. **Domain Entity Integrity**:
   - No `crm_people` table or duplicate registries.
   - Contacts belong to `contacts` table (linking to `organization_id` and optional `company_id`).
   - Leads represent sales opportunities linking to `contact_id`, `company_id`, and `pipeline_stage_id`.
4. **Pipeline Immutability During Imports**:
   - Ingesting 1,000 or 100,000 leads creates lead rows referencing existing pipeline stages.
   - Batch imports NEVER mutate, duplicate, or delete pipeline or stage configuration.
   - Every stage transition appends an immutable row to `lead_stage_history`.
5. **Data Masking & Anti-Theft**:
   - Roles like `TELECALLER` receive masked phone numbers (`+91 98**** 1234`) and emails (`ex****@domain.com`) in API responses.
   - One-click actions (Call, WhatsApp, Email) use proxied or application triggers without leaking raw contact databases.
   - Bulk exports are restricted and auditable.
6. **Asynchronous Ingestion**:
   - High-volume imports run asynchronously with progress tracking, row-level error isolation, and deduplication.
