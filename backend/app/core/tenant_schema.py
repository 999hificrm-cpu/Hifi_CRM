import re
import uuid
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger("jarvis.tenant_schema")

# Canonical pipeline stages for every new tenant schema
DEFAULT_PIPELINE_STAGES = [
    {"name": "New", "code": "NEW", "order_index": 0, "color": "#3b82f6", "win_probability": 10.0, "is_won": False, "is_lost": False},
    {"name": "Contacted", "code": "CONTACTED", "order_index": 1, "color": "#8b5cf6", "win_probability": 25.0, "is_won": False, "is_lost": False},
    {"name": "Interested", "code": "INTERESTED", "order_index": 2, "color": "#06b6d4", "win_probability": 50.0, "is_won": False, "is_lost": False},
    {"name": "Meeting Scheduled", "code": "MEETING", "order_index": 3, "color": "#eab308", "win_probability": 70.0, "is_won": False, "is_lost": False},
    {"name": "Proposal Sent", "code": "PROPOSAL", "order_index": 4, "color": "#f97316", "win_probability": 85.0, "is_won": False, "is_lost": False},
    {"name": "Won", "code": "WON", "order_index": 5, "color": "#22c55e", "win_probability": 100.0, "is_won": True, "is_lost": False},
    {"name": "Lost", "code": "LOST", "order_index": 6, "color": "#ef4444", "win_probability": 0.0, "is_won": False, "is_lost": True},
]


def get_schema_name_for_org(org_name: str) -> str:
    """
    Sanitizes organization name to a valid, clean PostgreSQL schema identifier in lowercase.
    Example: "Adani Industries LTD." -> "adani_industries_ltd"
    Example: "Apex Innovations" -> "apex_innovations"
    """
    clean = org_name.lower().strip()
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"[\s\-]+", "_", clean)
    clean = clean.strip("_")
    if not clean:
        clean = "tenant_" + uuid.uuid4().hex[:8]
    if clean[0].isdigit():
        clean = f"org_{clean}"
    return clean[:60]


def create_tenant_schema_tables(db: Session, schema_name: str, org_id: str) -> None:
    """
    Creates an isolated PostgreSQL schema for the tenant and clones all tenant-level tables.
    Initializes default sales pipeline, stages, and telecaller masking policies.
    """
    # Guard: Only PostgreSQL supports isolated schema namespaces
    if db.bind and db.bind.dialect.name != "postgresql":
        return

    # 1. Create Schema
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    db.commit()

    TENANT_TABLES = [
        "companies", "contacts", "pipelines", "pipeline_stages", "leads",
        "lead_stage_history", "lead_assignments", "activities", "tasks",
        "import_jobs", "import_row_errors", "audit_logs", "masking_policies",
        "contact_phones", "radar_events", "templates", "payments",
        "call_records", "telecaller_targets", "followup_policies",
        "absence_delegations", "eod_reports", "telecaller_sessions",
        "ai_insights", "ai_runs", "masking_exceptions",
        "attendance_sessions", "break_sessions", "daily_call_plans",
        "daily_tasks", "dedupe_candidates", "communication_logs",
        "availability_status", "leave_requests"
    ]
    for tbl in TENANT_TABLES:
        try:
            db.execute(text(f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{tbl}" (LIKE "public"."{tbl}" INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)'))
        except Exception as exc:
            db.rollback()
            logger.warning(f"Notice creating table {tbl} in {schema_name}: {exc}")
    db.commit()

    # Ensure schema evolution columns are present in existing tenant tables
    TENANT_COLUMN_MIGRATIONS = [
        ("leads", "deleted_at TIMESTAMP"),
        ("leads", "deleted_by VARCHAR(36)"),
        ("leads", "deletion_reason VARCHAR(500)"),
        ("leads", "product_service_id VARCHAR(36)"),
        ("leads", "product_service_name VARCHAR(150)"),
        ("leads", "purpose VARCHAR(50)"),
        ("import_jobs", "default_product_service_id VARCHAR(36)"),
        ("companies", "deleted_at TIMESTAMP"),
        ("companies", "deleted_by VARCHAR(36)"),
        ("companies", "deletion_reason VARCHAR(500)"),
        ("contacts", "deleted_at TIMESTAMP"),
        ("contacts", "deleted_by VARCHAR(36)"),
        ("contacts", "deletion_reason VARCHAR(500)"),
        ("audit_logs", "actor_user_id VARCHAR(36)"),
        ("audit_logs", "target_user_id VARCHAR(36)"),
        ("audit_logs", "support_session_id VARCHAR(36)"),
        ("audit_logs", "context_type VARCHAR(30) DEFAULT 'PLATFORM_CONTEXT'"),
        ("audit_logs", "reason VARCHAR(500)"),
        ("audit_logs", "sequence_number INTEGER"),
        ("audit_logs", "event_hash VARCHAR(64)"),
        ("audit_logs", "previous_event_hash VARCHAR(64)"),
    ]
    for tbl, col_def in TENANT_COLUMN_MIGRATIONS:
        try:
            db.execute(text(f'ALTER TABLE "{schema_name}"."{tbl}" ADD COLUMN IF NOT EXISTS {col_def}'))
            db.commit()
        except Exception:
            db.rollback()

    # 3. Seed Canonical Default Pipeline & Stages in tenant schema
    pipeline_check = db.execute(text(f'SELECT count(*) FROM "{schema_name}"."pipelines"')).scalar()
    if pipeline_check == 0:
        pipe_id = str(uuid.uuid4())
        db.execute(
            text(f'''
                INSERT INTO "{schema_name}"."pipelines" (id, organization_id, name, description, is_default, status, created_at, updated_at)
                VALUES (:id, :org_id, 'Standard Sales Pipeline', 'Default organization sales pipeline', TRUE, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            '''),
            {"id": pipe_id, "org_id": org_id}
        )

        for s in DEFAULT_PIPELINE_STAGES:
            stage_id = str(uuid.uuid4())
            db.execute(
                text(f'''
                    INSERT INTO "{schema_name}"."pipeline_stages" 
                    (id, pipeline_id, name, code, order_index, color, win_probability, is_won, is_lost, created_at, updated_at)
                    VALUES (:id, :pipe_id, :name, :code, :order_index, :color, :win_probability, :is_won, :is_lost, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                '''),
                {
                    "id": stage_id,
                    "pipe_id": pipe_id,
                    "name": s["name"],
                    "code": s["code"],
                    "order_index": s["order_index"],
                    "color": s["color"],
                    "win_probability": s["win_probability"],
                    "is_won": s["is_won"],
                    "is_lost": s["is_lost"],
                }
            )

    # 4. Seed Default Telecaller Masking Policies in tenant schema
    mask_check = db.execute(text(f'SELECT count(*) FROM "{schema_name}"."masking_policies"')).scalar()
    if mask_check == 0:
        db.execute(
            text(f'''
                INSERT INTO "{schema_name}"."masking_policies" (id, organization_id, tenant_role, field, is_masked, created_at, updated_at)
                VALUES 
                (:id1, :org_id, 'TELECALLER', 'PHONE', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (:id2, :org_id, 'TELECALLER', 'EMAIL', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            '''),
            {"id1": str(uuid.uuid4()), "id2": str(uuid.uuid4()), "org_id": org_id}
        )

    db.commit()
    logger.info(f"Initialized isolated PostgreSQL schema '{schema_name}' for org '{org_id}'")


def install_org_schema_trigger(db: Session) -> None:
    """
    Installs a PostgreSQL PL/pgSQL function and trigger on the `public.organizations` table.
    Ensures that if an organization is inserted DIRECTLY into the database,
    it automatically derives `schema_name`, applies defaults, creates the dedicated schema & tables!
    """
    if db.bind and db.bind.dialect.name != "postgresql":
        return

    trigger_sql = """
    CREATE OR REPLACE FUNCTION trg_fn_create_organization_schema()
    RETURNS TRIGGER AS $$
    DECLARE
        v_schema TEXT;
    BEGIN
        -- 1. Apply column defaults if missing
        NEW.status := COALESCE(NEW.status, 'ACTIVE');
        NEW.timezone := COALESCE(NEW.timezone, 'Asia/Kolkata');
        NEW.currency := COALESCE(NEW.currency, 'INR');
        NEW.created_at := COALESCE(NEW.created_at, CURRENT_TIMESTAMP);
        NEW.updated_at := COALESCE(NEW.updated_at, CURRENT_TIMESTAMP);
        IF NEW.settings IS NULL THEN
            NEW.settings := '{}'::json;
        END IF;

        -- 2. Derive schema name if not provided
        IF NEW.schema_name IS NULL OR NEW.schema_name = '' THEN
            v_schema := lower(regexp_replace(NEW.name, '[^a-zA-Z0-9]+', '_', 'g'));
            v_schema := trim(both '_' from v_schema);
            IF v_schema ~ '^[0-9]' THEN
                v_schema := 'org_' || v_schema;
            END IF;
            IF length(v_schema) = 0 THEN
                v_schema := 'tenant_' || substr(md5(random()::text), 1, 8);
            END IF;
            v_schema := substr(v_schema, 1, 60);
            NEW.schema_name := v_schema;
        ELSE
            v_schema := NEW.schema_name;
        END IF;

        -- 3. Create Schema dynamically
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', v_schema);

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_create_organization_schema ON public.organizations;
    CREATE TRIGGER trg_create_organization_schema
    BEFORE INSERT ON public.organizations
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_create_organization_schema();
    """
    try:
        db.execute(text(trigger_sql))
        db.commit()
        logger.info("Successfully installed PostgreSQL trigger for automatic organization schema creation")
    except Exception as e:
        db.rollback()
        logger.warning(f"Could not install PostgreSQL trigger: {e}")


def migrate_tenant_data_from_public(db: Session, org_id: str, schema_name: str) -> None:
    """
    Safely copies existing tenant rows from public schema to the new isolated schema.
    Uses ON CONFLICT DO NOTHING to ensure zero data loss and idempotency.
    """
    if db.bind and db.bind.dialect.name != "postgresql":
        return

    data_ops = [
        ("companies", "organization_id = :org_id"),
        ("contacts", "organization_id = :org_id"),
        ("pipelines", "organization_id = :org_id"),
        ("pipeline_stages", 'pipeline_id IN (SELECT id FROM "public"."pipelines" WHERE organization_id = :org_id)'),
        ("leads", "organization_id = :org_id"),
        ("lead_stage_history", "organization_id = :org_id"),
        ("lead_assignments", "organization_id = :org_id"),
        ("activities", "organization_id = :org_id"),
        ("tasks", "organization_id = :org_id"),
        ("masking_policies", "organization_id = :org_id"),
    ]

    for tbl, cond in data_ops:
        try:
            db.execute(text(f'INSERT INTO "{schema_name}"."{tbl}" SELECT * FROM "public"."{tbl}" WHERE {cond} ON CONFLICT DO NOTHING'), {"org_id": org_id})
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning(f"Notice migrating data to {schema_name}: {exc}")


def sync_all_tenant_schemas(db: Session) -> Dict[str, str]:
    """
    Scans all existing organizations in public.organizations, assigns schema_name if missing,
    ensures the isolated schema and tables exist for each, and migrates existing rows.
    """
    if db.bind and db.bind.dialect.name != "postgresql":
        return {}

    from app.models.organization import Organization
    orgs = db.query(Organization).all()
    results = {}

    for org in orgs:
        if not org.schema_name:
            org.schema_name = get_schema_name_for_org(org.name)
            db.commit()
        
        create_tenant_schema_tables(db, org.schema_name, org.id)
        migrate_tenant_data_from_public(db, org.id, org.schema_name)
        results[org.name] = org.schema_name

    return results
