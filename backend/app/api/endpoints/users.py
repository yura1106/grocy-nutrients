import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser, get_current_user, get_grocy_api
from app.core.config import settings
from app.core.rate_limit import check_sensitive_rate_limit
from app.core.security import (
    create_account_deletion_token,
    generate_api_key,
    verify_account_deletion_token,
)
from app.db.base import get_db
from app.models.household import HouseholdUser
from app.models.user_api_key import UserAPIKey
from app.schemas.user import (
    AccountDeletionConfirm,
    HealthParametersRead,
    HealthParametersUpdate,
    UserRead,
    UserUpdate,
)
from app.schemas.user_api_key import APIKeyCreate, APIKeyCreateResponse, APIKeyRead
from app.services import health_profile as health_profile_service
from app.services import household as household_service
from app.services import user as user_service
from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError
from app.tasks.email import send_account_deletion_email_task, send_data_export_email_task

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserRead)
def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Any:
    """
    Get current user information
    """
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_in: UserUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
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
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return health_profile_service.get_health_params(db, current_user)


@router.put("/me/health", response_model=HealthParametersRead)
def update_health_parameters(
    params_in: HealthParametersUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
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
        logger.error("Grocy request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error contacting Grocy server",
        )
    except GrocyError as exc:
        logger.error("Grocy API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Grocy API error",
        )

    return data


@router.post("/me/request-deletion")
def request_account_deletion(
    request: Request,
    export_data: bool = Query(default=False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Request account deletion. Sends confirmation email with deletion link."""
    check_sensitive_rate_limit(request, "request_deletion")
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
    request: Request,
    data: AccountDeletionConfirm,
    db: Session = Depends(get_db),
) -> None:
    """Confirm account deletion via email token. Permanently deletes all user data."""
    check_sensitive_rate_limit(request, "confirm_deletion")
    # We need to find the user first to verify the token
    # Decode without verification to get the user_id
    import jwt

    try:
        unverified = jwt.decode(
            data.token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=[settings.JWT_ALGORITHM],
        )
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


@router.get("/me/api-keys", response_model=list[APIKeyRead])
def list_api_keys(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """List the current user's API keys (metadata only — never the secret)."""
    return db.exec(
        select(UserAPIKey).where(UserAPIKey.user_id == current_user.id)
    ).all()


@router.post("/me/api-keys", response_model=APIKeyCreateResponse, status_code=201)
def create_api_key(
    body: APIKeyCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create an API key bound to a household. The plaintext key is returned ONCE."""
    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == body.household_id,
            HouseholdUser.user_id == current_user.id,
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this household.",
        )

    full_key, prefix, key_hash = generate_api_key()
    api_key = UserAPIKey(
        user_id=current_user.id,
        household_id=body.household_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return APIKeyCreateResponse(
        id=api_key.id,  # type: ignore[arg-type]
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        household_id=api_key.household_id,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        key=full_key,
    )


@router.delete("/me/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke (delete) one of the current user's API keys."""
    api_key = db.exec(
        select(UserAPIKey).where(
            UserAPIKey.id == key_id, UserAPIKey.user_id == current_user.id
        )
    ).first()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    db.delete(api_key)
    db.commit()
