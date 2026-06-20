import hmac
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import jwt
from fastapi import Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_api_key_secret, is_token_blacklisted, parse_api_key
from app.db.base import get_db
from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_api_key import UserAPIKey
from app.schemas.user import TokenPayload
from app.services.grocy_api import GrocyAPI, GrocyConfigError, build_grocy_api

logger = logging.getLogger(__name__)

# `AuthenticatedUser` is a `User` known to be persisted (id is not None).
# Returned from `get_current_user` so callers can pass `user.id` to APIs that
# expect `int` without `# type: ignore[arg-type]`. At runtime it's just `User`;
# we narrow `id` to `int` only for static type checkers to avoid SQLModel's
# field-shadow warning that arises from a real subclass overriding `id`.
if TYPE_CHECKING:

    class AuthenticatedUser(User):
        id: int  # type: ignore[assignment]
else:
    AuthenticatedUser = User


def _validate_token_and_get_user(token: str, db: Session) -> AuthenticatedUser:
    """Decode the access JWT, run all auth checks, return the User.

    Raises 401 on any failure, 503 if Redis is unavailable (via blacklist check).
    """
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )
    try:
        payload = jwt.decode(
            token,
            settings.APP_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        if token_data.purpose and token_data.purpose != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    statement = select(User).where(User.id == token_data.sub)
    user = db.exec(statement).first()
    if not user or not user.is_active:
        # Uniform 401 — don't leak whether the subject exists or is inactive.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    if token_data.ver is not None and token_data.ver != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )
    # The user was just loaded from DB, so `id` is guaranteed not None.
    return cast(AuthenticatedUser, user)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """Resolve the current user from the access cookie."""
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return _validate_token_and_get_user(token, db)


def _unauthorized() -> HTTPException:
    # Uniform 401 for every failure mode — no existence or timing oracle.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def _touch_last_used(api_key_id: int) -> None:
    """Bump last_used_at best-effort in its own session; never fail the request."""
    try:
        with SessionLocal() as session:
            row = session.get(UserAPIKey, api_key_id)
            if row is not None:
                row.last_used_at = datetime.now(UTC)
                session.add(row)
                session.commit()
    except Exception:
        logger.warning("Failed to update last_used_at for api key", exc_info=True)


def authenticate_api_key(
    full_key: str, db: Session
) -> tuple[AuthenticatedUser, int | None]:
    """Validate `gnk_<prefix>_<secret>`; return (active User, key's household_id).

    `household_id` is None for legacy keys minted before the per-key binding;
    the MCP layer rejects None. Raises 401 on any validation failure.
    """
    parsed = parse_api_key(full_key)
    if parsed is None:
        raise _unauthorized()
    prefix, secret = parsed

    api_key = db.exec(
        select(UserAPIKey).where(UserAPIKey.key_prefix == prefix)
    ).first()
    if api_key is None:
        raise _unauthorized()
    if not hmac.compare_digest(api_key.key_hash, hash_api_key_secret(secret)):
        raise _unauthorized()
    if api_key.expires_at is not None:
        # SQLite may return a naive datetime for a tz-aware column; assume UTC.
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise _unauthorized()

    user = db.get(User, api_key.user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    if api_key.id is not None:
        _touch_last_used(api_key.id)
    return cast(AuthenticatedUser, user), api_key.household_id


def get_grocy_api(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
) -> GrocyAPI:
    """
    FastAPI dependency that returns a configured GrocyAPI instance
    using credentials from the user's household membership.

    Requires household_id query parameter. Looks up:
    - grocy_api_key from HouseholdUser (per-user, per-household)
    - grocy_url from Household
    """
    try:
        return build_grocy_api(db, household_id, current_user.id)
    except GrocyConfigError as exc:
        http_status = (
            status.HTTP_403_FORBIDDEN
            if exc.code == "not_a_member"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=http_status, detail=exc.detail) from exc
