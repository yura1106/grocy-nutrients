import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


def create_access_token(
    subject: str | Any,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "purpose": "access",
        "ver": token_version,
        "jti": secrets.token_urlsafe(16),
    }
    return str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM))


def create_refresh_token(subject: str | Any, token_version: int) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "purpose": "refresh",
        "ver": token_version,
        "jti": secrets.token_urlsafe(16),
    }
    return str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM))


def create_password_reset_token(user_id: int, hashed_password: str) -> str:
    """Create a reset token signed with SECRET_KEY + password hash fragment.
    Changing the password invalidates the token automatically."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "password_reset"}
    secret = settings.SECRET_KEY + hashed_password[:16]
    return str(jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM))


def verify_password_reset_token(token: str, hashed_password: str) -> int | None:
    """Verify reset token. Returns user_id or None."""
    secret = settings.SECRET_KEY + hashed_password[:16]
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("purpose") != "password_reset":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (jwt.PyJWTError, ValueError):
        return None


def verify_refresh_token(token: str) -> int | None:
    """Verify refresh token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("purpose") != "refresh":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (jwt.PyJWTError, ValueError):
        return None


def create_account_deletion_token(user_id: int, hashed_password: str) -> str:
    """Create an account deletion token signed with SECRET_KEY + password hash fragment.
    Changing the password invalidates the token automatically."""
    expire = datetime.now(UTC) + timedelta(hours=24)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "account_deletion"}
    secret = settings.SECRET_KEY + hashed_password[:16]
    return str(jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM))


def verify_account_deletion_token(token: str, hashed_password: str) -> int | None:
    """Verify account deletion token. Returns user_id or None."""
    secret = settings.SECRET_KEY + hashed_password[:16]
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("purpose") != "account_deletion":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (jwt.PyJWTError, ValueError):
        return None


def blacklist_token(token: str) -> None:
    """Add a token to the Redis blacklist until it expires.

    Fail-closed: if Redis is unavailable, raise 503 — the caller cannot guarantee
    revocation, so the operation must not silently succeed.
    """
    try:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            exp = payload.get("exp")
            ttl = (
                int(exp - datetime.now(UTC).timestamp())
                if exp
                else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        except jwt.PyJWTError:
            ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        if ttl > 0:
            get_redis().setex(f"blacklist:{token}", ttl, "1")
    except RedisError as e:
        logger.error("Redis unavailable during blacklist_token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable",
        ) from e


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted.

    Fail-closed: if Redis is unavailable, raise 503 — we cannot confirm the
    token is NOT revoked, so we refuse the request rather than risk accepting
    a revoked token.
    """
    try:
        return bool(get_redis().exists(f"blacklist:{token}"))
    except RedisError as e:
        logger.error("Redis unavailable during is_token_blacklisted: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable",
        ) from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")
