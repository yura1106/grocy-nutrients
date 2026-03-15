from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.household import HouseholdUser
from app.models.user import User
from app.schemas.household import (
    AddUserRequest,
    AddUserResponse,
    HouseholdCreate,
    HouseholdDetail,
    HouseholdUpdate,
    HouseholdWithRole,
    SetGrocyKeyRequest,
    UserSearchResult,
)
from app.services import household as household_service

router = APIRouter()


@router.post("", response_model=HouseholdDetail)
def create_household(
    data: HouseholdCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return household_service.create_household(db, data, current_user.id)


@router.get("", response_model=list[HouseholdWithRole])
def get_my_households(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return household_service.get_user_households(db, current_user.id)


@router.get("/search-users", response_model=list[UserSearchResult])
def search_users(
    q: str = Query(min_length=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = household_service.search_users(db, q)
    return [UserSearchResult.model_validate(u) for u in users]


@router.get("/{household_id}", response_model=HouseholdDetail)
def get_household(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return household_service.get_household_detail(db, household_id, current_user.id)


@router.patch("/{household_id}", response_model=HouseholdDetail)
def update_household(
    household_id: int,
    data: HouseholdUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    household_service.check_admin(db, household_id, current_user.id)
    household_service.update_household(db, household_id, data)
    return household_service.get_household_detail(db, household_id, current_user.id)


@router.post("/{household_id}/users", response_model=AddUserResponse)
def add_user(
    household_id: int,
    data: AddUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    household_service.check_admin(db, household_id, current_user.id)
    household_service.add_user_to_household(db, household_id, data.user_id, data.role_name)
    return AddUserResponse(
        household_id=household_id,
        user_id=data.user_id,
        role_name=data.role_name,
    )


@router.put("/{household_id}/grocy-key")
def set_my_grocy_key(
    household_id: int,
    data: SetGrocyKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set the current user's Grocy API key for this household."""
    from sqlmodel import select

    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == current_user.id,
        )
    ).first()
    if not membership:
        from fastapi import HTTPException
        from fastapi import status as http_status

        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Not a member of this household",
        )
    membership.grocy_api_key = data.grocy_api_key
    db.add(membership)
    db.commit()
    return {"message": "Grocy API key saved"}


@router.delete("/{household_id}/users/{user_id}", status_code=204)
def remove_user(
    household_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Allow admin or the user themselves
    is_self = current_user.id == user_id
    if not is_self:
        household_service.check_admin(db, household_id, current_user.id)
    household_service.remove_user_from_household(db, household_id, user_id)
