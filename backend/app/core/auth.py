from typing import TYPE_CHECKING, cast

import jwt
from fastapi import Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import is_token_blacklisted
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import TokenPayload
from app.services.grocy_api import GrocyAPI, GrocyConfigError, build_grocy_api

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
