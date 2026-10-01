# JARVIS CRM — Master Architecture & System Flow Diagrams

This document contains visual diagrams mapping out the entire JARVIS CRM system, its modular monolith architecture, role-based workflows, and data pipelines. It is structured to be easy to understand and present.

---

## 1. High-Level System Architecture (10,000-Foot View)

The entire application runs as a **Modular Monolith** with strict domain boundaries, server-enforced multi-tenancy, and role-based access control.

```mermaid
graph TB
    subgraph Clients["Presentation Layer (React 19 + TypeScript + Vite)"]
        SA_UI["Super Admin Console"]
        OA_UI["Org Admin Workspace"]
        TC_UI["Telecaller Outbound Desk"]
    end

    subgraph Gateway["API Gateway & Security Layer (FastAPI)"]
        JWT["OAuth2 JWT Authentication"]
        TenantGuard["Tenant Resolution Guard (get_tenant_id)"]
        GlobalGuard["Optional Tenant Guard (get_optional_tenant_id)"]
        MaskingInterceptor["Anti-Theft Masking Engine"]
    end

    subgraph Domains["Domain Services Layer (Modular Monolith)"]
        AuthSvc["Auth & User Management"]
        LeadSvc["Lead & Pipeline Engine"]
        ImportSvc["Streaming Ingestion Engine"]
        CommSvc["Communication & Actions Proxy"]
        RadarSvc["Radar Intelligence & Audit Engine"]
    end

    subgraph Data["Persistence Layer (SQLite / PostgreSQL)"]
        OrgDB[("Tenant Scoped Data (Filtered by organization_id)")]
        GlobalDB[("Platform Scope (Global Registry & Super Admin)")]
    end

    SA_UI --> GlobalGuard
    OA_UI --> TenantGuard
    TC_UI --> TenantGuard

    TenantGuard --> JWT
    GlobalGuard --> JWT

    JWT --> MaskingInterceptor
    MaskingInterceptor --> Domains

    AuthSvc --> OrgDB
    LeadSvc --> OrgDB
    ImportSvc --> OrgDB
    ImportSvc --> GlobalDB
    CommSvc --> OrgDB
    RadarSvc --> OrgDB
```

---

## 2. Role-Based Navigation & Module Breakdown

JARVIS CRM delivers distinct, dedicated module workflows based on the user's authenticated persona:

```mermaid
graph TD
    User([Authenticated User]) --> CheckRole{User Role}

    %% SUPER ADMIN ROUTE
    CheckRole -->|"SUPERADMIN (Platform Level)"| SuperAdminModules["Super Admin Console"]
    subgraph SAModules["Super Admin Workspaces"]
        SuperAdminModules --> Mod_SA_Org["Organizations Console<br>• Tenant Workspaces<br>• Workspace Provisioning<br>• Subscription Tiers & KPIs"]
        SuperAdminModules --> Mod_SA_Audit["Platform Security Audit<br>• Cross-Tenant Audit Trail<br>• Action Type Filter<br>• Real-Time Security Log"]
        SuperAdminModules --> Mod_SA_Global["Global Database Registry<br>• 70,000+ Company Master<br>• Director / Contact Mapping<br>• Global Bulk Ingestion Wizard"]
    end

    %% ORG ADMIN ROUTE
    CheckRole -->|"ADMIN (Tenant Level)"| AdminModules["Org Admin Workspace"]
    subgraph OAModules["CRM Organization Modules"]
        AdminModules --> Mod_OA_Radar["Radar Insights<br>• Deal velocity metrics<br>• Stale lead warnings<br>• Revenue forecasting"]
        AdminModules --> Mod_OA_Kanban["Sales Pipeline Kanban<br>• Native Drag & Drop<br>• Dynamic stage totals<br>• Real-time search & filters"]
        AdminModules --> Mod_OA_Leads["Leads & Contacts Directory<br>• Single '+ Add Lead' manual entry<br>• 360° Lead Detail Drawer<br>• Full contact info unmasked"]
        AdminModules --> Mod_OA_Import["Lead Ingestion Center<br>• CSV / Excel file uploads<br>• Smart auto-column mapping<br>• Deduplication & stage assignment"]
    end

    %% TELECALLER ROUTE
    CheckRole -->|"TELECALLER (Front-Line Sales)"| TelecallerModules["Telecaller Desk"]
    subgraph TCModules["Outbound Calling Desk"]
        TelecallerModules --> Mod_TC_Masked["Anti-Theft Contact View<br>• Phone: +91 98**** 1234<br>• Email: ex****@domain.com<br>• Zero raw export capability"]
        TelecallerModules --> Mod_TC_Cockpit["Live VoIP Calling Cockpit<br>• Real-time ticking call timer<br>• Mute / End call toggles<br>• Auto-logs duration & notes"]
        TelecallerModules --> Mod_TC_Actions["One-Click Actions<br>• Proxied WhatsApp Web launch<br>• Direct Gmail composer<br>• Quick outcome logging"]
    end
```

---

## 3. Lead Lifecycle & Pipeline Progression Flow

This flow illustrates how leads enter the organization, move through stages via Drag-and-Drop, and maintain immutable audit history.

```mermaid
sequenceDiagram
    autonumber
    actor User as Sales Rep / Org Admin
    participant UI as Kanban Board UI
    participant API as FastAPI (/api/v1/leads)
    participant LeadService as Lead Service
    participant DB as Database Engine

    Note over User, UI: Action: Drag lead card to new column
    User->>UI: Drags card from "NEW" to "CONTACTED"
    UI->>UI: Optimistic UI Update (Card snaps, counters refresh)
    UI->>API: POST /leads/{id}/stage { stage_id, reason }
    
    API->>LeadService: change_lead_stage()
    LeadService->>DB: Query Lead & Previous Stage History
    LeadService->>LeadService: Calculate elapsed duration in previous stage
    LeadService->>DB: INSERT into lead_stage_history (Immutable audit record)
    LeadService->>DB: UPDATE lead (new pipeline_stage_id, status: OPEN/WON/LOST)
    LeadService->>DB: INSERT into activities (System: "Moved to Contacted")
    LeadService->>DB: INSERT into radar_events (Action: "STAGE_CHANGED")
    LeadService->>DB: COMMIT Transaction
    
    API-->>UI: Return serialized LeadOut
    UI->>UI: Show success banner: Advanced "Tata Power" -> Contacted
```

---

## 4. Anti-Theft Data Masking & Outbound Calling Flow

How Telecallers conduct calls and emails without leaking the raw proprietary lead database.

```mermaid
sequenceDiagram
    autonumber
    actor Telecaller as Telecaller Agent
    participant DeskUI as Telecaller Desk UI
    participant API as Backend Security Gateway
    participant LeadService as Lead Service
    participant External as External Service (Gmail / WhatsApp / VoIP)

    Telecaller->>DeskUI: Open Telecaller Desk
    DeskUI->>API: GET /api/v1/leads?status=OPEN
    API->>LeadService: Fetch leads for tenant
    LeadService->>LeadService: should_mask_field(TELECALLER) = TRUE
    LeadService-->>DeskUI: Returns Masked Leads (+91 98**** 1234, ex****@domain.com)

    alt One-Click VoIP Call
        Telecaller->>DeskUI: Click "Call Lead"
        DeskUI->>DeskUI: Mount Live VoIP Cockpit (Timer starts: 00:01, 00:02...)
        Telecaller->>DeskUI: Click "End Call" (Duration: 24s)
        DeskUI->>DeskUI: Auto-prefill notes: "Connected outbound call (24s)"
        DeskUI->>API: POST /activities (Logs call activity & outcome)
    else One-Click WhatsApp Action
        Telecaller->>DeskUI: Click "WhatsApp"
        DeskUI->>API: POST /leads/{id}/action/whatsapp
        API->>API: Audit in radar_events ("WHATSAPP_TRIGGERED")
        API-->>DeskUI: Return WhatsApp Web URL with encoded contextual greeting
        DeskUI->>External: Opens WhatsApp Web in new tab
    else One-Click Gmail Action
        Telecaller->>DeskUI: Click "Email (Gmail)"
        DeskUI->>API: POST /leads/{id}/action/email
        API->>API: Audit in radar_events ("EMAIL_TRIGGERED")
        API-->>DeskUI: Return Gmail Compose URL with recipient & subject
        DeskUI->>External: Opens mail.google.com with pre-populated composer
    end
```

---

## 5. Dual Ingestion Pipeline (Tenant Leads vs. Global Companies)

A single smart auto-mapping wizard handles both tenant sales leads and global master data:

```mermaid
flowchart TD
    Start([User Uploads CSV / Excel]) --> Inspect["Inspect Headers & Sample Rows"]
    Inspect --> Detect["Smart Auto-Detection Engine"]
    Detect --> Modal["ImportModal: Column Mapping Confirmation"]

    Modal --> ChooseType{Job Scope}

    %% TENANT LEADS BRANCH
    ChooseType -->|"TENANT_LEADS (Org Admin)"| TenantIngest["Tenant Leads Ingestion Engine"]
    subgraph TenantFlow["Tenant Scoped Lead Import"]
        TenantIngest --> T_OrgCheck["Derive organization_id from Auth Token"]
        T_OrgCheck --> T_Stage["Assign to default 'NEW' Pipeline Stage"]
        T_Stage --> T_Contact["Create or Match Contact"]
        T_Contact --> T_Company["Create or Match Company"]
        T_Company --> T_Lead["Insert Lead (score, priority, title, value)"]
        T_Lead --> T_History["Insert Initial lead_stage_history (Immutable)"]
    end

    %% GLOBAL COMPANIES BRANCH
    ChooseType -->|"GLOBAL_COMPANIES (Super Admin)"| GlobalIngest["Global Master Registry Engine"]
    subgraph GlobalFlow["Global Enterprise Import"]
        GlobalIngest --> G_PlatformCheck["Verify SUPERADMIN Platform Scope"]
        G_PlatformCheck --> G_Dedupe{"Deduplication Check (by CIN / Legal Name)"}
        G_Dedupe -->|Exists| G_Update["Update Existing GlobalCompany record"]
        G_Dedupe -->|New| G_Insert["Insert into GlobalCompany"]
        G_Insert --> G_Contact["Insert into GlobalContact (Directors/Key Persons)"]
        G_Contact --> G_Map["Establish GlobalCompanyContactMap relationship"]
    end

    TenantFlow --> Success([Job Completed: Rows Processed & Error Isolation Logged])
    GlobalFlow --> Success
```

---

## 6. Entity Relationship & Data Model (ER Diagram)

The underlying relational schema guarantees tenant isolation, domain integrity, and auditability:

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : members
    ORGANIZATIONS ||--o{ PIPELINES : owns
    ORGANIZATIONS ||--o{ COMPANIES : registers
    ORGANIZATIONS ||--o{ CONTACTS : registers
    ORGANIZATIONS ||--o{ LEADS : tracks
    ORGANIZATIONS ||--o{ IMPORT_JOBS : runs
    ORGANIZATIONS ||--o{ RADAR_EVENTS : logs

    PIPELINES ||--o{ PIPELINE_STAGES : steps
    PIPELINE_STAGES ||--o{ LEADS : current_stage

    COMPANIES ||--o{ CONTACTS : employs
    CONTACTS ||--o{ LEADS : prospect
    COMPANIES ||--o{ LEADS : account

    LEADS ||--o{ LEAD_STAGE_HISTORY : audit_trail
    LEADS ||--o{ ACTIVITIES : interaction_history
    LEADS ||--o{ TASKS : follow_ups

    GLOBAL_COMPANIES ||--o{ GLOBAL_COMPANY_CONTACT_MAP : links
    GLOBAL_CONTACTS ||--o{ GLOBAL_COMPANY_CONTACT_MAP : links
```

---

## 7. How to Explain This Architecture in 2 Minutes

When presenting this build to stakeholders or technical evaluators:

1. **"It's a Modular Monolith with Server-Enforced Multi-Tenancy"**:
   - Point to **Diagram 1 & 2**. Every tenant is mathematically isolated by `organization_id` derived server-side from JWT tokens. Clients cannot manipulate tenancy.
2. **"Three Dedicated User Experiences"**:
   - **Super Admin**: Manages tenant workspaces, platform audits, and global data ingestion.
   - **CRM Org Admin**: Runs executive radar insights, drags leads across Kanban stages, manages contacts, and imports lists.
   - **Telecaller**: Operates in an anti-theft environment where all phone numbers and emails are masked, using a built-in VoIP calling cockpit and one-click WhatsApp/Gmail triggers.
3. **"Pipeline Immutability & Auditability"**:
   - Point to **Diagram 3 & 6**. Stage configurations never get corrupted by bulk imports. Every transition logs an immutable row in `lead_stage_history` with the exact duration spent in that stage.
4. **"Zero Data Leakage"**:
   - Point to **Diagram 4**. Telecallers can call, message, and email prospects without ever having access to exportable raw database records.
