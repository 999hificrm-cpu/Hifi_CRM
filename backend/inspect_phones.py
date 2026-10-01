from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
schemas = [r[0] for r in db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog');")).fetchall()]

print("Inspecting phone numbers in database...")
for s in schemas:
    has_leads = db.execute(text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='{s}' AND table_name='leads')")).scalar()
    if has_leads:
        res = db.execute(text(f"SELECT id, title, contact_phone FROM \"{s}\".leads WHERE contact_phone IS NOT NULL LIMIT 5;")).fetchall()
        print(f"\nSchema {s} leads sample phones:")
        for r in res:
            print(f"  {r[1]} -> '{r[2]}'")

# Also check global_companies and global_people in public
has_gc = db.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='global_companies')")).scalar()
if has_gc:
    res = db.execute(text("SELECT legal_name, phone FROM public.global_companies WHERE phone IS NOT NULL LIMIT 5;")).fetchall()
    print("\nGlobal Companies sample phones:")
    for r in res:
        print(f"  {r[0]} -> '{r[1]}'")

db.close()
