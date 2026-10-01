# JARVIS CRM - SOURCE OF TRUTH

This is the **CANONICAL SOURCE OF TRUTH** for JARVIS CRM business rules and logic.

*Note: Documentation describes the actual implementation. Documentation must NOT define behavior that the code does not implement.*

## Source-of-Truth Hierarchy

1. **LEVEL 1**: Database + DB constraints
2. **LEVEL 2**: Backend services/business rules
3. **LEVEL 3**: API authorization/contracts
4. **LEVEL 4**: Frontend state/UI
5. **LEVEL 5**: Documentation

---

## Authoritative Sources Table

| Domain | Authoritative Source | Not Authoritative | Reason |
| --- | --- | --- | --- |
| **Tenant** | Authenticated server-side tenant context (`get_tenant_id`) | Client payloads, Frontend state | Prevents tenant spoofing. |
| **User** | Authenticated JWT User | Frontend local storage | Only signed JWT verifies identity securely. |
| **Role** | Backend RBAC (`User.tenant_role`) | UI hiding / conditional rendering | Frontend UI can be tampered with. |
| **Lead Owner** | `Lead.owner_id` | Frontend assignment tables | DB is the absolute truth for ownership. |
| **Lead Stage** | Persisted pipeline stage on `Lead` | Call Outcome | Stages only change when explicitly updated. |
| **Stage History** | Persisted `LeadStageHistory` audit | `Activity` logs alone | Dedicated history guarantees tracking. |
| **Call** | Actual `CallRecord` in the database | `Activity` (task completion) | Activity creation is not proof of call finalization. |
| **Call Outcome** | Finalized `CallRecord` outcome | `Activity` descriptions | Only `CallRecord` holds telephony result. |
| **Call KPI** | `CallRecord` aggregation | Frontend counters | Target counts require verified completed records. |
| **Follow-up** | Active persisted `FOLLOW_UP` Task | Call History, Lead Stage | A lead is Follow-Up ONLY if an explicit Task exists. |
| **Follow-up Due** | `Task.due_at` + `status=PENDING` | `overdue` flag | Overdue is derived from `due_at < now`. |
| **Follow-up Completion**| Persisted `Task.status=COMPLETED` | Frontend removal | Must change backend state to drop from queue. |
| **Target** | `TelecallerTarget` table | Hardcoded goals | Targets are dynamically set by Org Admin. |
| **Target Actuals** | `CallRecord` derived metrics | Activities or Lead statuses | True talk time/connects depend on finalized calls. |
| **Shift** | Persisted `AttendanceSession` | Frontend timer | Shift duration is tracked via server timestamps. |
| **Product/Service** | Organization-scoped `ProductService` | Global Registry | Each tenant has their own pricing/products. |
| **Lead Purpose** | `Lead.purpose` | Notes | Hard requirement for specific domains. |
| **Assignment** | Backend `get_leads_available_for_assignment` API | Frontend filtering | Prevents exposing cross-telecaller data. |
| **Assignment History**| `LeadAssignment` | Activities alone | Strict audit log of all owner changes. |
| **Global Company** | `GlobalCompany` + tenant `Company` projection | Unsynced frontend forms | Master data prevents duplicates and deduplicates leads. |
| **Global People** | `GlobalPerson` + tenant `Contact` projection | Generic CRM contacts | Same as Global Company. |
| **Quota** | Successful claim/projection count | Requested size | Deduction only occurs for successful inserts. |
| **Dashboard Metrics** | Backend authoritative aggregation | React state | Ensures consistency across sessions and users. |
| **Worklist Class.** | Backend Lead query with `status=NEW` | "Call Activity exists" | Business rules define freshness (e.g. requires outreach). |

---

## Detailed Definitions

### Tenant Identity & Security
- **Tenant Identity**: Must be derived server-side via `get_tenant_id` from the secure JWT. 
- **Tenant Security**: NEVER trust `organization_id` sent in unauthenticated client payloads. Frontend filtering is NOT a security boundary.

### Lead Ownership & Assignment
- **Lead Ownership**: `Lead.owner_id` is the current absolute owner.
- **Assignment Eligibility**: Evaluated strictly by `GET /leads/available-for-assignment`. For selected Telecaller A, only leads where `owner_id IS NULL` or `owner_id == A` are eligible. Other telecallers' leads are completely excluded by the backend.
- **Assignment History**: A dedicated `LeadAssignment` record captures every assignment/reassignment.

### Stage vs. Call Outcome
- **CALL OUTCOME != LEAD STAGE**
- **Call Outcome**: What happened during the call (Connected, Busy, No Answer). Authoritative source is the `CallRecord`.
- **Lead Stage**: Where the lead is in the CRM lifecycle (New, Interested, Meeting Scheduled). Authoritative source is `Lead.pipeline_stage_id`. Call Outcome does NOT automatically change Lead Stage.
- **Stage History**: Every explicit stage change persists a `LeadStageHistory` record.

### Calling & Call KPIs
- **ONE REAL CALL = ONE AUTHORITATIVE CALLRECORD**.
- **Call Identity**: Identified securely via `call_record_id` and provider identifier.
- **Call Lifecycle**: Dial → `CallRecord` created (`INITIATED`) → Provider webhook finalizes state → Outcome/Stage saved manually.
- **Duplicate Prevention**: Both webhooks and manual outcome updates update the *existing* `CallRecord` (idempotent operation). No duplicate `CallRecord` is created on retry.
- **Target Actuals**: All valid finalized calls count toward target actuals (including fresh calls, previously contacted calls, follow-up calls, callbacks, and re-attempts).

### Follow-ups
- **FOLLOW-UP != CALL**, **FOLLOW-UP != CONTACTED**, **FOLLOW-UP != INTERESTED**.
- A lead is FOLLOW_UP *only* when an active, persisted `Task` with `task_type=FOLLOW_UP` and `status=PENDING` exists.
- **Creation**: Only explicit scheduling creates an active follow-up.
- **Completion**: Marking complete updates the backend `Task.status` to `COMPLETED`.
- **Rescheduling**: Updates the `due_at` on the *existing* logical active follow-up. Does not create a duplicate.
- **Duplicate Prevention**: One lead = one active follow-up.

### Global Registries & Quotas
- **Global Company / People**: Consists of a Global Master (`GlobalCompany`/`GlobalPerson`) + Tenant Projection (`Company`/`Contact`).
- **Data Protection**: Tenant projections ensure tenant-safe visibility without exposing the global master or other tenants' data (no puller identity exposure).
- **Quota**: Quota deduction is strictly based on *successful* claims (projections), not the initially requested size.

### Database Invariants
- One active target per organization/user/date.
- One active follow-up per lead.
- One company/people projection per tenant/global entity.
- One open shift per user per day.
- Idempotent updates on `CallRecord`.
