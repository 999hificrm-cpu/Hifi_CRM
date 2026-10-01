-- ============================================================================
-- JARVIS CRM — CANONICAL DATABASE SCHEMA (v3.0, final)
-- Engine: PostgreSQL 15+
-- Supersedes: 03_DATABASE_SCHEMA.md v2.0 and the earlier two-database draft
--
-- Architecture: single PostgreSQL database, shared-schema multi-tenancy.
-- `tenants.id` is the isolation key. Platform (global) tables and tenant CRM
-- tables live in the SAME database, which means — unlike the earlier
-- two-physical-database draft — cross-domain foreign keys ARE real,
-- enforced, and transactional (see JARVIS_CRM_DATABASE_ARCHITECTURE.md §2).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 0. EXTENSIONS
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive email columns

-- ----------------------------------------------------------------------------
-- 1. ENUM TYPES
-- ----------------------------------------------------------------------------
CREATE TYPE platform_role_enum   AS ENUM ('SUPER_ADMIN', 'DATA_OPS');
CREATE TYPE tenant_role_enum     AS ENUM ('TENANT_ADMIN', 'TENANT_MANAGER', 'TENANT_AGENT');
CREATE TYPE user_status_enum     AS ENUM ('INVITED', 'ACTIVE', 'SUSPENDED', 'DEACTIVATED');

CREATE TYPE upload_batch_type_enum   AS ENUM ('COMPANY', 'PEOPLE', 'COMPANY_PERSON_MAP', 'TENANT_LEADS');
CREATE TYPE upload_batch_status_enum AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'PARTIAL', 'FAILED');
CREATE TYPE match_status_enum        AS ENUM ('AUTO_MATCHED', 'NEEDS_REVIEW', 'CONFIRMED', 'REJECTED');

CREATE TYPE lead_source_enum    AS ENUM ('MANUAL', 'IMPORT', 'GLOBAL_PULL');
CREATE TYPE lead_priority_enum  AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
CREATE TYPE lead_status_enum    AS ENUM ('OPEN', 'WON', 'LOST', 'ARCHIVED');

CREATE TYPE masking_field_enum AS ENUM ('PHONE', 'ALTERNATE_PHONE', 'EMAIL', 'ADDRESS', 'LINKEDIN');

CREATE TYPE activity_type_enum   AS ENUM ('CALL', 'WHATSAPP', 'EMAIL', 'MEETING', 'NOTE', 'SYSTEM');
CREATE TYPE direction_enum       AS ENUM ('INBOUND', 'OUTBOUND');
CREATE TYPE call_status_enum     AS ENUM ('COMPLETED', 'MISSED', 'FAILED', 'NO_ANSWER', 'BUSY');
CREATE TYPE message_channel_enum AS ENUM ('WHATSAPP', 'SMS');
CREATE TYPE delivery_status_enum AS ENUM ('QUEUED', 'SENT', 'DELIVERED', 'READ', 'FAILED');

CREATE TYPE task_type_enum   AS ENUM ('FOLLOW_UP', 'CALL_BACK', 'MEETING_PREP', 'GENERAL');
CREATE TYPE task_status_enum AS ENUM ('PENDING', 'COMPLETED', 'CANCELLED', 'OVERDUE');

CREATE TYPE radar_action_enum AS ENUM (
  'CONTACT_VIEW', 'BULK_VIEW', 'EXPORT', 'MASKED_CALL', 'MASKED_WHATSAPP',
  'MASKED_EMAIL', 'REVEAL_REQUEST', 'REVEAL_GRANTED', 'LOGIN'
);
CREATE TYPE radar_alert_status_enum AS ENUM ('OPEN', 'ACKNOWLEDGED', 'DISMISSED', 'ESCALATED');

CREATE TYPE subscription_status_enum AS ENUM ('TRIALING', 'ACTIVE', 'PAST_DUE', 'CANCELLED', 'EXPIRED');

CREATE TYPE notification_channel_enum AS ENUM ('IN_APP', 'PUSH', 'EMAIL');
CREATE TYPE notification_status_enum  AS ENUM ('PENDING', 'SENT', 'READ', 'FAILED');

CREATE TYPE storage_provider_enum AS ENUM ('MINIO', 'S3', 'R2', 'LOCAL');

-- ----------------------------------------------------------------------------
-- 2. SHARED TRIGGER FUNCTIONS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 3. IDENTITY & ACCESS  (spans platform + tenant — see doc §3.1)
-- ============================================================================

CREATE TABLE plans (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code                VARCHAR(50) UNIQUE NOT NULL,          -- STARTER / GROWTH / ENTERPRISE
  name                VARCHAR(150) NOT NULL,
  seat_limit          INTEGER NOT NULL,
  monthly_pull_quota  INTEGER NOT NULL,
  feature_flags       JSONB NOT NULL DEFAULT '{}',
  price_amount        NUMERIC(12,2),
  price_currency      VARCHAR(10) NOT NULL DEFAULT 'INR',
  is_active           BOOLEAN NOT NULL DEFAULT true,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_plans_updated_at BEFORE UPDATE ON plans
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE tenants (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(255) NOT NULL,
  slug        VARCHAR(100) UNIQUE NOT NULL,
  status      VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',        -- ACTIVE / SUSPENDED / CANCELLED
  timezone    VARCHAR(100) NOT NULL DEFAULT 'Asia/Kolkata',
  settings    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_tenants_updated_at BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE tenant_subscriptions (
  id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  plan_id                         UUID NOT NULL REFERENCES plans(id),
  status                          subscription_status_enum NOT NULL DEFAULT 'TRIALING',
  seats_purchased                 INTEGER NOT NULL,
  pull_quota_monthly              INTEGER NOT NULL,          -- snapshot from plan, can be overridden
  pull_quota_used_current_period  INTEGER NOT NULL DEFAULT 0,
  current_period_start            DATE NOT NULL,
  current_period_end              DATE NOT NULL,
  renewal_date                    DATE,
  billing_provider                VARCHAR(50) DEFAULT 'RAZORPAY',
  billing_provider_ref            VARCHAR(255),
  created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Only one "live" subscription per tenant at a time.
CREATE UNIQUE INDEX uq_tenant_subscriptions_live
  ON tenant_subscriptions (tenant_id)
  WHERE status IN ('TRIALING', 'ACTIVE', 'PAST_DUE');
CREATE TRIGGER trg_tenant_subscriptions_updated_at BEFORE UPDATE ON tenant_subscriptions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE users (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID REFERENCES tenants(id) ON DELETE CASCADE,   -- NULL = platform user
  platform_role         platform_role_enum,
  tenant_role           tenant_role_enum,
  permission_overrides  JSONB NOT NULL DEFAULT '{}',        -- granular per-user exceptions (FR-002)
  full_name             VARCHAR(255) NOT NULL,
  email                 CITEXT NOT NULL,
  phone                 VARCHAR(50),
  password_hash         TEXT NOT NULL,
  status                user_status_enum NOT NULL DEFAULT 'INVITED',
  last_login_at         TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- A user is EITHER a platform user XOR a tenant user. Enforced at the DB,
  -- not left to application discipline (resolves ambiguity in the source docs).
  CONSTRAINT chk_users_scope_exclusive CHECK (
    (tenant_id IS NULL     AND platform_role IS NOT NULL AND tenant_role IS NULL) OR
    (tenant_id IS NOT NULL AND tenant_role   IS NOT NULL AND platform_role IS NULL)
  )
);
CREATE UNIQUE INDEX uq_users_platform_email ON users (email) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX uq_users_tenant_email   ON users (tenant_id, email) WHERE tenant_id IS NOT NULL;
CREATE INDEX ix_users_tenant_id ON users (tenant_id);
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE invites (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID REFERENCES tenants(id) ON DELETE CASCADE,   -- NULL = platform invite (e.g. DATA_OPS)
  email         CITEXT NOT NULL,
  tenant_role   tenant_role_enum,
  platform_role platform_role_enum,
  invited_by    UUID NOT NULL REFERENCES users(id),
  token         TEXT UNIQUE NOT NULL,
  status        VARCHAR(30) NOT NULL DEFAULT 'PENDING',   -- PENDING / ACCEPTED / EXPIRED / REVOKED
  expires_at    TIMESTAMPTZ NOT NULL,
  accepted_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_invites_scope_exclusive CHECK (
    (tenant_id IS NULL     AND platform_role IS NOT NULL AND tenant_role IS NULL) OR
    (tenant_id IS NOT NULL AND tenant_role   IS NOT NULL AND platform_role IS NULL)
  )
);
CREATE INDEX ix_invites_email ON invites (email);

-- ============================================================================
-- 4. PLATFORM / GLOBAL REGISTRY  (super-admin owned, immutable from tenant screens)
-- ============================================================================

-- platform_data_upload_batches is forward-declared here (documents/companies FK into it)
CREATE TABLE platform_data_upload_batches (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_type               upload_batch_type_enum NOT NULL,
  uploaded_by              UUID NOT NULL REFERENCES users(id),
  target_tenant_id         UUID REFERENCES tenants(id),   -- required when batch_type = TENANT_LEADS and uploader is a platform user
  file_name                VARCHAR(255) NOT NULL,
  file_type                VARCHAR(20) NOT NULL,
  storage_document_id      UUID,        -- FK added after `documents` table exists (see §8)
  status                   upload_batch_status_enum NOT NULL DEFAULT 'PENDING',
  total_rows               INTEGER NOT NULL DEFAULT 0,
  processed_rows           INTEGER NOT NULL DEFAULT 0,
  successful_rows          INTEGER NOT NULL DEFAULT 0,
  duplicate_rows           INTEGER NOT NULL DEFAULT 0,
  invalid_rows             INTEGER NOT NULL DEFAULT 0,
  failed_rows              INTEGER NOT NULL DEFAULT 0,
  error_summary            JSONB,
  started_at               TIMESTAMPTZ,
  completed_at             TIMESTAMPTZ,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_batch_tenant_leads_target CHECK (
    batch_type <> 'TENANT_LEADS' OR target_tenant_id IS NOT NULL
  )
);
CREATE INDEX ix_upload_batches_tenant ON platform_data_upload_batches (target_tenant_id);

CREATE TABLE platform_data_upload_errors (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id     UUID NOT NULL REFERENCES platform_data_upload_batches(id) ON DELETE CASCADE,
  row_number   INTEGER NOT NULL,
  raw_row      JSONB NOT NULL,          -- original row, for reprocessing/debugging
  error_code   VARCHAR(100) NOT NULL,
  error_message TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_upload_errors_batch ON platform_data_upload_errors (batch_id);

CREATE TABLE platform_companies (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  registry_country          CHAR(2) NOT NULL DEFAULT 'IN',
  registry_type             VARCHAR(30) NOT NULL DEFAULT 'CIN',   -- generalized: CIN today, other jurisdictions later
  registry_id               VARCHAR(64) NOT NULL,                 -- the CIN value lives here
  legal_name                VARCHAR(255) NOT NULL,
  display_name              VARCHAR(255),
  company_type              VARCHAR(50),
  industry                  VARCHAR(150),
  incorporation_date        DATE,
  website                   TEXT,
  email                     CITEXT,
  phone                     VARCHAR(50),
  address                   TEXT,
  city                      VARCHAR(100),
  state                     VARCHAR(100),
  country                   CHAR(2) NOT NULL DEFAULT 'IN',
  postal_code                VARCHAR(20),
  linkedin_url               TEXT,
  status                    VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE / DEACTIVATED (soft delete, FR-015)
  deactivated_at            TIMESTAMPTZ,
  deactivated_reason        TEXT,
  first_seen_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_updated_by_batch_id  UUID REFERENCES platform_data_upload_batches(id),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Hard dedupe key (FR-010): DB-enforced, not just application upsert logic.
CREATE UNIQUE INDEX uq_platform_companies_registry
  ON platform_companies (registry_country, registry_type, registry_id);
CREATE INDEX ix_platform_companies_city_industry ON platform_companies (city, industry);
CREATE INDEX ix_platform_companies_email ON platform_companies (email);

CREATE TABLE platform_people (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  registry_country          CHAR(2) NOT NULL DEFAULT 'IN',
  registry_type             VARCHAR(30) NOT NULL DEFAULT 'DIN',
  registry_id               VARCHAR(64),                    -- nullable: DIN may be absent (FR-011 fuzzy path)
  first_name                VARCHAR(100),
  last_name                 VARCHAR(100),
  full_name                 VARCHAR(255) NOT NULL,
  email                     CITEXT,
  phone                     VARCHAR(50),
  linkedin_url              TEXT,
  country                   VARCHAR(100),
  state                     VARCHAR(100),
  city                      VARCHAR(100),
  match_status              match_status_enum NOT NULL DEFAULT 'AUTO_MATCHED',  -- FR-011 review queue
  match_notes               TEXT,
  status                    VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
  first_seen_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_updated_by_batch_id  UUID REFERENCES platform_data_upload_batches(id),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_platform_people_registry
  ON platform_people (registry_country, registry_type, registry_id)
  WHERE registry_id IS NOT NULL;
-- Fuzzy-match dedupe keys (per original schema note: "these become important deduplication keys")
CREATE INDEX ix_platform_people_email ON platform_people (email);
CREATE INDEX ix_platform_people_phone ON platform_people (phone);
CREATE INDEX ix_platform_people_linkedin ON platform_people (linkedin_url);
CREATE INDEX ix_platform_people_review_queue ON platform_people (match_status) WHERE match_status = 'NEEDS_REVIEW';

CREATE TABLE platform_company_person_map (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id        UUID NOT NULL REFERENCES platform_companies(id) ON DELETE CASCADE,
  person_id         UUID NOT NULL REFERENCES platform_people(id) ON DELETE CASCADE,
  designation       VARCHAR(150),
  appointment_date  DATE,
  cessation_date    DATE,
  status            VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE / CEASED
  source_batch_id   UUID REFERENCES platform_data_upload_batches(id),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_company_person_stint
  ON platform_company_person_map (company_id, person_id, COALESCE(appointment_date, 'epoch'::date));
CREATE INDEX ix_company_person_person ON platform_company_person_map (person_id);
CREATE TRIGGER trg_cpm_updated_at BEFORE UPDATE ON platform_company_person_map
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 5. TENANT CRM MASTER DATA
-- ============================================================================

CREATE TABLE crm_companies (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  global_company_id  UUID REFERENCES platform_companies(id),   -- REAL FK now (single DB) — was a "logical reference" only in the two-DB draft
  name               VARCHAR(255) NOT NULL,
  legal_name         VARCHAR(255),
  domain             VARCHAR(255),
  industry           VARCHAR(150),
  company_size       VARCHAR(50),
  country            VARCHAR(100),
  state              VARCHAR(100),
  city               VARCHAR(100),
  address            TEXT,
  phone              VARCHAR(50),
  email              CITEXT,
  website            VARCHAR(500),
  status             VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
  created_by         UUID REFERENCES users(id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_crm_companies_tenant_domain
  ON crm_companies (tenant_id, domain) WHERE domain IS NOT NULL;
CREATE INDEX ix_crm_companies_tenant ON crm_companies (tenant_id);
CREATE INDEX ix_crm_companies_global ON crm_companies (global_company_id);
CREATE TRIGGER trg_crm_companies_updated_at BEFORE UPDATE ON crm_companies
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE crm_people (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  global_person_id UUID REFERENCES platform_people(id),
  crm_company_id   UUID REFERENCES crm_companies(id),
  first_name       VARCHAR(100),
  last_name        VARCHAR(100),
  full_name        VARCHAR(255) NOT NULL,
  email            CITEXT,
  phone            VARCHAR(50),
  alternate_phone  VARCHAR(50),
  job_title        VARCHAR(150),
  department       VARCHAR(100),
  linkedin_url     VARCHAR(500),
  status           VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
  created_by       UUID REFERENCES users(id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_crm_people_tenant_email
  ON crm_people (tenant_id, email) WHERE email IS NOT NULL;
CREATE INDEX ix_crm_people_tenant ON crm_people (tenant_id);
CREATE INDEX ix_crm_people_company ON crm_people (crm_company_id);
CREATE INDEX ix_crm_people_global ON crm_people (global_person_id);
CREATE TRIGGER trg_crm_people_updated_at BEFORE UPDATE ON crm_people
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 6. PIPELINE & LEADS
-- ============================================================================

CREATE TABLE pipelines (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name        VARCHAR(150) NOT NULL,
  description TEXT,
  is_default  BOOLEAN NOT NULL DEFAULT false,
  status      VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_pipelines_one_default_per_tenant
  ON pipelines (tenant_id) WHERE is_default = true;
CREATE TRIGGER trg_pipelines_updated_at BEFORE UPDATE ON pipelines
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE pipeline_stages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline_id  UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
  name         VARCHAR(100) NOT NULL,
  code         VARCHAR(50) NOT NULL,
  position     INTEGER NOT NULL,
  color        VARCHAR(20),
  probability  NUMERIC(5,2),
  is_won       BOOLEAN NOT NULL DEFAULT false,
  is_lost      BOOLEAN NOT NULL DEFAULT false,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_stage_not_won_and_lost CHECK (NOT (is_won AND is_lost))
);
CREATE UNIQUE INDEX uq_pipeline_stages_position ON pipeline_stages (pipeline_id, position);
CREATE UNIQUE INDEX uq_pipeline_stages_code ON pipeline_stages (pipeline_id, code);
CREATE TRIGGER trg_pipeline_stages_updated_at BEFORE UPDATE ON pipeline_stages
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE leads (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                 UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  crm_company_id            UUID REFERENCES crm_companies(id),
  pipeline_stage_id         UUID NOT NULL REFERENCES pipeline_stages(id),   -- current stage ONLY; pipeline resolved via stage
  source_global_company_id  UUID REFERENCES platform_companies(id),
  source_global_person_id   UUID REFERENCES platform_people(id),
  owner_id                  UUID REFERENCES users(id),
  primary_contact_id        UUID,   -- FK added below after lead_contacts exists (circular ref)
  title                     VARCHAR(255) NOT NULL,
  contact_name              VARCHAR(255),   -- fast-list snapshot of the primary contact — see doc §5
  contact_email             CITEXT,
  contact_phone             VARCHAR(50),
  source                    lead_source_enum NOT NULL DEFAULT 'MANUAL',
  status                    lead_status_enum NOT NULL DEFAULT 'OPEN',   -- cached, kept in sync by trigger from stage flags
  priority                  lead_priority_enum NOT NULL DEFAULT 'MEDIUM',
  score                     INTEGER,
  value                     NUMERIC(15,2),
  currency                  VARCHAR(10) NOT NULL DEFAULT 'INR',
  description               TEXT,
  notes                     TEXT,
  created_by                UUID REFERENCES users(id),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at                 TIMESTAMPTZ
);
CREATE INDEX ix_leads_tenant_status ON leads (tenant_id, status);
CREATE INDEX ix_leads_tenant_stage ON leads (tenant_id, pipeline_stage_id);
CREATE INDEX ix_leads_owner ON leads (owner_id);
CREATE INDEX ix_leads_company ON leads (crm_company_id);
CREATE TRIGGER trg_leads_updated_at BEFORE UPDATE ON leads
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- lead_contacts resolves the SRS FR-033 gap: a lead supports MANY contacts,
-- not just the one snapshot on the lead row.
CREATE TABLE lead_contacts (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id        UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  crm_person_id  UUID NOT NULL REFERENCES crm_people(id),
  role           VARCHAR(100),          -- e.g. Decision Maker, Influencer
  is_primary     BOOLEAN NOT NULL DEFAULT false,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_lead_contacts_pair ON lead_contacts (lead_id, crm_person_id);
CREATE UNIQUE INDEX uq_lead_contacts_one_primary ON lead_contacts (lead_id) WHERE is_primary = true;
CREATE INDEX ix_lead_contacts_person ON lead_contacts (crm_person_id);
CREATE TRIGGER trg_lead_contacts_updated_at BEFORE UPDATE ON lead_contacts
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE leads
  ADD CONSTRAINT fk_leads_primary_contact
  FOREIGN KEY (primary_contact_id) REFERENCES lead_contacts(id) ON DELETE SET NULL;

CREATE TABLE lead_stage_history (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id      UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  pipeline_id  UUID NOT NULL REFERENCES pipelines(id),
  from_stage_id UUID REFERENCES pipeline_stages(id),
  to_stage_id  UUID NOT NULL REFERENCES pipeline_stages(id),
  changed_by   UUID REFERENCES users(id),
  reason       TEXT,
  changed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_lead_stage_history_lead ON lead_stage_history (lead_id, changed_at);

CREATE TABLE lead_assignments (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id          UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  user_id          UUID NOT NULL REFERENCES users(id),
  assignment_type  VARCHAR(50) NOT NULL DEFAULT 'PRIMARY',   -- PRIMARY / SUPPORT / MANAGER
  is_primary       BOOLEAN NOT NULL DEFAULT true,
  assigned_by      UUID REFERENCES users(id),
  assigned_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  unassigned_at    TIMESTAMPTZ
);
CREATE INDEX ix_lead_assignments_lead ON lead_assignments (lead_id);
CREATE INDEX ix_lead_assignments_user_active ON lead_assignments (user_id) WHERE unassigned_at IS NULL;

-- Keep leads.status/closed_at in sync whenever the current stage changes,
-- instead of leaving "won/lost" derivation to scattered application code.
CREATE OR REPLACE FUNCTION sync_lead_status_from_stage() RETURNS TRIGGER AS $$
DECLARE
  v_is_won BOOLEAN;
  v_is_lost BOOLEAN;
BEGIN
  SELECT is_won, is_lost INTO v_is_won, v_is_lost
  FROM pipeline_stages WHERE id = NEW.pipeline_stage_id;

  IF v_is_won THEN
    NEW.status := 'WON';
    NEW.closed_at := COALESCE(NEW.closed_at, now());
  ELSIF v_is_lost THEN
    NEW.status := 'LOST';
    NEW.closed_at := COALESCE(NEW.closed_at, now());
  ELSIF NEW.status IN ('WON','LOST') THEN
    -- moved back out of a won/lost stage: reopen
    NEW.status := 'OPEN';
    NEW.closed_at := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_leads_stage_sync
  BEFORE INSERT OR UPDATE OF pipeline_stage_id ON leads
  FOR EACH ROW EXECUTE FUNCTION sync_lead_status_from_stage();

CREATE TABLE data_pull_log (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                 UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  pulled_by                 UUID NOT NULL REFERENCES users(id),
  global_company_id         UUID REFERENCES platform_companies(id),
  global_person_id          UUID REFERENCES platform_people(id),
  resulting_crm_company_id  UUID REFERENCES crm_companies(id),
  resulting_crm_person_id   UUID REFERENCES crm_people(id),
  resulting_lead_id         UUID REFERENCES leads(id),
  global_version_snapshot   JSONB NOT NULL,   -- frozen copy of pulled fields, survives later global edits/soft-delete
  pulled_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_data_pull_log_tenant ON data_pull_log (tenant_id, pulled_at);

-- ============================================================================
-- 7. MASKING (core differentiator — FR-040..046)
-- ============================================================================

CREATE TABLE masking_policies (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  tenant_role  tenant_role_enum NOT NULL,
  field        masking_field_enum NOT NULL,
  is_masked    BOOLEAN NOT NULL DEFAULT true,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_masking_policies ON masking_policies (tenant_id, tenant_role, field);
CREATE TRIGGER trg_masking_policies_updated_at BEFORE UPDATE ON masking_policies
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE masking_exceptions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id      UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id),
  field        masking_field_enum NOT NULL,
  granted_by   UUID NOT NULL REFERENCES users(id),
  granted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ NOT NULL,
  revoked_at   TIMESTAMPTZ,
  reason       TEXT
);
CREATE INDEX ix_masking_exceptions_active
  ON masking_exceptions (lead_id, user_id, field)
  WHERE revoked_at IS NULL;

-- ============================================================================
-- 8. FILES / DOCUMENTS
-- ============================================================================

CREATE TABLE documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID REFERENCES tenants(id) ON DELETE CASCADE,   -- NULL = platform-level document (e.g. a raw global upload file)
  uploaded_by       UUID REFERENCES users(id),
  file_name         VARCHAR(255) NOT NULL,
  original_name     VARCHAR(255) NOT NULL,
  mime_type         VARCHAR(100),
  size_bytes        BIGINT,
  storage_provider  storage_provider_enum NOT NULL DEFAULT 'MINIO',
  storage_key       TEXT NOT NULL,
  checksum_sha256   VARCHAR(128),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_documents_tenant ON documents (tenant_id);

ALTER TABLE platform_data_upload_batches
  ADD CONSTRAINT fk_upload_batches_document
  FOREIGN KEY (storage_document_id) REFERENCES documents(id);

CREATE TABLE document_links (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID REFERENCES tenants(id) ON DELETE CASCADE,
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  entity_type  VARCHAR(50) NOT NULL,     -- LEAD / COMPANY / TASK / UPLOAD_BATCH
  entity_id    UUID NOT NULL,
  created_by   UUID REFERENCES users(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_document_links_entity ON document_links (entity_type, entity_id);

-- ============================================================================
-- 9. ACTIVITIES / COMMUNICATION
-- ============================================================================

CREATE TABLE activities (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id         UUID REFERENCES leads(id) ON DELETE CASCADE,
  crm_company_id  UUID REFERENCES crm_companies(id),
  crm_person_id   UUID REFERENCES crm_people(id),
  user_id         UUID NOT NULL REFERENCES users(id),
  activity_type   activity_type_enum NOT NULL,
  subject         VARCHAR(255),
  description     TEXT,
  status          VARCHAR(30) NOT NULL DEFAULT 'COMPLETED',
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_activities_lead ON activities (lead_id, occurred_at);
CREATE INDEX ix_activities_tenant_type ON activities (tenant_id, activity_type);

CREATE TABLE call_details (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity_id        UUID NOT NULL UNIQUE REFERENCES activities(id) ON DELETE CASCADE,
  direction          direction_enum NOT NULL,
  masked             BOOLEAN NOT NULL DEFAULT false,
  provider           VARCHAR(50),
  provider_call_id   VARCHAR(255),
  duration_seconds   INTEGER,
  call_status        call_status_enum,
  recording_url      TEXT,
  transcript         TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE message_details (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity_id          UUID NOT NULL UNIQUE REFERENCES activities(id) ON DELETE CASCADE,
  channel              message_channel_enum NOT NULL,
  direction            direction_enum NOT NULL,
  masked               BOOLEAN NOT NULL DEFAULT false,
  template_name        VARCHAR(150),
  sender               VARCHAR(255),
  recipient            VARCHAR(255),
  message_body         TEXT,
  external_message_id  VARCHAR(255),
  delivery_status      delivery_status_enum,
  sent_at              TIMESTAMPTZ,
  delivered_at         TIMESTAMPTZ,
  read_at              TIMESTAMPTZ
);

CREATE TABLE email_details (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity_id          UUID NOT NULL UNIQUE REFERENCES activities(id) ON DELETE CASCADE,
  direction            direction_enum NOT NULL,
  masked               BOOLEAN NOT NULL DEFAULT false,
  from_email           VARCHAR(255),
  to_email             TEXT,
  cc                   TEXT,
  bcc                  TEXT,
  subject              VARCHAR(500),
  body_text            TEXT,
  body_html            TEXT,
  external_message_id  VARCHAR(255),
  thread_id            VARCHAR(255),
  delivery_status      delivery_status_enum,
  opened_at            TIMESTAMPTZ,
  sent_at              TIMESTAMPTZ
);

-- ============================================================================
-- 10. TASKS, FOLLOW-UPS & CALENDAR
-- ============================================================================

-- A "follow-up" (FR-063/064) IS a task with task_type = FOLLOW_UP. This keeps
-- one entity instead of two, while task_reschedule_history satisfies the
-- explicit "reschedule history is retained" requirement.
CREATE TABLE tasks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id         UUID REFERENCES leads(id) ON DELETE CASCADE,
  crm_company_id  UUID REFERENCES crm_companies(id),
  crm_person_id   UUID REFERENCES crm_people(id),
  task_type       task_type_enum NOT NULL DEFAULT 'GENERAL',
  assigned_to     UUID REFERENCES users(id),
  created_by      UUID REFERENCES users(id),
  title           VARCHAR(255) NOT NULL,
  description     TEXT,
  priority        lead_priority_enum NOT NULL DEFAULT 'MEDIUM',
  status          task_status_enum NOT NULL DEFAULT 'PENDING',
  due_at          TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_tasks_assignee_due ON tasks (assigned_to, due_at) WHERE status = 'PENDING';
CREATE INDEX ix_tasks_lead ON tasks (lead_id);
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE task_reschedule_history (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id           UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  previous_due_at   TIMESTAMPTZ,
  new_due_at        TIMESTAMPTZ NOT NULL,
  rescheduled_by    UUID REFERENCES users(id),
  reason            TEXT,
  rescheduled_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_task_reschedule_task ON task_reschedule_history (task_id);

CREATE TABLE calendar_events (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id        UUID REFERENCES leads(id) ON DELETE CASCADE,
  user_id        UUID NOT NULL REFERENCES users(id),
  linked_task_id UUID REFERENCES tasks(id),
  title          VARCHAR(255) NOT NULL,
  description    TEXT,
  starts_at      TIMESTAMPTZ NOT NULL,
  ends_at        TIMESTAMPTZ,
  location       TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_calendar_events_user_time ON calendar_events (user_id, starts_at);
CREATE TRIGGER trg_calendar_events_updated_at BEFORE UPDATE ON calendar_events
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE notifications (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id             UUID NOT NULL REFERENCES users(id),
  channel             notification_channel_enum NOT NULL,
  title               VARCHAR(255) NOT NULL,
  body                TEXT,
  related_entity_type VARCHAR(50),
  related_entity_id   UUID,
  status              notification_status_enum NOT NULL DEFAULT 'PENDING',
  scheduled_for       TIMESTAMPTZ,
  sent_at             TIMESTAMPTZ,
  read_at             TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_notifications_user_status ON notifications (user_id, status);

-- ============================================================================
-- 11. RADAR (audit + anomaly scoring) & GOVERNANCE
-- ============================================================================

-- High-volume, append-only. Recommend RANGE partitioning by occurred_at once
-- volume justifies it (see doc §7) — created here as a plain table for MVP.
CREATE TABLE radar_events (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  actor_user_id  UUID NOT NULL REFERENCES users(id),
  action         radar_action_enum NOT NULL,
  entity_type    VARCHAR(50) NOT NULL,
  entity_id      UUID NOT NULL,
  ip_address     INET,
  user_agent     TEXT,
  metadata       JSONB,
  occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_radar_events_actor_time ON radar_events (tenant_id, actor_user_id, occurred_at);
CREATE INDEX ix_radar_events_entity ON radar_events (entity_type, entity_id);

CREATE TABLE radar_alert_rules (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                UUID REFERENCES tenants(id) ON DELETE CASCADE,   -- NULL = platform default template
  rule_type                VARCHAR(100) NOT NULL,   -- BULK_CONTACT_VIEW / OFF_HOURS_ACCESS / EXPORT_ATTEMPT / ...
  threshold_count          INTEGER,
  threshold_window_minutes INTEGER,
  config                   JSONB NOT NULL DEFAULT '{}',
  is_active                BOOLEAN NOT NULL DEFAULT true,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_radar_rules_updated_at BEFORE UPDATE ON radar_alert_rules
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE radar_alerts (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  rule_id          UUID REFERENCES radar_alert_rules(id),
  actor_user_id    UUID REFERENCES users(id),
  status           radar_alert_status_enum NOT NULL DEFAULT 'OPEN',
  summary          TEXT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  acknowledged_by  UUID REFERENCES users(id),
  acknowledged_at  TIMESTAMPTZ
);
CREATE INDEX ix_radar_alerts_tenant_status ON radar_alerts (tenant_id, status);

CREATE TABLE radar_alert_events (
  alert_id  UUID NOT NULL REFERENCES radar_alerts(id) ON DELETE CASCADE,
  event_id  UUID NOT NULL REFERENCES radar_events(id) ON DELETE CASCADE,
  PRIMARY KEY (alert_id, event_id)
);

-- General system audit trail — distinct from radar_events (NFR-14 requires both).
CREATE TABLE audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id     UUID REFERENCES users(id),
  action      VARCHAR(100) NOT NULL,
  entity_type VARCHAR(100) NOT NULL,
  entity_id   UUID,
  old_values  JSONB,
  new_values  JSONB,
  ip_address  INET,
  user_agent  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id);

-- Outbox pattern for async processing (BullMQ workers, webhooks, future AI hooks).
CREATE TABLE domain_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID REFERENCES tenants(id) ON DELETE CASCADE,
  event_type      VARCHAR(150) NOT NULL,
  aggregate_type  VARCHAR(100) NOT NULL,
  aggregate_id    UUID NOT NULL,
  payload         JSONB NOT NULL,
  status          VARCHAR(30) NOT NULL DEFAULT 'PENDING',
  retry_count     INTEGER NOT NULL DEFAULT 0,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at    TIMESTAMPTZ
);
CREATE INDEX ix_domain_events_pending ON domain_events (status, occurred_at) WHERE status = 'PENDING';

-- ============================================================================
-- 12. AI / MCP-READY LAYER (Phase 2 — schema reserved now, not built out yet)
-- ============================================================================

CREATE TABLE ai_runs (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id        UUID REFERENCES users(id),
  run_type       VARCHAR(100) NOT NULL,
  entity_type    VARCHAR(50),
  entity_id      UUID,
  model          VARCHAR(150),
  provider       VARCHAR(100),
  input_tokens   INTEGER,
  output_tokens  INTEGER,
  latency_ms     INTEGER,
  status         VARCHAR(30),
  input_data     JSONB,
  output_data    JSONB,
  error_message  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_insights (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  entity_type   VARCHAR(50) NOT NULL,
  entity_id     UUID NOT NULL,
  insight_type  VARCHAR(100) NOT NULL,
  title         VARCHAR(255),
  content       TEXT,
  score         NUMERIC(5,2),
  confidence    NUMERIC(5,2),
  model         VARCHAR(150),
  metadata      JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ
);
CREATE INDEX ix_ai_insights_entity ON ai_insights (entity_type, entity_id);

COMMIT;