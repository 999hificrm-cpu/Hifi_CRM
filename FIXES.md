# [OBSOLETE] - THIS DOCUMENT IS NO LONGER ACCURATE

**Please refer to docs/SOURCE_OF_TRUTH.md and ARCHITECTURE.md for current accurate information.**


**JARVIS CRM — STRUCTURED PRODUCTION AUDIT REPORT**
*(Pre-fix inspection complete. No production code modified yet. Findings are based on full repository inspection of models, services, APIs, migrations, frontend, Docker, tests, and data-flow tracing.)*

### Overall Mental Model (Summary)

- **Architecture**: Modular monolith (FastAPI + SQLAlchemy + Celery + Redis + React/TS). Shared database with `organization_id` tenant filters + some soft-delete + RBAC via `platform_role` / `tenant_role` + JWT with token version + revocation.
- **Core hierarchy**: Organization → Users → Companies/Contacts → Leads (with pipeline stages, owner_id, product_service_id, snapshots) → Activities / Tasks → Daily queue / Targets / Shifts.
- **Key engines**: Global Registry (pull into tenant CRM), Import engine (CSV/XLSX), Telecaller Desk (queue + targets + shifts + vCard), Follow-up via Task model, Products/Services (org-scoped).
- **Data flow**: Auth → tenant context from JWT/user → service layer (partial) → API → frontend components (heavy logic in App.tsx + TelecallerDesk etc.).
- **Sources of truth problems**: Multiple overlapping models for sessions/targets/follow-ups; ad-hoc schema patches in `main.py`; JSON fields used alongside dedicated tables; frontend and backend sometimes calculate the same metrics differently.

---

### Findings by Severity

#### CRITICAL

1. **Dual / inconsistent Telecaller Target sources of truth**

   - **Module/files**: `app/models/user.py` (`telecaller_targets` JSON), `app/models/telecaller_target.py` (dedicated table with different defaults 100/40/2), `app/api/v1/telecaller.py` (Create schema hardcodes 80/30/2; `/targets/today` reads **only** `user.telecaller_targets` JSON and ignores the table + `achieved_*` columns).
   - **Root cause**: Two parallel systems were introduced; the read path never queries `TelecallerTarget`. Defaults differ across model / schema / fallback.
   - **Why problem / Business impact**: ORG_ADMIN configures one place; Telecaller Desk reads another (or zeros). Progress % can be wrong or show hardcoded values. Zero-target handling and date boundaries are fragile.
   - **Security**: Low (no direct leakage).
   - **Recommended fix**: Make `TelecallerTarget` the single authoritative table (org + user + business date). Migrate any JSON data, remove JSON column usage for targets, enforce org-level defaults only when explicitly configured, compute actuals strictly from qualifying `Activity` rows of type CALL for that user/date (already partially done). Add unique constraint (org, user, date).
   - **Status**: Confirmed via code paths. Not fixed yet.
2. **Global Registry pull lacks atomicity, correct quota accounting, and concurrency safety**

   - **Module/files**: `app/services/global_service.py` (`pull_global_companies_to_crm`), models `global_registry.py` / `organization.py` (Subscription.pull_quota_*), frontend GlobalRegistryView.
   - **Root cause**: Loop over IDs with ordinary queries; quota deducted by *requested* count (`needed`) even for already-pulled / missing / failed records; no `SELECT ... FOR UPDATE`, no unique constraint on tenant-side claim, no transaction isolation against concurrent orgs. Global master is correctly preserved, but puller identity fields exist on global model.
   - **Why problem / Business impact**: Race → double-pull or over-quota; quota can be exhausted without successful claims; lineage/history incomplete.
   - **Security impact**: Medium (possible quota abuse; risk of leaking puller org if UI/API ever surfaces the global pulled_by_* fields).
   - **Recommended fix**: Wrap in transaction + row locks on global rows + Subscription; deduct quota **only** for successfully created tenant records; make claim idempotent per (org, global_id); never expose puller identity in ordinary GlobalCompanyOut responses; preserve all historical global records.
   - **Status**: Confirmed. Not fixed yet.
3. **Ad-hoc schema evolution outside Alembic**

   - **Module/files**: `app/main.py` (large block of `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` on startup for soft-delete, audit columns, etc.), Alembic versions under `backend/alembic/versions/`.
   - **Root cause**: Startup “schema check” patches columns instead of proper migrations. Models and migrations drift.
   - **Why problem / Business impact**: Clean DB vs existing DB behave differently; production migrations can fail or silently leave inconsistent state; hard to reason about indexes/FKs/nullability.
   - **Recommended fix**: Move every column into proper Alembic revisions; remove or severely restrict startup ALTER logic; ensure `alembic upgrade head` is the only path.
   - **Status**: Confirmed. Not fixed yet.

#### HIGH

4. **Follow-up / Daily queue / Task duplication risk**

   - **Module/files**: `app/models/task.py` (Task + DailyTask + DailyCallPlan), `app/api/v1/telecaller.py` (queue construction joins Tasks + new leads), `app/tasks/daily_tasks.py`, `app/services/task_service.py` / `followup_service.py` (thin).
   - **Root cause**: Queue is built on-the-fly in the API; multiple generators (Next-Best-Action, daily plan, policy, frontend) can create Tasks without strong idempotency key on (lead_id, type, due window, assignee). Historical completed tasks are kept, but active follow-up uniqueness is not enforced at DB level.
   - **Why problem**: Same lead can appear as both fresh and follow-up; counters diverge; telecaller sees duplicates.
   - **Recommended fix**: Single authoritative active follow-up per lead (unique partial index or service-level lock); reschedule updates existing Task; daily queue is a pure read of (due Tasks + unowned/fresh assigned leads) with de-duplication by lead_id; actual follow-up counts come only from active Task records.
   - **Status**: Confirmed by structure; full concurrency tests still needed.
5. **Shift / Attendance state is fragile**

   - **Module/files**: `app/models/session.py` (AttendanceSession, BreakSession, TelecallerSession), `app/models/availability.py`, `app/api/v1/shifts.py`.
   - **Root cause**: `date` column typed as DateTime but compared to Python `date`; multiple overlapping session tables; no strong uniqueness on (user, date, open session); frontend can re-init state independently.
   - **Why problem**: Reload can show wrong ACTIVE state; end-shift may leave dangling sessions; timer accuracy depends on client.
   - **Recommended fix**: Server is single source of truth for shift status; enforce at most one open AttendanceSession per user; normalize date to pure Date; close breaks on shift end; return authoritative status on every relevant endpoint.
   - **Status**: Confirmed.
6. **Lead ownership / assignment not fully hardened against IDOR / reassignment races**

   - **Module/files**: Lead model (`owner_id`), assignment endpoints in leads/telecaller APIs, serialize_lead + masking.
   - **Root cause**: Some list endpoints filter by owner, but reassignment paths need explicit “must be currently unowned or same org + role check + history write”. Backend must reject cross-telecaller access even if client tampers with IDs.
   - **Why problem**: Telecaller A can potentially reach Telecaller B’s leads via crafted requests; assignment history can be incomplete.
   - **Recommended fix**: Every lead read/write that is telecaller-scoped must enforce `owner_id == current_user.id` (or manager override); bulk assignment must be transactional and write history; never trust client-supplied owner_id for authorization.
   - **Status**: Partially present; needs exhaustive endpoint audit.
7. **Import Product/Service + tenant isolation + status consistency**

   - **Module/files**: Large `import_service.py`, product_service model/API, lead creation paths.
   - **Root cause**: Product/Service must be org-scoped; invalid mapping should be row-level error, not silent null or cross-tenant FK. Status values after import must match what queue/pipeline/assignment expect.
   - **Status**: Model and UI exist and are routed; full validation path needs verification against large-file / partial-failure behavior.

#### MEDIUM

8. vCard endpoint correctly checks ownership but intentionally returns unmasked PII (by design for “Add to Contacts”). Confirm business rule (active shift required or just assignment) and that logs never store the raw vCard.
9. Multiple session models (TelecallerSession vs AttendanceSession) create confusion and possible double-counting of productivity.
10. Hardcoded defaults (80/30/2, 100/40, talk_time=120) appear in several places.
11. Frontend Navbar is partially configuration-driven but still has hard-coded tab maps; overflow/More handling needs verification for future modules.
12. Alembic history contains both additive and some potentially destructive patterns; startup code can mask missing migrations.
13. Analytics / dashboard counters are computed in multiple places (API vs frontend vs radar service); risk of divergence.
14. Celery daily tasks and import tasks need explicit idempotency keys and transaction boundaries.

#### LOW / Technical Debt

- Large single App.tsx + many large components.
- Some services are thin wrappers; business logic lives in API routes.
- SQLite test DBs committed; production path assumes Postgres.
- Mock telephony/WhatsApp providers.
- PDF “SUPER_ADMIN_MASTER_PROBLEM” list documents many additional Super-Admin billing/subscription state-machine gaps (out of immediate Telecaller/Lead scope but real).

---

### Cross-Cutting Observations

- **Tenant isolation**: Generally present via `organization_id` filters + `get_tenant_id`, but must be verified on every ID-accepting endpoint (especially global, vCard, assignment, reports).
- **Masking**: Present for telecaller views; vCard intentionally bypasses for assigned leads.
- **Pipeline immutability**: Stage history is written; good.
- **Testing**: Existing suite covers auth, some tenant isolation, import, assignment, Super-Admin phase 1, but is incomplete for concurrency, targets, follow-up uniqueness, and global claim races.
- **Docker / env**: docker-compose present; secrets in example are weak; startup schema patching is a production risk.

---

### Next Steps (as required)

1. Continue exhaustive tracing of remaining endpoints (assignment, follow-up creation, import column mapping, products CRUD, all telecaller list filters, Celery jobs).
2. Produce detailed per-module flow diagrams in the final report.
3. Implement root-cause fixes in priority order (Targets single source of truth → Global claim atomicity → Schema/migration hygiene → Follow-up uniqueness → Shift authority → Assignment hardening → Tests).
4. Add regression tests for every Critical/High finding.
5. Run full backend test suite, frontend type-check/build, and report exact results.
6. Deliver **FINAL JARVIS CRM AUDIT & FIX REPORT** with FIXED / PARTIALLY FIXED / NOT FIXED status for every original finding.

