import logging
from datetime import timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.core.encryption import reencrypt_user_api_keys
from app.core.rate_limit import check_login_rate_limit, reset_login_attempts
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    get_password_hash,
    is_token_blacklisted,
    verify_password_reset_token,
    verify_refresh_token,
)
from app.db.base import get_db
from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserCreate,
    UserRead,
)
from app.services import user as user_service
from app.tasks.email import send_password_reset_email_task

logger = logging.getLogger(__name__)

router = APIRouter()


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(
        settings.access_cookie_name,
        access,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.ACCESS_COOKIE_PATH,
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=settings.REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.access_cookie_name, path=settings.ACCESS_COOKIE_PATH)
    response.delete_cookie(settings.refresh_cookie_name, path=settings.REFRESH_COOKIE_PATH)


def _unauthorized_clearing_cookies(detail: str) -> JSONResponse:
    """401 response that also clears the auth cookies.

    Mutating the injected `response` parameter does NOT carry over to a
    raised HTTPException — Starlette builds a fresh response for the
    exception. Returning JSONResponse directly is the only way to attach
    Set-Cookie headers to a non-2xx auth flow result.
    """
    resp = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": detail},
    )
    _clear_auth_cookies(resp)
    return resp


def _issue_token_pair(user: AuthenticatedUser) -> tuple[str, str]:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access = create_access_token(
        user.id,
        token_version=user.token_version,
        expires_delta=access_token_expires,
    )
    refresh = create_refresh_token(user.id, token_version=user.token_version)
    return access, refresh


@router.post("/register", response_model=UserRead)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    # Generic message to prevent account enumeration (OWASP)
    user = user_service.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your input and try again.",
        )

    user = user_service.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your input and try again.",
        )

    user = user_service.create(db, user_in=user_in)
    return user


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> None:
    check_login_rate_limit(request)

    user = user_service.authenticate(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    reset_login_attempts(request)

    access, refresh = _issue_token_pair(cast(AuthenticatedUser, user))
    _set_auth_cookies(response, access, refresh)


@router.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    refresh = request.cookies.get(settings.refresh_cookie_name)
    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    # Reuse detection: if this refresh token was already blacklisted, the prior
    # rotation has happened — this is a replay/theft signal. Clear the cookies
    # and refuse, so the legitimate user has to log in again.
    if is_token_blacklisted(refresh):
        logger.warning("Refresh token reuse detected")
        return _unauthorized_clearing_cookies("Refresh token reused")

    user_id = verify_refresh_token(refresh)
    if user_id is None:
        return _unauthorized_clearing_cookies("Invalid or expired refresh token")

    user = user_service.get_by_id(db, user_id=user_id)
    if not user or not user.is_active:
        return _unauthorized_clearing_cookies("Invalid or expired refresh token")

    # Rotation: blacklist the just-used refresh, issue a fresh pair.
    blacklist_token(refresh)
    new_access, new_refresh = _issue_token_pair(cast(AuthenticatedUser, user))
    _set_auth_cookies(response, new_access, new_refresh)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Always returns 200 to prevent email enumeration (OWASP)."""
    user = user_service.get_by_email(db, email=data.email)
    if user and user.is_active:
        token = create_password_reset_token(user.id, user.hashed_password)  # type: ignore[arg-type]
        send_password_reset_email_task.delay(user.email, user.username, token)
        logger.info("Password reset requested for user %s", user.id)

    return {
        "message": "If an account with this email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> Any:
    import jwt

    try:
        unverified = jwt.decode(
            data.token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = int(unverified.get("sub", 0))
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = user_service.get_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    verified_id = verify_password_reset_token(data.token, user.hashed_password)
    if verified_id is None or verified_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    old_hash = user.hashed_password
    new_hash = get_password_hash(data.new_password)
    reencrypt_user_api_keys(db, user.id, old_hash, new_hash)

    user.hashed_password = new_hash
    # Invalidate all existing sessions on password change.
    user.token_version = (user.token_version or 0) + 1
    db.add(user)
    db.commit()

    logger.info("Password reset completed for user %s", user.id)
    return {"message": "Password has been reset successfully."}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    access = request.cookies.get(settings.access_cookie_name)
    refresh = request.cookies.get(settings.refresh_cookie_name)
    if access:
        blacklist_token(access)
    if refresh:
        blacklist_token(refresh)
    _clear_auth_cookies(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all_devices(
    response: Response,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Invalidate every active session for the current user."""
    current_user.token_version = (current_user.token_version or 0) + 1
    db.add(current_user)
    db.commit()
    _clear_auth_cookies(response)
