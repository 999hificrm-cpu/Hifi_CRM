# JARVIS CRM — Architecture Bible

## Non-Negotiable Engineering Rules
- **Rule 1**: Zero cross-tenant data access. Every customer query is strictly filtered by `organization_id` derived server-side from the authenticated JWT session.
- **Rule 2**: No business logic inside UI components. Logic lives in backend domain services.
- **Rule 3**: No business logic inside route handlers. Route handlers perform input validation, call domain services, and return typed schemas.
- **Rule 4**: No direct database access from AI agents. AI operates strictly via domain service layers and RBAC authorization boundaries.
- **Rule 5**: No hard-coded pipelines or stages. Pipelines are configurable per organization.
- **Rule 6**: No hard-coded roles or permissions. Roles map to granular permission matrices.
- **Rule 7**: No permanent local file paths in production. All file uploads use the `StorageProvider` abstraction.
- **Rule 8**: No secrets in source code or Git. All secrets are managed via `.env`.
- **Rule 9**: Every important mutation is auditable (`audit_logs` and `radar_events`).
- **Rule 10**: Pipeline stages are immutable during batch imports. Ingesting leads appends `lead_stage_history` without touching pipeline definitions.
