import pytest
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.organization import Organization, Plan, Subscription
from app.models.user import User
from app.core.security import get_password_hash, create_access_token
from app.services.organization_service import create_organization
from app.schemas.organization import OrganizationCreate

TEST_DB_FILE = "./test_jarvis_crm.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def superadmin_token(db_session):
    admin = db_session.query(User).filter(User.email == "superadmin@jarvis.local").first()
    if not admin:
        admin = User(
            email="superadmin@jarvis.local",
            full_name="Super Admin",
            platform_role="SUPER_ADMIN",
            password_hash=get_password_hash("password123"),
            status="ACTIVE"
        )
        db_session.add(admin)
        db_session.commit()
    return create_access_token(admin.id)


@pytest.fixture
def tenant_a_fixture(db_session):
    plan = db_session.query(Plan).filter(Plan.code == "GROWTH").first()
    if not plan:
        plan = Plan(code="GROWTH", name="Growth", seat_limit=15, monthly_pull_quota=5000)
        db_session.add(plan)
        db_session.commit()

    org = db_session.query(Organization).filter(Organization.slug == "test-tenant-a").first()
    if not org:
        org = create_organization(
            db=db_session,
            data=OrganizationCreate(
                name="Tenant Alpha",
                slug="test-tenant-a",
                admin_name="Alpha Admin",
                admin_email="admin@alpha.com",
                admin_password="Password@123",
                plan_code="GROWTH"
            )
        )

    # Add Telecaller user
    tc = db_session.query(User).filter(User.email == "telecaller@alpha.com").first()
    if not tc:
        tc = User(
            organization_id=org.id,
            tenant_role="TELECALLER",
            full_name="Alpha Telecaller",
            email="telecaller@alpha.com",
            password_hash=get_password_hash("Password@123"),
            status="ACTIVE"
        )
        db_session.add(tc)
        db_session.commit()

    admin_user = db_session.query(User).filter(User.email == "admin@alpha.com").first()
    return {
        "org": org,
        "admin_user": admin_user,
        "admin_token": create_access_token(admin_user.id),
        "telecaller_user": tc,
        "telecaller_token": create_access_token(tc.id)
    }


@pytest.fixture
def tenant_b_fixture(db_session):
    org = db_session.query(Organization).filter(Organization.slug == "test-tenant-b").first()
    if not org:
        org = create_organization(
            db=db_session,
            data=OrganizationCreate(
                name="Tenant Beta",
                slug="test-tenant-b",
                admin_name="Beta Admin",
                admin_email="admin@beta.com",
                admin_password="Password@123",
                plan_code="GROWTH"
            )
        )
    admin_user = db_session.query(User).filter(User.email == "admin@beta.com").first()
    return {
        "org": org,
        "admin_user": admin_user,
        "admin_token": create_access_token(admin_user.id)
    }
