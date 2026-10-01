from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.deps import get_db
from app.core.config import settings
import redis
import os

router = APIRouter(tags=["Health & System Diagnostics"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    # 1. Check Database
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
        
    # 2. Check Redis
    redis_ok = False
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
        
    # 3. Overall Status
    system_status = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": system_status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "error",
        "redis_broker": "connected" if redis_ok else "error",
        "storage": settings.STORAGE_PROVIDER
    }
