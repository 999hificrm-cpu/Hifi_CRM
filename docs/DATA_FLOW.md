# JARVIS CRM - DATA FLOW

## CALL FLOW

1. **Telecaller** clicks "Call" on the Frontend.
2. **Frontend** initiates Dial API request (`/telephony/dial`).
3. **Backend** creates a `CallRecord` in the database with `status = INITIATED`.
4. **Provider/Native Lifecycle** handles the actual telephony call.
5. **Webhook/Callback** from the provider hits the backend, updating the *existing* `CallRecord` to its finalized state (e.g., `CONNECTED`, `NO_ANSWER`). This is an idempotent operation based on `call_record_id` or provider ID. No duplicate records are created.
6. **Telecaller** fills out the outcome form (Outcome, Stage, Follow-up, Notes) and saves.
7. **Backend** processes the outcome transactionally:
    - Updates the *same* `CallRecord` with the outcome.
    - Creates an `Activity` log.
    - Updates `Lead` stage (if changed explicitly) and inserts `LeadStageHistory`.
    - Upserts/Creates a `Task` (Follow-up) if scheduled.
8. **Dashboard Metrics** are queried directly from the `CallRecord` table (e.g., Daily Calls, Connected Calls).

## FOLLOW-UP FLOW

1. **Call Outcome** form includes explicit scheduling of a follow-up date and time.
2. **Follow-up Service** (Backend) receives the request during the outcome save.
3. **Database** creates or updates a `Task` with `task_type = FOLLOW_UP`, `status = PENDING`, and the specified `due_at`.
4. **Worklist / My Follow-ups** queries the `Task` table for pending follow-ups assigned to the current user.
5. **Complete**: Telecaller clicks "Mark Complete". API updates `Task.status = COMPLETED`. It is removed from the active worklist queries.
6. **Reschedule**: Telecaller selects a new date. API updates the *existing* `Task.due_at` and records the change in `reschedule_history`.

## ASSIGNMENT FLOW

1. **ORG_ADMIN** opens Team Management and selects a target Telecaller.
2. **Assignment API** (`GET /leads/available-for-assignment`) fetches the eligible dataset. This includes ONLY unassigned leads and leads *already* assigned to the selected telecaller. Other telecallers' leads are strictly excluded by the SQL query.
3. **Frontend** renders the selectable list, marking already-owned leads with an "Already Assigned" badge.
4. **ORG_ADMIN** selects a batch of leads (manual selection or Quick Select) and submits.
5. **Backend Assignment Transaction**:
    - Verifies the telecaller is active and clocked in (Shift).
    - Checks each lead's `owner_id` (only processing unassigned leads to avoid silent overwrites).
    - Updates `Lead.owner_id = telecaller.id`.
    - Inserts a record into `LeadAssignment` for history tracking.
    - Creates an `Activity` indicating assignment.

## GLOBAL REGISTRY FLOW (COMPANY)

1. **Upload/Admin** inserts a master company record into `GlobalCompany`.
2. **Tenant User** searches for a company name. The API returns results from `GlobalCompany`.
3. **Tenant User** selects and imports a company.
4. **Backend**:
    - Locks the record or uses constraints to prevent concurrency issues.
    - Creates a localized `Company` projection tied to the `tenant_id`.
    - Marks the global record as pulled by the tenant.
    - Deducts exactly ONE from the tenant's global company quota (only on successful insert).
    - The puller's identity is NOT exposed globally.

## GLOBAL REGISTRY FLOW (PEOPLE)

1. **Upload/Admin** inserts a master person record into `GlobalPerson`.
2. **Tenant User** searches the registry.
3. **Tenant User** imports a person.
4. **Backend**:
    - Employs locks/constraints to ensure no race conditions.
    - Creates a localized `Contact` projection (and linked `Lead` if required) tied to the `tenant_id`.
    - Logs the pull action safely.
    - Deducts from the tenant's global people quota upon successful creation.
