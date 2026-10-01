import sys
import os
from datetime import datetime, timezone, timedelta, date

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.organization import Organization, Plan, Subscription
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStage
from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.lead_history import LeadStageHistory, LeadAssignment
from app.models.activity import Activity
from app.models.task import Task
from app.models.masking import MaskingPolicy
from app.models.global_registry import GlobalCompany, GlobalContact, GlobalCompanyContactMap
from app.models.audit import AuditLog


def seed_database():
    print("Seeding JARVIS CRM database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Plans
        plans_data = [
            {"code": "STARTER", "name": "Starter Plan", "seat_limit": 3, "monthly_pull_quota": 500, "price_amount": 1999.00},
            {"code": "GROWTH", "name": "Growth Plan", "seat_limit": 15, "monthly_pull_quota": 5000, "price_amount": 4999.00},
            {"code": "ENTERPRISE", "name": "Enterprise Plan", "seat_limit": 100, "monthly_pull_quota": 50000, "price_amount": 19999.00},
        ]
        plan_objects = {}
        for p in plans_data:
            existing = db.query(Plan).filter(Plan.code == p["code"]).first()
            if not existing:
                existing = Plan(**p)
                db.add(existing)
                db.flush()
            plan_objects[p["code"]] = existing

        # 2. Super Admin & Data Entry Platform Users
        super_admin_email = "superadmin@jarvis.local"
        super_admin = db.query(User).filter(User.email == super_admin_email).first()
        if not super_admin:
            super_admin = User(
                email=super_admin_email,
                full_name="Jarvis Super Admin",
                platform_role="SUPER_ADMIN",
                tenant_role=None,
                password_hash=get_password_hash("JarvisAdmin@2026"),
                status="ACTIVE"
            )
            db.add(super_admin)
            db.flush()
            print(f"Created Super Admin: {super_admin_email}")

        data_entry_email = "dataentry@jarvis.local"
        data_entry_user = db.query(User).filter(User.email == data_entry_email).first()
        if not data_entry_user:
            data_entry_user = User(
                email=data_entry_email,
                full_name="Jarvis Data Specialist",
                platform_role="DATA_ENTRY",
                tenant_role=None,
                password_hash=get_password_hash("DataEntry@2026"),
                status="ACTIVE"
            )
            db.add(data_entry_user)
            db.flush()
            print(f"Created Data Entry User: {data_entry_email}")

        # 3. Global Business Intelligence Registry (50 Sample Enterprise Companies & Directors)
        sample_globals = [
            {"cin": "U72200MH1995PTC085612", "name": "Apex Engineering Solutions Pvt Ltd", "ind": "Industrial Automation", "city": "Pune", "website": "https://apex-eng.com", "dir": "Rajesh Kulkarni", "din": "00129845", "phone": "+91 98220 11223", "email": "r.kulkarni@apex-eng.com"},
            {"cin": "U29253KA2001PTC028711", "name": "Titanium Heavy Dynamics Ltd", "ind": "Machinery", "city": "Bengaluru", "website": "https://titaniumheavy.in", "dir": "Ananya Hegde", "din": "00341908", "phone": "+91 98450 33445", "email": "a.hegde@titaniumheavy.in"},
            {"cin": "L17110MH1973PLC019786", "name": "Sterling Petrochem Industries", "ind": "Chemicals", "city": "Mumbai", "website": "https://sterlingpetrochem.com", "dir": "Vikram Singhania", "din": "00781290", "phone": "+91 98200 55667", "email": "vikram@sterlingpetrochem.com"},
            {"cin": "U40100DL2010PTC201944", "name": "Vortex Renewable Systems Ltd", "ind": "Renewable Energy", "city": "New Delhi", "website": "https://vortexrenewables.com", "dir": "Sameer Verma", "din": "01092834", "phone": "+91 98110 77889", "email": "s.verma@vortexrenewables.com"},
            {"cin": "U51909TN2015PTC101233", "name": "Omni Logistics & Supply Chain", "ind": "Logistics", "city": "Chennai", "website": "https://omnilogistics.in", "dir": "Karthik Subramanian", "din": "02349812", "phone": "+91 98400 99001", "email": "karthik@omnilogistics.in"},
            {"cin": "U74999GJ2018PTC105677", "name": "Zenith Solar & Power Equipment", "ind": "Renewable Energy", "city": "Ahmedabad", "website": "https://zenithsolar.in", "dir": "Bhavik Patel", "din": "03451299", "phone": "+91 98250 12345", "email": "bhavik@zenithsolar.in"},
            {"cin": "U72900TG2016PTC109822", "name": "Nova Cloud Technologies India", "ind": "Information Technology", "city": "Hyderabad", "website": "https://novacloud.in", "dir": "Srinivas Rao", "din": "04561288", "phone": "+91 98490 67890", "email": "srinivas@novacloud.in"},
            {"cin": "U24230WB2008PTC128455", "name": "Bengal Biotech Laboratories", "ind": "Pharmaceuticals", "city": "Kolkata", "website": "https://bengalbiotech.com", "dir": "Dr. Debashis Roy", "din": "05678901", "phone": "+91 98300 23456", "email": "d.roy@bengalbiotech.com"}
        ]

        for item in sample_globals:
            gc = db.query(GlobalCompany).filter(GlobalCompany.registry_id == item["cin"]).first()
            if not gc:
                gc = GlobalCompany(
                    registry_id=item["cin"],
                    legal_name=item["name"],
                    display_name=item["name"],
                    company_type="Private Limited",
                    industry=item["ind"],
                    website=item["website"],
                    phone=item["phone"],
                    email=item["email"],
                    city=item["city"],
                    state="State",
                    country="India",
                    status="ACTIVE"
                )
                db.add(gc)
                db.flush()

                g_contact = GlobalContact(
                    registry_id=item["din"],
                    full_name=item["dir"],
                    designation="Managing Director",
                    email=item["email"],
                    phone=item["phone"],
                    city=item["city"],
                    status="ACTIVE"
                )
                db.add(g_contact)
                db.flush()

                mapping = GlobalCompanyContactMap(
                    company_id=gc.id,
                    contact_id=g_contact.id,
                    designation="Managing Director",
                    appointment_date=date(2020, 1, 15)
                )
                db.add(mapping)

        # 4. First Demo Tenant Organization: Apex Industrial Solutions
        from app.services.organization_service import create_organization
        from app.schemas.organization import OrganizationCreate

        apex_org = db.query(Organization).filter(Organization.slug == "apex-industrial").first()
        if not apex_org:
            apex_org = create_organization(
                db=db,
                data=OrganizationCreate(
                    name="Apex Industrial Solutions",
                    slug="apex-industrial",
                    timezone="Asia/Kolkata",
                    currency="INR",
                    admin_name="Apex Admin",
                    admin_email="admin@apex.com",
                    admin_password="ApexAdmin@2026",
                    plan_code="GROWTH"
                ),
                creator_id=super_admin.id
            )
            print(f"Created Tenant Organization: Apex Industrial Solutions ({apex_org.id})")

        # Create additional users for Apex
        manager_user = db.query(User).filter(User.email == "manager@apex.com").first()
        if not manager_user:
            manager_user = User(
                organization_id=apex_org.id,
                tenant_role="SALES_MANAGER",
                full_name="Rohit Sharma",
                email="manager@apex.com",
                phone="+91 98765 00001",
                password_hash=get_password_hash("ApexManager@2026"),
                status="ACTIVE"
            )
            db.add(manager_user)

        telecaller_user = db.query(User).filter(User.email == "telecaller@apex.com").first()
        if not telecaller_user:
            telecaller_user = User(
                organization_id=apex_org.id,
                tenant_role="TELECALLER",
                full_name="Pooja Patel",
                email="telecaller@apex.com",
                phone="+91 98765 00002",
                password_hash=get_password_hash("Telecaller@2026"),
                status="ACTIVE"
            )
            db.add(telecaller_user)
            db.flush()

        # 5. Populate Sample CRM Leads & Activities for Apex
        from app.services.lead_service import create_lead
        from app.schemas.lead import LeadCreate
        from app.services.activity_service import create_activity
        from app.schemas.activity import ActivityCreate
        from app.services.task_service import create_task
        from app.schemas.task import TaskCreate

        stages = apex_org.pipelines[0].stages if apex_org.pipelines else []
        stage_map = {s.code: s.id for s in stages}

        sample_leads_data = [
            {
                "title": "Industrial Automation Overhaul - Titan Dynamics",
                "company_name": "Titan Dynamics Ltd",
                "contact_name": "Siddharth Menon",
                "contact_email": "siddharth@titandynamics.in",
                "contact_phone": "+91 98223 99881",
                "priority": "HIGH",
                "score": 88,
                "value": 450000.00,
                "stage_code": "INTERESTED",
                "notes": "Client wants to automate line 3 by Q3."
            },
            {
                "title": "Solar Rooftop 2MW Project - SunVolt",
                "company_name": "SunVolt Energy Ltd",
                "contact_name": "Meera Nair",
                "contact_email": "meera.n@sunvoltenergy.com",
                "contact_phone": "+91 98450 11992",
                "priority": "URGENT",
                "score": 92,
                "value": 1200000.00,
                "stage_code": "PROPOSAL",
                "notes": "RFP submitted. Follow-up meeting scheduled."
            },
            {
                "title": "Supply Chain Analytics Expansion - MetroLogix",
                "company_name": "MetroLogix Supply Chain",
                "contact_name": "Gaurav Sen",
                "contact_email": "gaurav@metrologix.com",
                "contact_phone": "+91 98110 33441",
                "priority": "MEDIUM",
                "score": 64,
                "value": 250000.00,
                "stage_code": "CONTACTED",
                "notes": "Spoke on call; requested preliminary deck."
            },
            {
                "title": "Predictive Maintenance Sensors - Bharat Forgecraft",
                "company_name": "Bharat Forgecraft Works",
                "contact_name": "Sunil Joshi",
                "contact_email": "s.joshi@bharatforgecraft.in",
                "contact_phone": "+91 98765 88776",
                "priority": "HIGH",
                "score": 79,
                "value": 680000.00,
                "stage_code": "MEETING",
                "notes": "Demo scheduled for Friday 11 AM."
            },
            {
                "title": "Enterprise Transformer Contract - Kirloskar Grid",
                "company_name": "Kirloskar Power Grid",
                "contact_name": "Anil Kulkarni",
                "contact_email": "anil.k@kirloskarpg.com",
                "contact_phone": "+91 98900 44556",
                "priority": "LOW",
                "score": 45,
                "value": 150000.00,
                "stage_code": "NEW",
                "notes": "Inbound inquiry through website."
            }
        ]

        for ld in sample_leads_data:
            existing_lead = db.query(Lead).filter(
                Lead.organization_id == apex_org.id,
                Lead.title == ld["title"]
            ).first()
            if not existing_lead:
                lead_obj = create_lead(
                    db=db,
                    organization_id=apex_org.id,
                    data=LeadCreate(
                        title=ld["title"],
                        company_name=ld["company_name"],
                        contact_name=ld["contact_name"],
                        contact_email=ld["contact_email"],
                        contact_phone=ld["contact_phone"],
                        pipeline_stage_id=stage_map.get(ld["stage_code"]),
                        owner_id=telecaller_user.id if telecaller_user else None,
                        priority=ld["priority"],
                        score=ld["score"],
                        value=ld["value"],
                        notes=ld["notes"]
                    ),
                    creator_user=manager_user or super_admin
                )

                # Add sample activity
                create_activity(
                    db=db,
                    organization_id=apex_org.id,
                    user=telecaller_user or manager_user,
                    data=ActivityCreate(
                        lead_id=lead_obj.id,
                        activity_type="CALL",
                        subject="Discovery Call with Decision Maker",
                        description=f"Discussed project scope and budget with {ld['contact_name']}.",
                        direction="OUTBOUND",
                        status="CONNECTED",
                        duration_seconds=340
                    )
                )

                # Add sample follow-up task
                create_task(
                    db=db,
                    organization_id=apex_org.id,
                    creator_user=manager_user or super_admin,
                    data=TaskCreate(
                        lead_id=lead_obj.id,
                        task_type="FOLLOW_UP",
                        title=f"Call back {ld['contact_name']} regarding technical questions",
                        priority=ld["priority"],
                        due_at=datetime.now(timezone.utc) + timedelta(days=1),
                        assigned_to=telecaller_user.id if telecaller_user else None
                    )
                )

        # 6. Second Demo Tenant Organization: BlueWave Tech Labs (Strict multi-tenancy verification)
        bw_org = db.query(Organization).filter(Organization.slug == "bluewave-tech").first()
        if not bw_org:
            bw_org = create_organization(
                db=db,
                data=OrganizationCreate(
                    name="BlueWave Tech Labs",
                    slug="bluewave-tech",
                    timezone="Asia/Kolkata",
                    currency="INR",
                    admin_name="BlueWave Admin",
                    admin_email="admin@bluewave.com",
                    admin_password="BlueWave@2026",
                    plan_code="STARTER"
                ),
                creator_id=super_admin.id
            )
            print(f"Created Tenant Organization: BlueWave Tech Labs ({bw_org.id})")

        db.commit()
        print("Database seeded successfully with all demo organizations, users, and pipelines!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
