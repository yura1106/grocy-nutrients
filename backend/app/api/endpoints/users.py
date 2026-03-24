from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.auth import get_current_user, get_grocy_api
from app.core.security import create_account_deletion_token, verify_account_deletion_token
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import (
    AccountDeletionConfirm,
    HealthParametersRead,
    HealthParametersUpdate,
    UserRead,
    UserUpdate,
)
from app.services import health_profile as health_profile_service
from app.services import household as household_service
from app.services import user as user_service
from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError
from app.tasks.email import send_account_deletion_email_task, send_data_export_email_task

router = APIRouter()


@router.get("/me", response_model=UserRead)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user information
    """
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Update current user
    """
    # Check if email is being updated and if it's already taken
    if user_in.email and user_in.email != current_user.email:
        user = user_service.get_by_email(db, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Check if username is being updated and if it's already taken
    if user_in.username and user_in.username != current_user.username:
        user = user_service.get_by_username(db, username=user_in.username)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

    user = user_service.update(db, db_user=current_user, user_in=user_in)
    return user


@router.get("/me/health", response_model=HealthParametersRead)
def get_health_parameters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return health_profile_service.get_health_params(db, current_user)


@router.put("/me/health", response_model=HealthParametersRead)
def update_health_parameters(
    params_in: HealthParametersUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return health_profile_service.update_health_params(db, current_user, params_in)


@router.get("/grocy/system-info")
def get_grocy_system_info(
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    """
    Fetch system info from Grocy for the current user.
    Uses the user's stored GROCY API key.
    """
    try:
        # data = grocy_api.get("/system/info")
        data = grocy_api.get_product(10)
    except GrocyAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Grocy API key",
        )
    except GrocyRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error contacting Grocy: {exc}",
        )
    except GrocyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return data


@router.post("/me/request-deletion")
def request_account_deletion(
    export_data: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Request account deletion. Sends confirmation email with deletion link."""
    token = create_account_deletion_token(current_user.id, current_user.hashed_password)
    send_account_deletion_email_task.delay(current_user.email, current_user.username, token)
    if export_data:
        data = household_service.export_user_data(db, current_user.id)
        send_data_export_email_task.delay(
            current_user.email, current_user.username, data, "account"
        )
    return {"message": "Confirmation email sent. Please check your inbox."}


@router.post("/me/confirm-deletion", status_code=204)
def confirm_account_deletion(
    data: AccountDeletionConfirm,
    db: Session = Depends(get_db),
) -> None:
    """Confirm account deletion via email token. Permanently deletes all user data."""
    # We need to find the user first to verify the token
    # Decode without verification to get the user_id
    from jose import jwt as jose_jwt

    try:
        unverified = jose_jwt.get_unverified_claims(data.token)
        user_id = int(unverified.get("sub", 0))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deletion token",
        )

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Now verify the token properly
    verified_user_id = verify_account_deletion_token(data.token, user.hashed_password)
    if verified_user_id is None or verified_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired deletion token",
        )

    household_service.delete_user_account(db, user.id)
