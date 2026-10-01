from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
try:
    res_public = db.execute(text('SELECT count(*) FROM public.import_jobs')).scalar()
    print('public.import_jobs count:', res_public)
except Exception as e:
    print('public.import_jobs error:', e)

schemas = db.execute(text('SELECT schema_name FROM organizations WHERE schema_name IS NOT NULL')).scalars().all()
for s in schemas:
    try:
        cnt = db.execute(text(f'SELECT count(*) FROM "{s}".import_jobs')).scalar()
        print(f'{s}.import_jobs count:', cnt)
    except Exception as e:
        print(f'{s}.import_jobs error:', e)
db.close()
