from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import get_current_user, get_grocy_api
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services import user as user_service
from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError

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
