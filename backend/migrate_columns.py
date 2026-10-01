import sqlite3
from pathlib import Path

db_path = Path("jarvis_crm.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(global_companies)")
    cols = [r[1] for r in cur.fetchall()]
    for col in ["address", "cin", "registration_number", "gst_number"]:
        if col not in cols:
            cur.execute(f"ALTER TABLE global_companies ADD COLUMN {col} VARCHAR(500)")
            print(f"Added {col} to global_companies")

    cur.execute("PRAGMA table_info(global_people)")
    pcols = [r[1] for r in cur.fetchall()]
    if "associated_companies" not in pcols:
        cur.execute("ALTER TABLE global_people ADD COLUMN associated_companies JSON DEFAULT '[]'")
        print("Added associated_companies to global_people")

    conn.commit()
    conn.close()
    print("Database migration successfully finished!")
