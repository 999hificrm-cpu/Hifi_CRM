from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.followup_policy import FollowupPolicy
from app.schemas.followup_policy import FollowupPolicyCreate, FollowupPolicyUpdate, FollowupPolicyOut

router = APIRouter(prefix="/followup-policies", tags=["Followup Policies"])

def _check_admin(user: User):
    if user.tenant_role not in ["ORG_ADMIN", "SALES_MANAGER"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only ORG Admins and Sales Managers can manage follow-up policies")

@router.get("/", response_model=List[FollowupPolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    policies = db.query(FollowupPolicy).filter(FollowupPolicy.organization_id == tenant_id).all()
    return policies

@router.post("/", response_model=FollowupPolicyOut)
def create_policy(
    policy_in: FollowupPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    _check_admin(current_user)
    
    new_policy = FollowupPolicy(
        id=str(uuid.uuid4()),
        organization_id=tenant_id,
        name=policy_in.name,
        trigger_outcome=policy_in.trigger_outcome,
        max_attempts=policy_in.max_attempts,
        interval_minutes=policy_in.interval_minutes,
        is_active=policy_in.is_active
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.patch("/{policy_id}", response_model=FollowupPolicyOut)
def update_policy(
    policy_id: str,
    policy_in: FollowupPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    _check_admin(current_user)
    
    policy = db.query(FollowupPolicy).filter(
        FollowupPolicy.id == policy_id, 
        FollowupPolicy.organization_id == tenant_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        
    for field, value in policy_in.dict(exclude_unset=True).items():
        setattr(policy, field, value)
        
    db.commit()
    db.refresh(policy)
    return policy

@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    _check_admin(current_user)
    
    policy = db.query(FollowupPolicy).filter(
        FollowupPolicy.id == policy_id, 
        FollowupPolicy.organization_id == tenant_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        
    db.delete(policy)
    db.commit()
