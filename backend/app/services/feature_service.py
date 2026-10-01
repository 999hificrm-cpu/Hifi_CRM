from typing import Optional
from sqlalchemy.orm import Session
from app.models.organization import Organization, Plan, Subscription

def is_feature_enabled(db: Session, organization_id: str, feature_name: str) -> bool:
    """
    Evaluates whether a specific feature is enabled for an organization.
    Resolution Order:
    1. Organization-level overrides (if explicitly defined)
    2. Plan-level feature flags (default fallback)
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        return False
        
    # Check org-level overrides first
    if org.feature_overrides and feature_name in org.feature_overrides:
        return org.feature_overrides.get(feature_name, False)
        
    # Fallback to Plan-level rules via active subscription
    sub = db.query(Subscription).filter(Subscription.organization_id == organization_id).first()
    if not sub:
        return False
        
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    if not plan or not plan.feature_flags:
        return False
        
    return plan.feature_flags.get(feature_name, False)

def set_feature_override(db: Session, organization_id: str, feature_name: str, enabled: bool) -> Organization:
    """
    Super Admin action: Force a feature to be explicitly enabled or disabled for a tenant,
    regardless of their current subscription plan.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise ValueError("Organization not found")
        
    overrides = org.feature_overrides or {}
    overrides[feature_name] = enabled
    org.feature_overrides = overrides
    
    db.commit()
    db.refresh(org)
    return org
