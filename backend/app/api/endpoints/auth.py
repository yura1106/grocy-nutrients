import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.encryption import reencrypt_user_api_keys
from app.core.rate_limit import check_login_rate_limit, reset_login_attempts
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    get_password_hash,
    verify_password_reset_token,
    verify_refresh_token,
)
from app.db.base import get_db
from app.schemas.user import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
)
from app.services import user as user_service
from app.tasks.email import send_password_reset_email_task

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post("/login", response_model=Token)
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    # Rate limit check (OWASP brute-force protection)
    check_login_rate_limit(request)

    user = user_service.authenticate(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Reset rate limit counter on successful login
    reset_login_attempts(request)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Any:
    user_id = verify_refresh_token(data.refresh_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = user_service.get_by_id(db, user_id=user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Always returns 200 to prevent email enumeration (OWASP)."""
    user = user_service.get_by_email(db, email=data.email)
    if user and user.is_active:
        token = create_password_reset_token(user.id, user.hashed_password)
        # Send email asynchronously via Celery
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
    # First decode without verification to get user_id, then verify with their password hash
    from jose import JWTError
    from jose import jwt as jose_jwt

    try:
        unverified = jose_jwt.get_unverified_claims(data.token)
        user_id = int(unverified.get("sub", 0))
    except (JWTError, ValueError):
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

    # Verify token signature with user's current password hash
    verified_id = verify_password_reset_token(data.token, user.hashed_password)
    if verified_id is None or verified_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Re-encrypt API keys with the new password hash before changing it
    old_hash = user.hashed_password
    new_hash = get_password_hash(data.new_password)
    reencrypt_user_api_keys(db, user.id, old_hash, new_hash)

    # Update password
    user.hashed_password = new_hash
    db.add(user)
    db.commit()

    logger.info("Password reset completed for user %s", user.id)
    return {"message": "Password has been reset successfully."}


@router.post("/logout", dependencies=[Depends(get_current_user)])
def logout() -> Any:
    return {"message": "Successfully logged out"}
