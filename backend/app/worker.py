from celery import Celery
import os
from app.core.config import settings
from celery.signals import task_prerun, task_postrun, task_failure
from app.core.database import SessionLocal
from app.models.jobs import JobRun
from datetime import datetime, timezone
import traceback

# Configure Celery
# If REDIS_URL isn't set, default to a local redis for dev
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "jarvis_worker",
    broker=redis_url,
    backend=redis_url,
    include=['app.tasks.import_tasks', 'app.tasks.daily_tasks', 'app.tasks.billing_tasks']
)

from celery.schedules import crontab

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=100,
    beat_schedule={
        'initialize-daily-targets-midnight': {
            'task': 'app.tasks.daily_tasks.initialize_daily_targets',
            'schedule': crontab(hour=0, minute=0), # runs daily at midnight UTC
        },
        'dynamic-cleanup-and-deduplication': {
            'task': 'app.tasks.daily_tasks.dynamic_cleanup_and_deduplication',
            'schedule': crontab(hour=2, minute=0), # runs at 2 AM
        },
        'generate-eod-reports': {
            'task': 'app.tasks.daily_tasks.generate_eod_reports',
            'schedule': crontab(hour=23, minute=30), # runs at 11:30 PM
        },
        'subscription-monitor': {
            'task': 'tasks.billing.subscription_monitor',
            'schedule': crontab(hour=1, minute=0), # runs daily at 1:00 AM
        },
        'billing-reconciliation': {
            'task': 'tasks.billing.billing_reconciliation',
            'schedule': crontab(hour=3, minute=0), # runs daily at 3:00 AM
        }
    }
)

if __name__ == "__main__":
    celery_app.start()

# Job Tracking Signals
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **other):
    db = SessionLocal()
    try:
        job = JobRun(
            job_id=task_id,
            job_type=task.name,
            status="STARTED",
            started_at=datetime.now(timezone.utc)
        )
        db.add(job)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, retval=None, state=None, **other):
    if state == "FAILURE":
        return # Handled by task_failure
    db = SessionLocal()
    try:
        job = db.query(JobRun).filter(JobRun.job_id == task_id).first()
        if job:
            job.status = state
            job.completed_at = datetime.now(timezone.utc)
            if job.started_at:
                job.duration_seconds = int((job.completed_at - job.started_at).total_seconds())
            db.commit()
    except Exception:
        pass
    finally:
        db.close()

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback_obj=None, **other):
    db = SessionLocal()
    try:
        job = db.query(JobRun).filter(JobRun.job_id == task_id).first()
        if job:
            job.status = "FAILED"
            job.completed_at = datetime.now(timezone.utc)
            if job.started_at:
                job.duration_seconds = int((job.completed_at - job.started_at).total_seconds())
            job.error_message = str(exception)
            # Use Python's built-in traceback formatting
            tb_str = "".join(traceback.format_exception(type(exception), exception, traceback_obj))
            job.error_traceback = tb_str
            db.commit()
    except Exception:
        pass
    finally:
        db.close()
