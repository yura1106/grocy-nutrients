import hashlib
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
    return str(
        jwt.encode(
            to_encode, settings.APP_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM
        )
    )


def create_refresh_token(subject: str | Any, token_version: int) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "purpose": "refresh",
        "ver": token_version,
        "jti": secrets.token_urlsafe(16),
    }
    return str(
        jwt.encode(
            to_encode, settings.APP_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM
        )
    )


def create_password_reset_token(user_id: int, hashed_password: str) -> str:
    """Create a reset token signed with APP_SECRET_KEY + password hash fragment.
    Changing the password invalidates the token automatically."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "password_reset"}
    secret = settings.APP_SECRET_KEY.get_secret_value() + hashed_password[:16]
    return str(jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM))


def verify_password_reset_token(token: str, hashed_password: str) -> int | None:
    """Verify reset token. Returns user_id or None."""
    secret = settings.APP_SECRET_KEY.get_secret_value() + hashed_password[:16]
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
        payload = jwt.decode(
            token,
            settings.APP_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("purpose") != "refresh":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (jwt.PyJWTError, ValueError):
        return None


def create_account_deletion_token(user_id: int, hashed_password: str) -> str:
    """Create an account deletion token signed with APP_SECRET_KEY + password hash fragment.
    Changing the password invalidates the token automatically."""
    expire = datetime.now(UTC) + timedelta(hours=24)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "account_deletion"}
    secret = settings.APP_SECRET_KEY.get_secret_value() + hashed_password[:16]
    return str(jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM))


def verify_account_deletion_token(token: str, hashed_password: str) -> int | None:
    """Verify account deletion token. Returns user_id or None."""
    secret = settings.APP_SECRET_KEY.get_secret_value() + hashed_password[:16]
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
            payload = jwt.decode(
                token,
                settings.APP_SECRET_KEY.get_secret_value(),
                algorithms=[settings.JWT_ALGORITHM],
            )
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


# --- API keys (long-lived tokens for non-browser clients, e.g. the MCP server) ---

API_KEY_PREFIX = "gnk"
# token_hex prefix has no `_`, so `gnk_<prefix>_<secret>` always splits cleanly.
_API_KEY_PREFIX_BYTES = 8
_API_KEY_SECRET_BYTES = 32


def hash_api_key_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Mint a key, returning (full_key shown once, key_prefix, key_hash)."""
    prefix = secrets.token_hex(_API_KEY_PREFIX_BYTES)
    secret = secrets.token_urlsafe(_API_KEY_SECRET_BYTES)
    full_key = f"{API_KEY_PREFIX}_{prefix}_{secret}"
    return full_key, prefix, hash_api_key_secret(secret)


def parse_api_key(full_key: str) -> tuple[str, str] | None:
    """Split `gnk_<prefix>_<secret>` into (prefix, secret), or None if malformed."""
    parts = full_key.split("_", 2)
    if len(parts) != 3:
        return None
    scheme, prefix, secret = parts
    if scheme != API_KEY_PREFIX or not prefix or not secret:
        return None
    return prefix, secret
