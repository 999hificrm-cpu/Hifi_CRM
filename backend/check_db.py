from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.tenant_schema import sync_all_tenant_schemas
engine = create_engine('postgresql+psycopg2://postgres:Lokesh@localhost:5432/jarvis_crm')
SessionLocal = sessionmaker(bind=engine)
with SessionLocal() as db:
    res = sync_all_tenant_schemas(db)
    print("Synced schemas:", res)
