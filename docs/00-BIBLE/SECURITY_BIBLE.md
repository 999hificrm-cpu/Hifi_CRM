# JARVIS CRM — Security Bible

## 1. Authentication & Session Security
- Passwords hashed using PBKDF2-SHA256 with cryptographically generated salts.
- JWT Access Tokens with verified expiration and cryptographic signature.
- Strict session revocation on password change or user deactivation.

## 2. Multi-Tenant Isolation
- The `get_tenant_id` dependency enforces that tenant users can only access their authenticated `organization_id`.
- Super Admin operations require explicit tenant headers or platform scope.
- Cross-tenant database reads and updates return HTTP 404/403.

## 3. Data Masking & Anti-Theft
- Field-level masking applied server-side during serialization.
- Telecaller role cannot view raw phone or email values.
- Contact export is strictly forbidden for masked roles.
- Temporary exceptions expire automatically and are logged in `audit_logs`.
