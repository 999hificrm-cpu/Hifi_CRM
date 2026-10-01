# JARVIS CRM — System Architecture & Technical Specifications

**Note:** This document represents the current, verified architectural state of the application. For domain-specific business rules and authoritative definitions, refer to [SOURCE OF TRUTH](docs/SOURCE_OF_TRUTH.md).

## Architectural Overview
JARVIS CRM is built as a **Modular Monolith** organized into distinct domain boundaries. It strictly separates data access, business logic, API routing, and frontend rendering.

```
jarvis/
├── backend/
│   ├── app/
│   │   ├── core/         # Config, Database Engine, Security, FastAPI Dependencies
│   │   ├── models/       # SQLAlchemy 2.0 Declarative Models (Database Layer)
│   │   ├── schemas/      # Pydantic v2 Request & Response DTOs
│   │   ├── services/     # Core Domain Services & Business Logic (Service Layer)
│   │   ├── api/v1/       # RESTful API Route Controllers (API Layer)
│   │   └── main.py       # FastAPI Entrypoint & Middleware
│   ├── tests/            # Automated Pytest Suite
│   └── alembic/          # Database Migrations (Schema Evolution)
├── frontend/
│   ├── src/
│   │   ├── components/   # React Components (UI Layer)
│   │   ├── services/     # Typed API Service Client (Frontend API Layer)
│   │   ├── index.css     # Design System & Modern Styling
│   │   └── App.tsx       # Root React Component & Routing
└── docs/                 # Architecture Bibles, Source of Truth, Data Flow
```

## System Layers (Backend to Frontend)

### 1. Database (PostgreSQL/SQLite) & Migrations
- Managed exclusively by **Alembic**.
- Enforces data integrity through foreign keys, `ON DELETE CASCADE` rules, uniqueness constraints (e.g., target tracking, global registry deduplication), and indices for fast lookup.

### 2. Models (SQLAlchemy ORM)
- Located in `backend/app/models/`.
- **Tenant Isolation**: Almost every model requires an `organization_id` column as the strict tenant boundary.
- **Key Models**: `User`, `Lead`, `CallRecord`, `Task` (Follow-up), `Activity`, `Company`/`Contact` (Tenant), `GlobalCompany`/`GlobalPerson` (Global).

### 3. Services (Business Logic Layer)
- Located in `backend/app/services/`.
- This layer executes all critical business rules.
- Contains complex transaction logic (e.g., updating a CallRecord, creating a LeadStageHistory, and scheduling a Follow-up task atomically).
- Enforces entity lifecycle transitions independent of the web framework.

### 4. API Controllers (FastAPI Routes)
- Located in `backend/app/api/v1/`.
- Injects dependencies (`get_db`, `get_current_user`, `get_tenant_id`).
- Handles data validation using Pydantic `schemas`.
- Maps incoming HTTP requests to corresponding Service layer functions.

### 5. Authorization (Platform RBAC)
- Checked inside FastAPI dependencies.
- `get_tenant_id`: Extracts the tenant boundary securely from the JWT, *never* from unverified client payloads.
- **Roles**: `SUPER_ADMIN`, `ORG_ADMIN`, `SALES_MANAGER`, `TELECALLER`.
- **Ownership Verification**: Enforced actively in SQL queries (e.g., assignment visibility strictly limits what telecallers can see or what managers can assign).

### 6. Frontend API Client
- Located in `frontend/src/services/api.ts`.
- Singleton wrapper around `fetch`.
- Automatically attaches the `Authorization: Bearer <JWT>` header.
- Provides strict TypeScript typing matching the backend Pydantic schemas.

### 7. React Components
- Located in `frontend/src/components/`.
- Pure UI layer. Not responsible for enforcing security or authoritative business logic (e.g., filtering out other telecallers' leads is done in the backend API, the frontend simply renders the returned list).
- Connects directly to `api.ts` methods to trigger state mutations.

## Running the Application Locally

### 1. Backend Server
```bash
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
Interactive Swagger API documentation: `http://localhost:8000/api/v1/docs`

### 2. Frontend Development Server
```bash
cd frontend
npm run dev
```
Web application: `http://localhost:5173`

### 3. Run Automated Tests
```bash
python -m pytest backend/tests/ -v
```
