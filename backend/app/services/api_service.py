import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from app.models.api_management import ApiKey

def generate_api_key() -> Tuple[str, str, str]:
    """
    Generates a secure API key.
    Returns: (raw_key, key_prefix, key_hash)
    Raw key MUST NOT be stored in DB.
    """
    random_bytes = secrets.token_hex(32)
    raw_key = f"jarvis_sk_{random_bytes}"
    key_prefix = raw_key[:16] # e.g. jarvis_sk_abcd1234
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    return raw_key, key_prefix, key_hash

def create_api_key(
    db: Session, 
    organization_id: str, 
    name: str, 
    user_id: Optional[str] = None, 
    scopes: List[str] = None, 
    expires_in_days: int = 365
) -> str:
    raw_key, key_prefix, key_hash = generate_api_key()
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days) if expires_in_days else None
    
    api_key = ApiKey(
        organization_id=organization_id,
        user_id=user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes or [],
        expires_at=expires_at
    )
    
    db.add(api_key)
    db.commit()
    
    return raw_key

def verify_api_key(db: Session, raw_key: str) -> Optional[ApiKey]:
    if not raw_key.startswith("jarvis_sk_"):
        return None
        
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:16]
    
    api_key = db.query(ApiKey).filter(
        ApiKey.key_prefix == key_prefix,
        ApiKey.key_hash == key_hash,
        ApiKey.status == "ACTIVE"
    ).first()
    
    if not api_key:
        return None
        
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        api_key.status = "EXPIRED"
        db.commit()
        return None
        
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key
