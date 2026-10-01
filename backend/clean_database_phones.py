import re
from sqlalchemy import text
from app.core.database import SessionLocal

def normalize_to_10_digits(val: str) -> str:
    if not val:
        return val
    s = str(val).strip()
    if "*" in s:
        # Preserve masking, but strip leading +91 or 91 if present
        clean = re.sub(r"^\+?91[\s\-]*", "", s)
        return clean.strip()

    # Extract digits only
    digits = re.sub(r"\D", "", s)
    if not digits:
        return s

    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    if len(digits) > 10:
        return digits[-10:]
    return digits

db = SessionLocal()

print("=" * 70)
print("MIGRATING & STANDARDIZING ALL PHONE NUMBERS TO 10 DIGITS")
print("=" * 70)

schemas = [r[0] for r in db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog');")).fetchall()]

total_updated = 0

for schema in schemas:
    # 1. Update leads table if exists
    has_leads = db.execute(text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='{schema}' AND table_name='leads')")).scalar()
    if has_leads:
        rows = db.execute(text(f"SELECT id, contact_phone FROM \"{schema}\".leads WHERE contact_phone IS NOT NULL")).fetchall()
        for r_id, raw_p in rows:
            clean_p = normalize_to_10_digits(raw_p)
            if clean_p != raw_p:
                db.execute(text(f"UPDATE \"{schema}\".leads SET contact_phone = :p WHERE id = :id"), {"p": clean_p, "id": r_id})
                total_updated += 1

    # 2. Update contacts table if exists
    has_contacts = db.execute(text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='{schema}' AND table_name='contacts')")).scalar()
    if has_contacts:
        rows = db.execute(text(f"SELECT id, phone FROM \"{schema}\".contacts WHERE phone IS NOT NULL")).fetchall()
        for r_id, raw_p in rows:
            clean_p = normalize_to_10_digits(raw_p)
            if clean_p != raw_p:
                db.execute(text(f"UPDATE \"{schema}\".contacts SET phone = :p WHERE id = :id"), {"p": clean_p, "id": r_id})
                total_updated += 1

# Update public global tables
for tbl, col in [("global_companies", "phone"), ("global_contacts", "phone"), ("global_people", "phone"), ("users", "phone")]:
    has_tbl = db.execute(text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='{tbl}')")).scalar()
    if has_tbl:
        rows = db.execute(text(f"SELECT id, \"{col}\" FROM public.\"{tbl}\" WHERE \"{col}\" IS NOT NULL")).fetchall()
        for r_id, raw_p in rows:
            clean_p = normalize_to_10_digits(raw_p)
            if clean_p != raw_p:
                db.execute(text(f"UPDATE public.\"{tbl}\" SET \"{col}\" = :p WHERE id = :id"), {"p": clean_p, "id": r_id})
                total_updated += 1

db.commit()
print(f"[SUCCESS] Standardized {total_updated} phone numbers to 10-digit Indian format across all schemas!")

# Verification: Print sample phone numbers from apex_industrial_solutions and public
print("\nSample leads in 'apex_industrial_solutions':")
samples = db.execute(text("SELECT title, contact_phone FROM apex_industrial_solutions.leads WHERE contact_phone IS NOT NULL LIMIT 8")).fetchall()
for s in samples:
    print(f"  {s[0]} -> {s[1]}")

db.close()
