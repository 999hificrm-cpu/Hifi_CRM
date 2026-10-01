import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization
from app.core.security import get_password_hash
import uuid

def seed_production():
    db: Session = SessionLocal()
    try:
        # Check if users already exist to prevent duplicate seed error
        if db.query(User).first():
            print("Database already contains users. Skipping seed.")
            return

        print("Seeding initial production data...")

        # 1. Create an Organization
        org_id = str(uuid.uuid4())
        org = Organization(
            id=org_id,
            name="Acme Corp Production",
            slug="acmeprod",
            status="ACTIVE"
        )
        db.add(org)
        db.commit()

        # 2. Super Admin
        super_admin = User(
            id=str(uuid.uuid4()),
            email="superadmin@jarvis.com",
            full_name="Super Admin",
            password_hash=get_password_hash("admin123"),
            platform_role="SUPER_ADMIN",
            status="ACTIVE"
        )
        db.add(super_admin)

        # 3. Data Entry User
        data_entry = User(
            id=str(uuid.uuid4()),
            email="dataentry@jarvis.com",
            full_name="Global Data Entry",
            password_hash=get_password_hash("admin123"),
            platform_role="DATA_ENTRY",
            status="ACTIVE"
        )
        db.add(data_entry)

        # 4. Org Admin
        org_admin = User(
            id=str(uuid.uuid4()),
            email="orgadmin@jarvis.com",
            full_name="Acme Org Admin",
            password_hash=get_password_hash("admin123"),
            organization_id=org_id,
            tenant_role="ORG_ADMIN",
            status="ACTIVE"
        )
        db.add(org_admin)

        # 5. Telecaller
        telecaller = User(
            id=str(uuid.uuid4()),
            email="telecaller@jarvis.com",
            full_name="Acme Telecaller",
            password_hash=get_password_hash("admin123"),
            organization_id=org_id,
            tenant_role="TELECALLER",
            status="ACTIVE"
        )
        db.add(telecaller)

        db.commit()
        print("Seed completed successfully! You can login with 'admin123'")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_production()
