import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from app.models import Base

# Connection Strings
# The local database as defined in .env
LOCAL_PG_URL = "postgresql+psycopg://postgres:Lokesh@localhost:5432/jarvis_crm"
SUPABASE_URL = "postgresql+psycopg://postgres.jfqcnrmohilxkuibkqml:Knowletive%40123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

def migrate():
    print("=" * 60)
    print("JARVIS CRM: Local PostgreSQL to Supabase Complete Data Migration")
    print(f"Source Postgres: {LOCAL_PG_URL}")
    print(f"Target Supabase: {SUPABASE_URL}")
    print("=" * 60)

    # 1. Create source and target engines
    print("[Step 1/4] Connecting to databases...")
    try:
        source_engine = create_engine(LOCAL_PG_URL, future=True)
        # Test connection
        with source_engine.connect() as conn:
            pass
    except Exception as e:
        print("Connection failed with psycopg, falling back to psycopg2...")
        LOCAL_PG_URL_FALLBACK = LOCAL_PG_URL.replace("postgresql+psycopg://", "postgresql+psycopg2://")
        SUPABASE_URL_FALLBACK = SUPABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg2://")
        source_engine = create_engine(LOCAL_PG_URL_FALLBACK, future=True)
        target_engine = create_engine(SUPABASE_URL_FALLBACK, future=True)
    else:
        target_engine = create_engine(SUPABASE_URL, future=True)

    # Validate target engine connection
    try:
        with target_engine.connect() as conn:
            pass
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        print("\n[!] IMPORTANT: Supabase direct connections (db.*.supabase.co) require IPv6 support.")
        print("If you are seeing a 'failed to resolve host' or 'getaddrinfo failed' error,")
        print("your network likely doesn't support IPv6. Please go to your Supabase Dashboard -> Settings -> Database")
        print("and copy the 'Connection pooling' URL (which supports IPv4) instead of the Direct connection URL.")
        print("Update the SUPABASE_URL in this script and try again.")
        return

    print("\n[Step 2/4] Creating all tables in Supabase from SQLAlchemy metadata...")
    with target_engine.connect() as init_conn:
        init_conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))
        init_conn.execute(text("SET search_path TO public;"))
        init_conn.commit()

    # Create all tables according to the local schema
    Base.metadata.create_all(bind=target_engine)
    print("Schema created successfully in Supabase!")

    # 3. Transfer data table by table
    print("\n[Step 3/4] Migrating table data...")
    total_migrated_rows = 0

    with target_engine.connect() as pg_conn:
        # Disable foreign key triggers for seamless bulk insertion on Supabase
        try:
            pg_conn.execute(text("SET session_replication_role = 'replica';"))
            pg_conn.commit()
            print("Set Supabase PostgreSQL session_replication_role to 'replica' for safe insertion.")
        except Exception as e:
            print(f"Notice (session_replication_role): {e}")

        with source_engine.connect() as source_conn:
            for table in Base.metadata.sorted_tables:
                table_name = table.name
                
                # Fetch all rows from Source PostgreSQL
                stmt = select(table)
                res = source_conn.execute(stmt)
                rows = res.mappings().all()
                row_count = len(rows)
                
                if row_count == 0:
                    print(f"  -> Table '{table_name}': 0 rows (skipped)")
                    continue

                # Clear any existing rows in target table to prevent duplicates
                pg_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))
                pg_conn.commit()

                # Process rows to plain dictionaries
                processed_rows = [dict(row) for row in rows]

                # Bulk insert into Supabase
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
            print("Restored Supabase PostgreSQL session_replication_role to 'origin'.")
        except Exception as e:
            print(f"Notice restoring session_replication_role: {e}")

    # 4. Verification Step: Compare row counts across all tables
    print("\n[Step 4/4] Verifying row counts between Local and Supabase...")
    all_matched = True
    with target_engine.connect() as pg_conn:
        with source_engine.connect() as source_conn:
            for table in Base.metadata.sorted_tables:
                table_name = table.name
                source_count = source_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                target_count = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()

                status = "MATCH" if source_count == target_count else "MISMATCH"
                if source_count != target_count:
                    all_matched = False
                    print(f"  [!] {table_name}: Local={source_count}, Supabase={target_count} -> {status}")
                else:
                    print(f"  [OK] {table_name:<26}: {target_count} rows ({status})")

    if not all_matched:
        print("\nWarning: Some table counts did not match! Migration might be incomplete.")
    else:
        print(f"\nMigration Successful! Total rows preserved: {total_migrated_rows}")
    print("=" * 60)

if __name__ == "__main__":
    migrate()
