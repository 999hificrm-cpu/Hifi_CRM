# Jarvis CRM — Product Requirements Document (PRD)

**Version:** 1.0
**Status:** Draft for build (v0 / MVP scope marked explicitly)
**Owner:** Founding team
**Companion docs:** `02_SRS.md`, `03_DATABASE_SCHEMA.md`, `04_ARCHITECTURE_AND_DEVOPS.md`, `05_DEVELOPMENT_BIBLE.md`

---

## 1. Vision

Jarvis CRM is not a system-of-record CRM. It is a **Lead Intelligence Radar** — a CRM
wrapped around a licensed, continuously-growing national database of companies and the
people who run them, with an internal AI-based tracking layer that watches how *your own
team* touches that data.

Two products in one:

1. **Global Data Layer** — a super-admin-curated, standardized registry of Companies and
   People (directors/decision-makers), sold as a subscription. Paid tenants browse/filter
   and "pull" records into their own account instead of buying scraped lists from vendors.
2. **Tenant CRM Layer** — a normal-looking CRM (leads, pipeline, calls, WhatsApp, email,
   follow-ups) sitting on top of that data, but with **data-loss-prevention baked into the
   core**: telecallers work leads without ever seeing the raw phone number/email unless
   the admin explicitly allows it, and every read/export/call is logged and scored for
   anomalous (theft-like) behavior.

## 2. Problem Statement

| # | Problem | Who feels it | Jarvis CRM answer |
|---|---|---|---|
| 1 | Company data arrives from many sources (own leads, purchased lists, scraped sheets) in inconsistent formats | Marketing/Ops | Global Data Layer with a fixed Company + People schema and an import pipeline that normalizes any Excel/CSV into it |
| 2 | Sales/telecalling staff can copy, export, or screenshot paid-for contact data and walk off with it | Founders/Sales heads | Field-level data masking, click-to-call/WhatsApp/email without exposing raw contact info, export controls, watermarking, audit trail |
| 3 | No visibility into who accessed what data, when, or what happened to a lead through the pipeline | Ops/Compliance | Lead Intelligence Radar: full activity + access audit log, anomaly alerts, per-stage pipeline history |
| 4 | Lead generation means paying repeatedly for scraped/purchased data | Growth/Marketing | Subscription-based shared Global Data Layer; pull-once, reuse-forever (within license terms) inside the tenant's own CRM |

## 3. Users / Personas

1. **Super Admin (Jarvis-side)** — owns the Global Data Layer, manages tenants & plans,
   uploads/curates master Company & People data, monitors platform health.
2. **Data Ops Sub-user (Jarvis-side)** — uploads Excel/CSV batches into the global DB
   under super admin's supervision; limited to import/curation screens.
3. **Tenant Admin (paying customer)** — owns a company account/subscription, sets up
   pipeline stages, invites sub-users, browses & pulls global data, assigns leads,
   configures masking/permission rules, views dashboards.
4. **Tenant Sub-user / Telecaller / Sales rep** — works assigned leads only: calls,
   WhatsApp, emails, updates stage, sets follow-ups — never sees raw contact fields
   unless permitted.
5. **(Future) AI Agent** — connects via MCP to summarize a lead, draft a WhatsApp/email
   message, score/prioritize leads, flag anomalies — read/write via the same permissioned
   API a human sub-user would use.

## 4. Core Differentiators ("why not just use Zoho/HubSpot + a scraper")

- **Two-tier data model**: platform-owned Global Registry vs tenant-owned CRM data, with
  a formal "pull" action that is licensed, logged, and reversible (revoke on plan
  downgrade/cancellation).
- **Contact-data masking by design**, not bolted on: telecallers dial/WhatsApp/email
  through the platform (masked number / proxy send) instead of being handed the raw
  number/address.
- **Lead Intelligence Radar**: an internal tracking system scoring data-access behavior
  (bulk views, rapid exports, off-hours access, repeated failed masked-call attempts,
  etc.) and alerting the tenant admin.
- **MCP-ready from day one**: every capability exposed as a clean, permissioned API so an
  AI agent can be plugged in later without re-architecting.
- **Portable file storage**: documents/images live in an abstracted storage service
  (S3-compatible) that can be pointed at a new provider/server via one config change / API
  call — no re-upload migration project.

## 5. Scope by Phase

### Phase 0 — MVP (build first, ~10–12 weeks with AI-assisted/"vibe" coding)
- Super admin: global Company + People upload (Excel/CSV), dedupe by CIN/DIN, mapping
  table, upload batch history.
- Tenant admin: signup/org setup, subscription plan selection (manual/Razorpay stub OK),
  sub-user invite with roles.
- Global Data browsing + filters + "Pull to my account" (with pull quota per plan).
- Tenant CRM: Leads (from pull or manual/import), contacts under a lead, custom pipeline
  stages, lead assignment to sub-users.
- Activities: call log (manual + click-to-call), WhatsApp click-to-chat, email send,
  follow-up with reminder.
- **Data masking v1**: mask phone/email for "Telecaller" role by default; click-to-call
  via masked-number proxy (or `tel:` fallback if telephony provider not yet wired);
  export/copy disabled for masked roles.
- Basic audit log (who viewed/exported/called what, when).
- Admin dashboard: leads by stage, activity volume, conversion funnel, upload stats.
- PWA shell (installable, offline shell, click-to-call/WhatsApp/email from any device).
- File/document upload against a lead (stored via abstracted storage service).
- CI/CD to Hostinger VPS via GitHub Actions; staging + production.

### Phase 1 — Intelligence Radar
- Configurable masking rules per role/field/plan.
- Anomaly detection rules engine (thresholds → alerts → optional auto-lock of a user).
- Data watermarking on any export a role *is* allowed to make.
- Advanced dashboards: rep leaderboards, stage-velocity, source ROI.
- WhatsApp Business API (template messages), transactional email via provider (not just
  mailto).
- Bulk import mapping UI (map arbitrary Excel columns → schema fields) for tenant's own
  data.

### Phase 2 — AI / MCP
- MCP server exposing: lead search, lead summary, draft-message, stage update, radar
  alerts — permission-scoped per calling identity.
- AI lead scoring / next-best-action suggestion.
- AI-assisted data cleaning on global upload (entity resolution, address normalization).
- One-click storage migration tool (point storage service at new S3-compatible endpoint,
  background copy job, cutover).

## 6. Key User Stories (MVP)

- As a **Super Admin**, I upload an Excel of companies and one of directors; the system
  matches directors to companies by CIN and shows me an upload report (success/fail rows,
  reasons).
- As a **Super Admin**, I see when the global DB was last updated and by whom, per
  record and per batch.
- As a **Tenant Admin**, I filter the global database by city/industry/company-type and
  pull 500 companies into my account against my plan's monthly quota.
- As a **Tenant Admin**, I create pipeline stages (New → Contacted → Qualified →
  Proposal → Won/Lost) and assign pulled leads to two telecallers.
- As a **Telecaller**, I open a lead, tap "Call" and the call connects without me ever
  seeing the actual phone number; the call is logged automatically with duration.
- As a **Telecaller**, I set a follow-up for tomorrow 11am; I get a reminder and can
  reschedule from the reminder itself.
- As a **Tenant Admin**, I get an alert when a sub-user views 200 lead contact records
  in 10 minutes (possible scraping-for-exit behavior).
- As a **Tenant Admin**, I open the dashboard and see conversion % by stage, by rep, by
  data source (global-pull vs manual vs import).

## 7. Non-Goals (explicitly out of MVP)

- Full marketing-automation (drip campaigns, landing pages) — only outbound
  call/WhatsApp/email logging.
- Native mobile apps (PWA covers the "one-click call/WhatsApp/email on mobile" need).
- Multi-currency/international billing — start India-first (CIN/DIN registry is an
  India-specific construct; schema is generalized so other countries' registry IDs can be
  added later).

## 8. Monetization Sketch

- **Tenant plans** (Starter / Growth / Enterprise): differ by seat count, monthly global
  data pull quota, masking-rule customization, and dashboard depth.
- **Global data pulls** metered per plan; overage add-on packs.
- Optional **telephony/WhatsApp usage** pass-through billing (provider costs).

## 9. Success Metrics

- Time-to-first-pulled-lead for a new tenant < 10 minutes.
- % of contact-data exposure incidents (raw number/email seen by unauthorized role) = 0
  in masked-role flows.
- Global DB dedupe accuracy (no duplicate CIN records) ≥ 99%.
- Median call-log capture rate (click-to-call sessions that produce a logged activity)
  ≥ 95%.

## 10. Assumptions & Constraints

- Legal basis for holding/reselling company & director data (CIN/DIN sourced from public
  MCA-type filings) is handled outside this document — product assumes data is
  lawfully sourced/licensed.
- India is the first market; schema and telephony integration choices favor Indian
  providers (Exotel/Knowlarity/Twilio-India, Meta WhatsApp Cloud API) but are abstracted
  behind interfaces so other regions can be added.
- Deployment target is a single Hostinger VPS for MVP (vertical scaling), with the
  architecture kept container-based so it can move to multi-node later without a rewrite.

## 15. Architecture amendment — 2026-09-08

The CRM data model has been normalized after the Phase 3 review.

- A lead is an opportunity with direct primary contact fields (`contact_name`, `contact_email`, `contact_phone`).
- A lead has one current `pipeline_stage_id`; the pipeline is derived through the stage. Pipeline definitions are never copied per lead.
- Stage and assignment history are append-only event records.
- Customer organizations are represented by tenant contexts. New users are assigned to their organization's tenant; a separate physical database/schema is not created per user in the MVP.
- Tenant users can consume Global Registry data through controlled copy/pull workflows.
- Global Registry records remain platform-owned and immutable from tenant CRM screens.
