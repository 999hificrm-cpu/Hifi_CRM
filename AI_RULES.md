# JARVIS CRM — AI Coding Agent Master Rules

Every AI coding agent operating on this repository must adhere to the following rules:

1. **Never Bypass Tenant Isolation**: All tenant-scoped operations must derive `organization_id` from the authenticated session context.
2. **Never Put Business Logic in UI or Routers**: Always place core operations into domain services under `backend/app/services/`.
3. **Never Re-introduce `crm_people` or Duplicate Registries**: Maintain `companies`, `contacts`, and `leads` as the canonical domain models.
4. **Never Modify Pipelines During Ingestion**: Ingesting leads binds them to existing pipeline stages and records stage history.
5. **Always Enforce Data Masking Server-Side**: The API must never leak unmasked contact numbers or emails to unauthorized roles.
6. **Always Run Tests**: Every change must pass `python -m pytest backend/tests/ -v` and `npm run build` in `frontend/`.
