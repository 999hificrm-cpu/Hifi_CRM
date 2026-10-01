from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_super_admin, get_current_user
from app.models.organization import Organization, Subscription, Plan
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationOut, SubscriptionOut, PlanOut, SubscriptionChangePlan, SubscriptionChangeStatus
from app.services.organization_service import create_organization

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/", response_model=List[OrganizationOut])
def list_organizations(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin)
):
    query = db.query(Organization)
    if search:
        query = query.filter(
            (Organization.name.ilike(f"%{search}%")) |
            (Organization.slug.ilike(f"%{search}%"))
        )
    return query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_new_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin)
):
    return create_organization(db=db, data=data, creator_id=admin.id)


@router.get("/plans", response_model=List[PlanOut])
def list_available_plans(db: Session = Depends(get_db)):
    return db.query(Plan).filter(Plan.is_active == True).all()


@router.get("/{id}", response_model=OrganizationOut)
def get_organization_detail(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Tenant Admin can only view their own organization, Super Admin can view any
    if not current_user.is_super_admin and current_user.organization_id != id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("/{id}", response_model=OrganizationOut)
def update_organization(
    id: str,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_super_admin and current_user.organization_id != id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if data.name:
        org.name = data.name.strip()
    if data.timezone:
        org.timezone = data.timezone
    if data.currency:
        org.currency = data.currency
    if data.status and current_user.is_super_admin:
        org.status = data.status
    if data.settings:
        current_settings = dict(org.settings or {})
        current_settings.update(data.settings)
        org.settings = current_settings

    db.commit()
    try:
        db.refresh(org)
    except Exception:
        pass
    return org


@router.get("/{id}/subscription", response_model=SubscriptionOut)
def get_organization_subscription(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_super_admin and current_user.organization_id != id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    sub = db.query(Subscription).filter(Subscription.organization_id == id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return sub


@router.post("/{id}/subscription/change-plan", response_model=SubscriptionOut)
def change_organization_plan(
    id: str,
    data: SubscriptionChangePlan,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Super Admins can upgrade or downgrade an organization's plan."""
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    sub = db.query(Subscription).filter(Subscription.organization_id == id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    new_plan = db.query(Plan).filter(Plan.code == data.plan_code.upper()).first()
    if not new_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    sub.plan_id = new_plan.id
    sub.seats_purchased = new_plan.seat_limit
    sub.pull_quota_monthly = new_plan.monthly_pull_quota
    # User said "keep it simple" - no pro-ration or quota resets right now, just change limits

    db.commit()
    db.refresh(sub)
    return sub


@router.post("/{id}/subscription/status", response_model=SubscriptionOut)
def update_subscription_status(
    id: str,
    data: SubscriptionChangeStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Super Admins can change subscription status (e.g. to PAST_DUE for grace period handling)"""
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    sub = db.query(Subscription).filter(Subscription.organization_id == id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    sub.status = data.status.upper()
    db.commit()
    db.refresh(sub)
    return sub
