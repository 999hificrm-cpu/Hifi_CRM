from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from passlib.context import CryptContext
import jwt
from app.core.config import settings

# Use pbkdf2_sha256 with fallback to bcrypt for cross-platform zero-dependency reliability
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    token_version: int = 1,
    extra_claims: Optional[dict] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "token_version": token_version
    }
    if extra_claims:
        to_encode.update(extra_claims)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_support_token(
    actor_user_id: str,
    organization_id: str,
    support_session_id: str,
    target_user_id: Optional[str] = None,
    expires_minutes: int = 15
) -> str:
    """Creates a short-lived cryptographically signed support token (Problems #19, #20, #46)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    sub_id = target_user_id or actor_user_id
    payload = {
        "exp": expire,
        "sub": str(sub_id),
        "type": "support_session",
        "context_type": "SUPPORT_CONTEXT",
        "support_session_id": support_session_id,
        "actor_user_id": actor_user_id,
        "target_user_id": target_user_id,
        "organization_id": organization_id
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

