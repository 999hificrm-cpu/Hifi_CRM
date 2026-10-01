# JARVIS CRM: Lead Intelligence Radar & Controlled Outbound

JARVIS CRM is a modern, production-grade, multi-tenant CRM platform built from scratch with strict tenant data isolation, anti-theft contact data masking, an asynchronous spreadsheet ingestion engine, and native AI/MCP foundation.

## Key Features

- **Clean Canonical Domain Hierarchy**: `organizations` → `users` → `companies` / `contacts` → `leads` → `pipelines` / `stages` → `activities` → `tasks`.
- **Zero Schema Pollution**: No artificial `crm_people` tables or duplicate registries.
- **Pipeline Immutability**: Importing 1,000+ leads writes lead records and transition history without touching or duplicating pipeline definitions.
- **Role-Based Telecaller Protection**: Telecallers view masked phone numbers (`+91 98**** 1234`) and emails, triggering calls and WhatsApp messages via platform actions without raw data exposure.
- **Asynchronous Batch Ingestion**: CSV/XLSX file upload with automatic column detection, row-level validation, deduplication, and error isolation.
- **Global Business Intelligence Registry**: Platform-wide catalog of companies and directors with tenant pull quota management.
- **Autonomous Radar**: Opportunity radar highlighting hot leads, overdue follow-ups, and anomaly detection.
- **AI Copilot Readiness**: Lead scoring, executive summarization, and next-best-action recommendations.

## Quick Start

### 1. Database Seed
```bash
python scripts/seed_demo.py
```

### 2. Start Backend API
```bash
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
Swagger UI: `http://localhost:8000/api/v1/docs`

### 3. Start Frontend UI
```bash
cd frontend
npm run dev
```

### 4. Run Automated Tests
```bash
python -m pytest backend/tests/ -v
```

## Demo Credentials
| Role | Email | Password | Scope |
|---|---|---|---|
| Super Admin | `superadmin@jarvis.local` | `JarvisAdmin@2026` | Platform Overview, Tenant Provisioning, Global Registry |
| CRM Admin (Apex) | `admin@apex.com` | `ApexAdmin@2026` | Full CRM Pipeline, Ingestion Wizard, Team Management |
| Telecaller (Apex) | `telecaller@apex.com` | `Telecaller@2026` | Masked Calling Desk, 1-Click Outbound Actions |
