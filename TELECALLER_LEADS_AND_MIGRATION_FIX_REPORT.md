# [OBSOLETE] - THIS DOCUMENT IS NO LONGER ACCURATE

**Please refer to docs/SOURCE_OF_TRUTH.md and ARCHITECTURE.md for current accurate information.**

# Telecaller Leads and Migration Fix Report

## Scope completed

- Added a secure **Download VCF** action to the Telecaller Desk lead view.
- Made **All**, **B2B**, **B2C**, and **Other** lead filters server-authoritative.
- Preserved and returned lead `segment` and `lead_type` values through the API.
- Centralized lead-segment classification for manual creation and spreadsheet imports.
- Repaired the invariant migration so existing duplicate active follow-ups and
  duplicate daily target rows do not prevent deployment.

## Qualification rules

| Evidence | Segment |
| --- | --- |
| Free/personal email domain | B2C |
| Company name and corporate email domain | B2B |
| Missing or inconclusive evidence | OTHER |

An explicit B2B, B2C, or OTHER value is accepted after normalization; any other
value is rejected with HTTP 422. Legacy records without a segment are included
in the Other filter so that no lead disappears from operational queues.

## Security and tenant controls

VCF download uses the authenticated session and existing lead-access checks.
Telecallers can download cards only for leads they own or may access through an
active absence delegation. Downloads are tenant-scoped, produce an audit Radar
event, disable caching, and escape vCard content. Phone and email follow the
existing data-masking policy, so a VCF cannot bypass masking.

## Migration behavior

Before creating the one-active-follow-up index, older duplicate pending
follow-up tasks are retained as history and changed to `CANCELLED`; the newest
task remains active. Before creating the one-daily-target index, duplicate
configuration rows are reconciled to the newest configuration row.

## Verification performed

- Targeted Telecaller filters and VCF regression tests: passed.
- Security regression tests: passed.
- SQLite migration from an existing duplicate-follow-up state to `head`: passed.
- Backend suite excluding two environment-bound PostgreSQL integration tests:
  **41 passed**.
- Frontend production build: passed.

The two excluded integration tests directly require a locally reachable,
seeded PostgreSQL instance (`localhost:5432`); they are not runnable in this
archive-only environment. This report covers the requested Telecaller lead,
VCF, and migration paths, not a claim that every phase of the master prompt has
been implemented.

