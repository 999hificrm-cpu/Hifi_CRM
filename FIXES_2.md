# [OBSOLETE] - THIS DOCUMENT IS NO LONGER ACCURATE

**Please refer to docs/SOURCE_OF_TRUTH.md and ARCHITECTURE.md for current accurate information.**


**Deep analysis completed.** Below is the refined, verified picture of the critical subsystems after tracing database models → services → API endpoints → frontend calls → persistence, plus Celery jobs and concurrency characteristics.

---

### 1. Target Engine (Confirmed Dual Source of Truth — Critical)

| Path                                          | Writes                                                     | Reads                                                                            | Defaults                                  |
| --------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------- | ----------------------------------------- |
| **ORG_ADMIN Team UI**                   | `User.telecaller_targets` JSON via `PATCH /users/{id}` | —                                                                               | Client sends whatever admin types         |
| **Telecaller Desk**                     | —                                                         | `/telecaller/targets/today` → **only** `user.telecaller_targets` JSON | Fallback`0` (or talk_time=120)          |
| **Celery `initialize_daily_targets`** | Inserts rows into`telecaller_targets` **table**    | —                                                                               | Hardcoded**80 / 30 / 120 / 10 / 2** |
| **EOD report job**                      | —                                                         | Reads the**table**                                                         | Falls back to 80 if missing               |
| **Model defaults**                      | `TelecallerTarget` table                                 | —                                                                               | 100 / 40 / 120 / 10 / 2                   |
| **Pydantic Create schema**              | —                                                         | —                                                                               | 80 / 30 / 2                               |

**Root cause**: Two independent systems were introduced. The table is written by the nightly job and partially used by EOD, but the live Desk and the admin configuration UI both use the JSON column on `User`. The table’s `achieved_*` columns are never updated by the live activity path.

**Business impact**: An admin can set targets that appear correctly in Team Management and on the Desk, while background jobs and any future code that queries the table see different numbers. Hardcoded 80/30/2 appear in three places.

**Fix direction** (will implement): Make `TelecallerTarget` (org + user + business_date) the single authoritative store. Migrate existing JSON values into the table on first read/write, remove JSON usage for targets, add unique constraint, stop Celery from overwriting admin-configured values, and compute actuals only from qualifying `Activity` rows of type `CALL` for that user and org-local date.

---

### 2. Follow-up / Task Engine (Confirmed Duplication Risk — High)

**Creation paths**:

1. Policy engine (`execute_followup_policy`) triggered inside `create_activity` on every `CALL`.
   - Cancels all existing `PENDING` FOLLOW_UP tasks for the lead, then inserts a new one.
2. Frontend `TelecallerDesk.handleRecordOutcome`:
   - Always calls `logActivity(CALL)`.
   - **Additionally** calls `createTask(FOLLOW_UP)` if the preset is not `"none"`.
3. `create_task` service itself also cancels previous PENDING FOLLOW_UP for the same lead before insert.

**Observed behaviour**:

- Under normal single-user use the cancel-before-insert pattern keeps only one active task, but the due-date and title come from whichever path runs last (frontend usually wins).
- No DB-level unique constraint / partial unique index on `(lead_id) WHERE status='PENDING' AND task_type='FOLLOW_UP'`.
- Concurrent requests (or Celery + UI) can still produce a brief window of two PENDING rows.
- Historical COMPLETED/CANCELLED tasks are correctly retained.
- Daily queue (`/telecaller/queue/today`) correctly de-duplicates by `lead_id` when building the response, but the underlying Task table can still contain orphans.

**Root cause**: Business rule “one active follow-up per lead” is implemented only in application code in two places, not enforced by the database, and the frontend still performs its own creation instead of letting the policy engine be the sole authority.

---

### 3. Global Registry Claim (Confirmed Race & Quota Issues — Critical)

- Global master records are **never deleted** on pull (correct).
- Pull status for the current org is derived from existence of a tenant `Company.source_global_company_id` (correct isolation).
- `GlobalCompanyOut` does **not** expose `pulled_by_org_id` / puller identity (good).
- **Missing**:
  - No `SELECT … FOR UPDATE` (or equivalent advisory lock) on the global rows or the Subscription row.
  - Quota is decremented by the *requested* count, not by the number of successfully created tenant records.
  - No unique constraint preventing the same global company from being pulled twice into the same org under race conditions.
  - No atomic “claim + create tenant company + create lead + deduct quota” transaction boundary that survives concurrent ORG_ADMIN pulls from different organisations.

---

### 4. Shift / Attendance (Confirmed Fragility — High)

- Frontend correctly initialises as `OFFLINE` and loads authoritative status from `/shift/status`.
- Backend uses `AttendanceSession.date` typed as `DateTime` but compares it to a pure `date` object → timezone / type mismatch risk on some DBs.
- Multiple overlapping models (`AttendanceSession`, `BreakSession`, `TelecallerSession`, `AvailabilityStatus`).
- Assignment logic (both single and bulk) **requires** the target telecaller to have an open shift; this is a deliberate business rule but currently brittle because of the date comparison.
- No DB uniqueness guaranteeing at most one open session per user.

---

### 5. Lead Assignment & Ownership (Mostly Correct, Needs Hardening)

- List endpoints for telecallers correctly filter `owner_id == current_user.id` (+ active delegations).
- `assign_lead` and batch paths write `LeadAssignment` history and an Activity.
- Re-assignment of an already-owned lead is allowed for managers (intentional) but the “must be clocked in” guard can be bypassed if the date comparison fails.
- No explicit “do not silently overwrite another telecaller’s ownership without history” beyond the existing history write.

---

### 6. Import + Products/Services (Mostly Solid)

- Product/Service lookup is org-scoped (`ProductService.organization_id == …` + `ilike` on name).
- Missing product produces a clear **row-level** error (good).
- Default product on the import job is supported.
- Frontend Products & Services page is present in the Navbar for `ORG_ADMIN` and routed correctly.

---

### 7. Additional Verified Issues

| Issue                                                                                                       | Severity        | Evidence                                 |
| ----------------------------------------------------------------------------------------------------------- | --------------- | ---------------------------------------- |
| Celery`initialize_daily_targets` uses `User.is_active` which does **not** exist (only `status`) | High            | Will raise`AttributeError` every night |
| Startup`ALTER TABLE` patches in `main.py`                                                               | High            | Diverges from Alembic                    |
| No unique constraint on`(organization_id, user_id, target_date)` for targets                              | High            | Allows duplicate daily rows              |
| Frontend can still create a second Task even though policy already ran                                      | Medium          | Race window                              |
| AttendanceSession.date type mismatch                                                                        | Medium          | Comparison bugs                          |
| Hardcoded 80/30/2 appear in three independent places                                                        | Medium          | Maintenance hazard                       |
| vCard correctly checks ownership and intentionally returns unmasked PII                                     | Low (by design) | Acceptable for assigned telecaller       |

---

### Architecture Assessment (Current State)

- **Single source of truth** is broken for targets and partially for active follow-ups.
- Tenant isolation and basic RBAC are present and generally respected.
- Global master data is correctly preserved.
- Many business rules live in API route handlers rather than services, making them harder to test and reuse.
- Celery jobs and the live request path are not fully aligned.

---

**Next action (as required by the original brief)**I will now implement the root-cause fixes in priority order, starting with:

1. Unify the Target engine onto the `TelecallerTarget` table (migrate JSON, fix Celery, add unique constraint, update read path).
2. Make follow-up creation idempotent at the service + DB level and stop the frontend from creating a second Task.
3. Harden Global Registry claim with proper locking / quota accounting.
4. Fix shift date handling and User status filter in Celery.
5. Add/update automated tests for each of the above.
6. Re-run the test suite and produce the **FINAL JARVIS CRM AUDIT & FIX REPORT**.

Proceeding to code changes now.

