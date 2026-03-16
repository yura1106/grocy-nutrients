from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "purpose": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | Any) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "purpose": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_password_reset_token(user_id: int, hashed_password: str) -> str:
    """Create a reset token signed with SECRET_KEY + password hash fragment.
    Changing the password invalidates the token automatically."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "password_reset"}
    secret = settings.SECRET_KEY + hashed_password[:16]
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def verify_password_reset_token(token: str, hashed_password: str) -> int | None:
    """Verify reset token. Returns user_id or None."""
    secret = settings.SECRET_KEY + hashed_password[:16]
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("purpose") != "password_reset":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (JWTError, ValueError):
        return None


def verify_refresh_token(token: str) -> int | None:
    """Verify refresh token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("purpose") != "refresh":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (JWTError, ValueError):
        return None


def create_account_deletion_token(user_id: int, hashed_password: str) -> str:
    """Create an account deletion token signed with SECRET_KEY + password hash fragment.
    Changing the password invalidates the token automatically."""
    expire = datetime.now(UTC) + timedelta(hours=24)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "account_deletion"}
    secret = settings.SECRET_KEY + hashed_password[:16]
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def verify_account_deletion_token(token: str, hashed_password: str) -> int | None:
    """Verify account deletion token. Returns user_id or None."""
    secret = settings.SECRET_KEY + hashed_password[:16]
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("purpose") != "account_deletion":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (JWTError, ValueError):
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
