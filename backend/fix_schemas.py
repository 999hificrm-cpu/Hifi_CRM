import os
from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()

def fix():
    # Get all tenant schemas
    res = db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog') AND schema_name NOT LIKE 'pg_toast%'")).fetchall()
    schemas = [r[0] for r in res]
    
    missing_tables = [
        "contact_phones", "radar_events", "templates", "payments",
        "call_records", "telecaller_targets", "followup_policies",
        "absence_delegations", "eod_reports", "telecaller_sessions",
        "ai_insights", "ai_runs", "masking_exceptions"
    ]
    
    for schema in schemas:
        print(f"Fixing schema: {schema}")
        for tbl in missing_tables:
            try:
                db.execute(text(f'CREATE TABLE IF NOT EXISTS "{schema}"."{tbl}" (LIKE "public"."{tbl}" INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)'))
            except Exception as e:
                print(f"Error creating {tbl} in {schema}: {e}")
        db.commit()

fix()
print("Done!")
