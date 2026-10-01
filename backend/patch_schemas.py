import os
from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()

def fix():
    # Get all tenant schemas
    res = db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog') AND schema_name NOT LIKE 'pg_toast%'")).fetchall()
    schemas = [r[0] for r in res]
    
    missing_tables = [
        "attendance_sessions", "break_sessions", "daily_call_plans",
        "daily_tasks", "dedupe_candidates", "communication_logs",
        "availability_status", "leave_requests"
    ]
    
    for schema in schemas:
        print(f"Fixing schema: {schema}")
        
        # 1. Create missing tables
        for tbl in missing_tables:
            try:
                db.execute(text(f'CREATE TABLE IF NOT EXISTS "{schema}"."{tbl}" (LIKE "public"."{tbl}" INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)'))
            except Exception as e:
                print(f"Error creating {tbl} in {schema}: {e}")
                db.rollback()
        
        # 2. Add columns to leads
        try:
            db.execute(text(f'ALTER TABLE "{schema}".leads ADD COLUMN IF NOT EXISTS lead_type VARCHAR(50)'))
            db.execute(text(f'ALTER TABLE "{schema}".leads ADD COLUMN IF NOT EXISTS segment VARCHAR(10)'))
        except Exception as e:
            print(f"Error altering leads in {schema}: {e}")
            db.rollback()
            
        # 3. Add columns to pipelines
        try:
            db.execute(text(f'ALTER TABLE "{schema}".pipelines ADD COLUMN IF NOT EXISTS segment VARCHAR(10)'))
        except Exception as e:
            print(f"Error altering pipelines in {schema}: {e}")
            db.rollback()
            
        db.commit()

fix()
print("Done!")
