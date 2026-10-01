from sqlalchemy.orm import sessionmaker, declarative_base, Session
import sqlalchemy.exc as sa_exc
from sqlalchemy.pool import StaticPool
import logging
from sqlalchemy import create_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connect args depending on sqlite vs postgres
connect_args = {}
poolclass = None

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if ":memory:" in settings.DATABASE_URL:
        poolclass = StaticPool

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    poolclass=poolclass,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

# Universal safety net for multi-tenant schema connection pooling:
# Automatically reset search_path to public on pool checkout to avoid tenant bleed across requests
from sqlalchemy import event, text

if not settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET search_path TO public")
            cursor.close()
        except Exception:
            pass

    @event.listens_for(Session, "after_begin")
    def receive_after_begin(session, transaction, connection):
        tenant_schema = getattr(session, "tenant_schema", None)
        if tenant_schema:
            connection.execute(text(f'SET search_path TO "{tenant_schema}", public'))

import sqlalchemy.orm.exc as orm_exc

_orig_session_refresh = Session.refresh

def _safe_session_refresh(self, instance, *args, **kwargs):
    try:
        return _orig_session_refresh(self, instance, *args, **kwargs)
    except (orm_exc.ObjectDeletedError, sa_exc.InvalidRequestError, Exception) as exc:
        logger.debug(f"db.refresh safely bypassed for {instance}: {exc}")
        try:
            self.expunge(instance)
        except Exception:
            pass
        return None

Session.refresh = _safe_session_refresh

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
