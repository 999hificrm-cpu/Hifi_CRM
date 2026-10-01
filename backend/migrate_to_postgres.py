import json
import sqlite3
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text, inspect, Boolean, DateTime, JSON, Integer, Float
from app.models import Base

SQLITE_PATH = Path(__file__).resolve().parent / "jarvis_crm.db"
POSTGRES_URL = "postgresql+psycopg://postgres:Lokesh@localhost:5432/jarvis_crm"

def migrate():
    print("=" * 60)
    print("JARVIS CRM: SQLite to PostgreSQL Complete Data Migration")
    print(f"Source SQLite: {SQLITE_PATH}")
    print(f"Target Postgres: {POSTGRES_URL}")
    print("=" * 60)

    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"Source database not found: {SQLITE_PATH}")

    # 1. Create target Postgres engine
    pg_engine = create_engine(POSTGRES_URL, future=True)
    
    print("\n[Step 1/4] Creating all tables in PostgreSQL from SQLAlchemy metadata...")
    with pg_engine.connect() as init_conn:
        init_conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))
        init_conn.execute(text("SET search_path TO public;"))
        init_conn.commit()

    Base.metadata.create_all(bind=pg_engine)
    print("Schema created successfully!")

    # 2. Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # 3. Transfer data table by table
    print("\n[Step 2/4] Migrating table data...")
    total_migrated_rows = 0

    with pg_engine.connect() as pg_conn:
        # Disable foreign key triggers for seamless bulk insertion
        try:
            pg_conn.execute(text("SET session_replication_role = 'replica';"))
            pg_conn.commit()
            print("Set PostgreSQL session_replication_role to 'replica' for safe insertion.")
        except Exception as e:
            print(f"Notice (session_replication_role): {e}")

        for table in Base.metadata.sorted_tables:
            table_name = table.name
            
            # Fetch all rows from SQLite
            sqlite_cur.execute(f'SELECT * FROM "{table_name}"')
            rows = sqlite_cur.fetchall()
            row_count = len(rows)
            
            if row_count == 0:
                print(f"  -> Table '{table_name}': 0 rows (skipped)")
                continue

            # Clear any existing rows in target table to prevent duplicates
            pg_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))
            pg_conn.commit()

            # Column type mapping from SQLAlchemy table definition
            col_types = {col.name: col.type for col in table.columns}

            processed_rows = []
            for row in rows:
                row_dict = dict(row)
                cleaned_row = {}
                for col_name, val in row_dict.items():
                    if col_name not in col_types:
                        continue
                    
                    col_type = col_types[col_name]
                    if val is None:
                        cleaned_row[col_name] = None
                    elif isinstance(col_type, Boolean):
                        cleaned_row[col_name] = bool(val)
                    elif isinstance(col_type, JSON):
                        if isinstance(val, str):
                            try:
                                cleaned_row[col_name] = json.loads(val)
                            except Exception:
                                cleaned_row[col_name] = val
                        else:
                            cleaned_row[col_name] = val
                    elif isinstance(col_type, DateTime):
                        if isinstance(val, str):
                            try:
                                # SQLite stores datetime as ISO format strings
                                cleaned_row[col_name] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            except Exception:
                                cleaned_row[col_name] = val
                        else:
                            cleaned_row[col_name] = val
                    elif isinstance(col_type, Integer):
                        try:
                            cleaned_row[col_name] = int(val)
                        except Exception:
                            cleaned_row[col_name] = val
                    elif isinstance(col_type, Float):
                        try:
                            cleaned_row[col_name] = float(val)
                        except Exception:
                            cleaned_row[col_name] = val
                    else:
                        cleaned_row[col_name] = val
                processed_rows.append(cleaned_row)

            # Bulk insert into PostgreSQL
            # Insert in chunks of 500 for optimal performance
            chunk_size = 500
            for i in range(0, len(processed_rows), chunk_size):
                chunk = processed_rows[i:i + chunk_size]
                pg_conn.execute(table.insert(), chunk)
            pg_conn.commit()

            total_migrated_rows += row_count
            print(f"  [OK] Table '{table_name}': {row_count} rows migrated.")

        # Re-enable foreign key constraints
        try:
            pg_conn.execute(text("SET session_replication_role = 'origin';"))
            pg_conn.commit()
            print("Restored PostgreSQL session_replication_role to 'origin'.")
        except Exception as e:
            print(f"Notice restoring session_replication_role: {e}")

    sqlite_conn.close()

    # 4. Verification Step: Compare row counts across all tables
    print("\n[Step 3/4] Verifying row counts between SQLite and PostgreSQL...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    all_matched = True
    with pg_engine.connect() as pg_conn:
        for table in Base.metadata.sorted_tables:
            table_name = table.name
            sqlite_cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            sql_count = sqlite_cur.fetchone()[0]

            res = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            pg_count = res.scalar()

            status = "MATCH" if sql_count == pg_count else "MISMATCH"
            if sql_count != pg_count:
                all_matched = False
                print(f"  [!] {table_name}: SQLite={sql_count}, Postgres={pg_count} -> {status}")
            else:
                print(f"  [OK] {table_name:<26}: {pg_count} rows ({status})")

    sqlite_conn.close()

    if not all_matched:
        raise RuntimeError("Migration verification failed: Some table counts did not match!")

    print(f"\n[Step 4/4] Migration Successful! Total rows preserved: {total_migrated_rows}")
    print("=" * 60)

if __name__ == "__main__":
    migrate()
