from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.organization import Organization, Plan, Subscription
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStage
from app.models.masking import MaskingPolicy
from app.models.audit import AuditLog
from app.core.security import get_password_hash
from app.core.tenant_schema import get_schema_name_for_org, create_tenant_schema_tables
from app.schemas.organization import OrganizationCreate
import re


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:100]


DEFAULT_PIPELINE_STAGES = [
    {"name": "New", "code": "NEW", "order_index": 0, "color": "#3b82f6", "win_probability": 10.0, "is_won": False, "is_lost": False},
    {"name": "Contacted", "code": "CONTACTED", "order_index": 1, "color": "#8b5cf6", "win_probability": 25.0, "is_won": False, "is_lost": False},
    {"name": "Interested", "code": "INTERESTED", "order_index": 2, "color": "#06b6d4", "win_probability": 50.0, "is_won": False, "is_lost": False},
    {"name": "Meeting Scheduled", "code": "MEETING", "order_index": 3, "color": "#eab308", "win_probability": 70.0, "is_won": False, "is_lost": False},
    {"name": "Proposal Sent", "code": "PROPOSAL", "order_index": 4, "color": "#f97316", "win_probability": 85.0, "is_won": False, "is_lost": False},
    {"name": "Won", "code": "WON", "order_index": 5, "color": "#22c55e", "win_probability": 100.0, "is_won": True, "is_lost": False},
    {"name": "Lost", "code": "LOST", "order_index": 6, "color": "#ef4444", "win_probability": 0.0, "is_won": False, "is_lost": True},
]


def create_organization(db: Session, data: OrganizationCreate, creator_id: str = None) -> Organization:
    # 1. Generate unique slug
    base_slug = data.slug or slugify(data.name)
    slug = base_slug
    counter = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # 2. Check if admin email is already used for an active admin
    existing_user = db.query(User).filter(User.email == data.admin_email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.admin_email} already exists"
        )

    # 3. Create Organization with isolated schema_name
    schema_name = get_schema_name_for_org(data.name)
    org = Organization(
        name=data.name,
        slug=slug,
        schema_name=schema_name,
        timezone=data.timezone or "Asia/Kolkata",
        currency=data.currency or "INR",
        status="ACTIVE",
        settings={
            "owner_name": data.owner_name,
            "industry": data.industry,
            "cin": data.cin,
            "registration_number": data.registration_number,
            "gst_number": data.gst_number,
            "address": data.address,
            "city": data.city,
            "pincode": data.pincode,
            "state": data.state,
            "contact_number": data.contact_number,
            "contact_email": data.contact_email,
            "website": data.website,
            "company_type": data.company_type,
        }
    )
    db.add(org)
    db.flush()

    # Create isolated PostgreSQL schema and tenant-specific tables
    create_tenant_schema_tables(db, schema_name, org.id)

    # 4. Find or create plan and subscription
    target_plan_code = (data.plan_code or "GROWTH").upper()
    plan = db.query(Plan).filter(Plan.code == target_plan_code).first()
    if not plan:
        plan = db.query(Plan).filter(Plan.code == "GROWTH").first()
    if not plan:
        plan = Plan(
            code=target_plan_code,
            name=f"{target_plan_code.capitalize()} Plan",
            seat_limit=15,
            monthly_pull_quota=5000,
            price_amount=4999.00
        )
        db.add(plan)
        db.flush()

    subscription = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        status="ACTIVE",
        seats_purchased=plan.seat_limit,
        pull_quota_monthly=plan.monthly_pull_quota,
        pull_quota_used=0
    )
    db.add(subscription)

    # 5. Create initial Organization Admin User
    admin_user = User(
        organization_id=org.id,
        tenant_role="ORG_ADMIN",
        full_name=data.admin_name,
        email=data.admin_email.lower().strip(),
        phone=data.admin_phone,
        password_hash=get_password_hash(data.admin_password),
        status="ACTIVE"
    )
    db.add(admin_user)
    db.flush()

    # 6. Initialize default Sales Pipeline & canonical stages atomically
    default_pipeline = Pipeline(
        organization_id=org.id,
        name="Standard Sales Pipeline",
        description="Default organization sales pipeline",
        is_default=True,
        status="ACTIVE"
    )
    db.add(default_pipeline)
    db.flush()

    for stage_data in DEFAULT_PIPELINE_STAGES:
        stage = PipelineStage(
            pipeline_id=default_pipeline.id,
            name=stage_data["name"],
            code=stage_data["code"],
            order_index=stage_data["order_index"],
            color=stage_data["color"],
            win_probability=stage_data["win_probability"],
            is_won=stage_data["is_won"],
            is_lost=stage_data["is_lost"]
        )
        db.add(stage)

    # 7. Initialize default data masking policy for Telecallers
    telecaller_phone_mask = MaskingPolicy(
        organization_id=org.id,
        tenant_role="TELECALLER",
        field="PHONE",
        is_masked=True
    )
    telecaller_email_mask = MaskingPolicy(
        organization_id=org.id,
        tenant_role="TELECALLER",
        field="EMAIL",
        is_masked=True
    )
    db.add(telecaller_phone_mask)
    db.add(telecaller_email_mask)

    # 8. Record audit log
    audit = AuditLog(
        organization_id=org.id,
        user_id=creator_id or admin_user.id,
        action="ORGANIZATION_CREATED",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        new_values={"name": org.name, "slug": org.slug, "admin_email": admin_user.email}
    )
    db.add(audit)

    db.commit()
    try:
        db.refresh(org)
    except Exception:
        pass
    return org
