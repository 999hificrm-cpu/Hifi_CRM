# Jarvis CRM — Architecture & DevOps

**Version:** 1.0
**Companion docs:** `01_PRD.md`, `02_SRS.md`, `03_DATABASE_SCHEMA.md`, `05_DEVELOPMENT_BIBLE.md`

---

## 1. Recommended Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + TailwindCSS + shadcn/ui | SSR for dashboards, easy PWA plugin, huge AI-training-data familiarity (fast "vibe coding") |
| PWA | `next-pwa` (Workbox under the hood) | installable, offline shell, Web Push |
| Backend | Node.js + NestJS + TypeScript | opinionated modular structure maps 1:1 to SRS modules; built-in DI, guards (perfect for RBAC/masking policy), Swagger auto-gen |
| ORM | Prisma | type-safe, migration-friendly, great for AI-agent-generated queries |
| DB | PostgreSQL 15+ | relational integrity for CIN/DIN uniqueness, RLS support, full-text search |
| Cache/Queue | Redis 7 + BullMQ | reminders, async Excel processing, radar rule evaluation jobs |
| Object Storage | MinIO (self-hosted, S3-compatible) → swappable to AWS S3/Cloudflare R2 | satisfies "one-click migrate" requirement |
| Search (Phase 1+) | Postgres FTS first; Meilisearch/Elastic if global DB search outgrows Postgres | avoid premature complexity for MVP |
| Auth | JWT (access) + refresh cookie, `@nestjs/passport` | standard, well-understood by AI agents |
| Telephony | Exotel/Knowlarity (India) via adapter interface | click-to-call masking |
| WhatsApp | Meta WhatsApp Cloud API via adapter interface | |
| Email | Postmark/SES via adapter interface | |
| Payments | Razorpay via adapter interface | |
| Monitoring | Sentry (errors) + Pino (structured logs) + optional Grafana/Loki later | debugging/tracing requirement |
| Container/Deploy | Docker + Docker Compose, Nginx reverse proxy, Certbot | Hostinger VPS friendly |
| CI/CD | GitHub Actions → SSH deploy (or GHCR image pull) to VPS | push-to-deploy requirement |

> This stack is a recommendation, not a hard requirement — the SRS/schema are stack-
> agnostic. If the build team prefers Express over NestJS or a different frontend, keep
> the module boundaries and adapter-interface pattern; that's what actually delivers the
> portability/security requirements.

## 2. System Architecture (modular monolith, MVP)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (TLS, reverse proxy)                │
└───────────────┬───────────────────────────────┬──────────────────┘
                 │                               │
        ┌────────▼────────┐             ┌────────▼─────────┐
        │  Next.js (PWA)   │             │  NestJS API (BFF) │
        │  frontend        │◄───REST────►│  modular monolith │
        └──────────────────┘             └───────┬────────────┘
                                                   │
        ┌──────────────────────────────────────────┼──────────────────────────┐
        │                                          │                          │
 ┌──────▼──────┐  ┌───────────────┐  ┌─────────────▼───────┐  ┌───────────────▼──┐
 │ PostgreSQL  │  │ Redis (queue) │  │ MinIO (object store)│  │ Adapter Layer     │
 │ (primary DB)│  │ + BullMQ      │  │                      │  │ Telephony/WA/     │
 └─────────────┘  └───────────────┘  └──────────────────────┘  │ Email/Payments    │
                                                                 └───────────────────┘
```

### 2.1 NestJS Module Map (maps 1:1 to SRS §3)

```
src/
  modules/
    auth/                 # FR-001..004
    platform-data/        # FR-010..016  (global upload, dedupe, batches)
    global-browse/        # FR-020..025  (filter/search/pull)
    tenants/               # tenant + subscription mgmt, FR-090..092
    leads/                 # FR-030..035
    masking/               # FR-040..046  (policy engine — used by every module)
    radar/                 # FR-050..053  (audit events + anomaly rules + alerts)
    activities/            # FR-060..065
    followups/              # FR-063..064
    documents/              # FR-070..073 (talks to storage-service, not SDK directly)
    dashboards/             # FR-080..082
    notifications/          # push/email reminders (uses BullMQ)
    mcp-gateway/            # FR-110..112 — placeholder module, thin wrapper, Phase 2
  common/
    guards/                 # RBAC + masking-aware guards
    interceptors/           # request_id/trace_id injection, audit hook
    adapters/               # TelephonyAdapter, WhatsAppAdapter, EmailAdapter,
                             # StorageAdapter, PaymentAdapter — interfaces + impls
    policy/                 # central permission + masking policy evaluator
```

**Golden rule enforced by this layout**: a controller never talks to Prisma directly for
a masked field, and never talks to a provider SDK directly — always through
`policy/` and `adapters/`. This is what makes FR-041/042/043/044 actually hold under
code review and automated tests, not just in a diagram.

## 3. Data Masking / Proxy-Action Flow (reference sequence)

```
Agent taps "Call" on a Lead
   │
   ▼
Frontend calls POST /leads/:id/actions/call   (never reads raw phone number)
   │
   ▼
API: MaskingGuard checks role→field policy ── if masked ─┐
   │                                                       │
   ▼ (if not masked)                                       ▼ (if masked)
returns raw number to UI (tel: link)              TelephonyAdapter.initiateMaskedCall(
                                                       agentId, leadId)
                                                     → provider bridges both numbers
                                                     → provider webhook confirms call
                                                     → Activities module logs CALL
                                                     → Radar module logs MASKED_CALL event
```

Same shape applies to WhatsApp (`/actions/whatsapp`) and Email (`/actions/email`).

## 4. Storage Abstraction (for the "one-click migrate" requirement)

```ts
interface StorageAdapter {
  put(key: string, stream: Readable, meta: FileMeta): Promise<StorageObjectRef>;
  getSignedUrl(key: string, expirySeconds: number): Promise<string>;
  delete(key: string): Promise<void>;
  list(prefix?: string): AsyncIterable<StorageObjectRef>;
}
```

- MVP implementation: `MinioStorageAdapter` (self-hosted on the same VPS via Docker
  Compose service).
- Migration job (Phase 2): `StorageMigrationService` iterates `documents` table,
  streams each object from the old adapter to the new adapter, verifies
  `checksum_sha256`, updates `storage_provider`/`storage_key`, and only then deletes
  from the old backend — resumable, idempotent, safe to re-run.
- Because business logic only ever calls `StorageAdapter`, swapping MinIO for S3/R2 is
  a config + adapter-implementation change, not an application rewrite.

## 5. Deployment Topology (Hostinger VPS, MVP)

Single VPS running Docker Compose with these services:

```yaml
services:
  nginx:        # TLS termination, reverse proxy to web/api
  web:          # Next.js production build
  api:          # NestJS production build
  postgres:     # primary DB, named volume
  redis:        # queue/cache
  minio:        # object storage, named volume
  worker:       # BullMQ worker process (reminders, batch import processing, radar rule eval)
```

Two environments on the same VPS (recommended for MVP budget) using distinct Compose
project names/ports, or two small VPS instances once budget allows: `staging` and
`production`. `staging` deploys on every merge to `develop`; `production` deploys on
every merge/tag to `main` (manual approval gate recommended).

### 5.1 Example `docker-compose.prod.yml` skeleton

```yaml
version: "3.9"
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certbot/conf:/etc/letsencrypt:ro
    depends_on: [web, api]
  web:
    image: ghcr.io/yourorg/jarvis-web:${IMAGE_TAG}
    env_file: .env.production
    expose: ["3000"]
  api:
    image: ghcr.io/yourorg/jarvis-api:${IMAGE_TAG}
    env_file: .env.production
    expose: ["4000"]
    depends_on: [postgres, redis, minio]
  worker:
    image: ghcr.io/yourorg/jarvis-api:${IMAGE_TAG}
    command: ["node", "dist/worker.js"]
    env_file: .env.production
    depends_on: [postgres, redis]
  postgres:
    image: postgres:15
    volumes: ["pgdata:/var/lib/postgresql/data"]
    env_file: .env.production
  redis:
    image: redis:7-alpine
    volumes: ["redisdata:/data"]
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: ["miniodata:/data"]
    env_file: .env.production
volumes:
  pgdata:
  redisdata:
  miniodata:
```

## 6. CI/CD Pipeline (GitHub Actions → Hostinger VPS)

**On every push to `develop` / `main`:**

1. **lint-and-test** job: install deps, `eslint`, `tsc --noEmit`, `prisma validate`,
   unit tests (Jest), integration tests against an ephemeral Postgres service
   container.
2. **build** job (on pass): build & push Docker images for `web` and `api` to GitHub
   Container Registry (GHCR), tagged with the commit SHA and `latest`/`staging`.
3. **deploy** job (on pass, branch-gated):
   - SSH into the Hostinger VPS (using an `appleboy/ssh-action` or similar, secret-based
     key auth — never password auth).
   - `docker compose pull && docker compose up -d --remove-orphans`.
   - Run `prisma migrate deploy` inside the `api` container before flipping traffic
     (or as a pre-deploy step) — migrations are never run ad hoc on the box by hand.
   - Health-check the `/health` endpoint; auto-rollback (redeploy previous tag) on
     failure.
4. **notify** step: post deploy result (success/fail + commit + tag) to a Slack/Discord
   webhook or email — keeps the founder loop tight during vibe-coding sprints.

```yaml
# .github/workflows/deploy.yml (skeleton)
name: CI/CD
on:
  push:
    branches: [develop, main]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env: { POSTGRES_PASSWORD: test, POSTGRES_DB: jarvis_test }
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npx prisma validate
      - run: npm run test:unit
      - run: npm run test:integration

  build-and-push:
    needs: lint-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - run: |
          docker build -t ghcr.io/${{ github.repository }}/api:${{ github.sha }} -f apps/api/Dockerfile .
          docker build -t ghcr.io/${{ github.repository }}/web:${{ github.sha }} -f apps/web/Dockerfile .
          docker push ghcr.io/${{ github.repository }}/api:${{ github.sha }}
          docker push ghcr.io/${{ github.repository }}/web:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/jarvis-crm
            export IMAGE_TAG=${{ github.sha }}
            docker compose -f docker-compose.prod.yml pull
            docker compose -f docker-compose.prod.yml run --rm api npx prisma migrate deploy
            docker compose -f docker-compose.prod.yml up -d --remove-orphans
            curl -f https://your-domain.com/health || exit 1
```

## 7. Debugging / Tracing / "Vibe Coding" Support

- **`request_id`**: generated at Nginx or API entry, propagated via a header
  (`x-request-id`) through every log line and returned in error responses — lets a
  developer (or AI agent) paste one ID and get the full story.
- **Structured logs (Pino, JSON)** shipped to stdout (captured by `docker logs`), with a
  `docker compose logs -f api --tail=200` one-liner documented for local debugging, and
  an optional Loki/Grafana stack for production log search once traffic justifies it.
- **Sentry** wired in both `api` and `web` for uncaught exceptions with source maps, so
  stack traces resolve to real TypeScript lines even from built artifacts.
- **Centralized error taxonomy**: `common/errors/error-codes.ts` — every thrown domain
  error has a stable code (e.g. `LEAD_NOT_FOUND`, `PULL_QUOTA_EXCEEDED`,
  `MASKED_FIELD_ACCESS_DENIED`) returned in the API error payload — deterministic,
  greppable, and easy for an AI agent to handle in generated frontend code.
- **OpenAPI/Swagger** auto-generated from NestJS decorators, served at `/api/docs` in
  non-production, and exported as `openapi.json` in CI (committed to `docs/api/`) so it
  stays the living contract referenced by `02_SRS.md §FR-110`.
- **Seed + fixtures**: `npm run seed` gives every fresh clone (human or AI agent) a
  working demo tenant, demo global data, and demo users for each role — critical for
  fast, safe iterative "vibe coding" without hand-crafting test data each time.
- **Feature flags** (simple `feature_flags` jsonb on plans/tenants, or a lightweight
  flag table) let half-built Phase 1/2 features ship dark and be toggled on per tenant
  for testing.

## 8. Environments

| Env | Purpose | Data |
|---|---|---|
| local | developer/AI-agent iteration | Dockerized Postgres/Redis/MinIO, seeded fixtures |
| staging | pre-prod verification, `develop` branch auto-deploy | sanitized/synthetic data only |
| production | live tenants, `main` branch, approval-gated deploy | real data, backups enabled |

## 9. Backup & DR

- Nightly `pg_dump` (or WAL-based continuous archiving once volume justifies it) to a
  separate storage target (not the same MinIO instance) — 14-day retention minimum
  (NFR-21).
- MinIO bucket versioning enabled; periodic sync to an off-VPS location (e.g. a cheap
  S3/R2 bucket) as the real disaster-recovery copy, distinct from the "swap provider"
  migration feature.
- Documented restore runbook in `docs/runbooks/RESTORE.md` (Phase 0 deliverable, keep
  it short but real — test it once before go-live).

## 10. Future: MCP Server (Phase 2 placeholder)

`services/mcp-gateway` will expose a curated tool set (search leads, get lead summary,
draft outbound message, update stage, list radar alerts) to an MCP-compatible AI client,
authenticating as a scoped API identity that passes through the *same* `policy/` module
as human users — an AI agent is just another actor subject to masking and RBAC, never a
bypass.

## 13.1 Multi-tenant data model correction — 2026-09-08

The MVP uses shared PostgreSQL tables with `tenant_id` as the customer isolation key. A new customer is provisioned as a tenant and receives a private pipeline/stage configuration. A new user is assigned to that tenant; the system does not create a PostgreSQL schema/database per user.

The lead aggregate is normalized as:

`tenant → pipeline → pipeline_stage → lead`

The lead stores only `pipeline_stage_id` plus primary contact snapshots. `lead_stage_history` and `lead_assignments` preserve change history without overwriting historical events.

Global Registry consumption is a copy boundary:

`platform_company/person → tenant CRM company/person → optional tenant lead`

The source global row remains platform-owned.
