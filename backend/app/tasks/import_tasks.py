from celery import shared_task
from app.core.database import SessionLocal
from app.services.import_service import execute_import_job

@shared_task(bind=True, max_retries=3)
def run_import_job(self, job_id: str):
    db = SessionLocal()
    try:
        execute_import_job(db, job_id)
    except Exception as exc:
        db.rollback()
        # Mark as failed in DB
        # Then retry
        self.retry(exc=exc, countdown=60)
    finally:
        db.close()
