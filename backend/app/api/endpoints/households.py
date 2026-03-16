from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.core.encryption import decrypt_api_key, encrypt_api_key
from app.core.security import verify_password
from app.db.base import get_db
from app.models.household import Household, HouseholdUser
from app.models.user import User
from app.schemas.household import (
    AddUserRequest,
    AddUserResponse,
    BackfillNullCounts,
    BackfillResult,
    HouseholdCreate,
    HouseholdDeleteRequest,
    HouseholdDetail,
    HouseholdUpdate,
    HouseholdWithRole,
    SetGrocyKeyRequest,
    UserDataSummary,
    UserSearchResult,
)
from app.services import household as household_service
from app.tasks.email import send_data_export_email_task

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


@router.get("/{household_id}/grocy-key")
def get_my_grocy_key(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's decrypted Grocy API key for this household."""
    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == current_user.id,
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a member of this household",
        )
    if not membership.grocy_api_key:
        return {"grocy_api_key": None}
    plaintext = decrypt_api_key(membership.grocy_api_key, current_user.hashed_password)
    if not plaintext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt Grocy API key. Please re-save your key.",
        )
    return {"grocy_api_key": plaintext}


@router.put("/{household_id}/grocy-key")
def set_my_grocy_key(
    household_id: int,
    data: SetGrocyKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set the current user's Grocy API key for this household."""
    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == current_user.id,
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a member of this household",
        )
    membership.grocy_api_key = encrypt_api_key(data.grocy_api_key, current_user.hashed_password)
    db.add(membership)
    db.commit()
    return {"message": "Grocy API key saved"}


@router.get("/{household_id}/users/{user_id}/data-summary", response_model=UserDataSummary)
def get_user_data_summary(
    household_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get count of user's data records in a household (for deletion warning)."""
    is_self = current_user.id == user_id
    if not is_self:
        household_service.check_admin(db, household_id, current_user.id)
    return household_service.get_user_data_summary(db, household_id, user_id)


@router.delete("/{household_id}/users/{user_id}", status_code=204)
def remove_user(
    household_id: int,
    user_id: int,
    confirm: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete user from household. Requires confirm=true."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Pass ?confirm=true",
        )
    # Allow admin or the user themselves
    is_self = current_user.id == user_id
    if not is_self:
        household_service.check_admin(db, household_id, current_user.id)
    household_service.remove_user_from_household(db, household_id, user_id)


@router.delete("/{household_id}", status_code=204)
def delete_household(
    household_id: int,
    data: HouseholdDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hard delete a household and all its data. Requires password + confirmation text."""
    household_service.check_admin(db, household_id, current_user.id)

    # Verify password
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect password",
        )

    # Verify confirmation text
    household = db.exec(select(Household).where(Household.id == household_id)).first()
    if not household:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )
    expected = f"DELETE {household.name}"
    if data.confirmation_text != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation text must be exactly: {expected}",
        )

    if data.export_data:
        export = household_service.export_household_data(db, household_id)
        send_data_export_email_task.delay(
            current_user.email, current_user.username, export, "household"
        )

    household_service.delete_household(db, household_id)


@router.get("/{household_id}/backfill-status", response_model=BackfillNullCounts)
def get_backfill_status(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get count of records with NULL household_id or user_id (admin-only)."""
    household_service.check_admin(db, household_id, current_user.id)
    return household_service.get_backfill_null_counts(db)


@router.post("/{household_id}/backfill", response_model=BackfillResult)
def run_backfill(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fill NULL household_id and user_id values with current household/user (admin-only)."""
    household_service.check_admin(db, household_id, current_user.id)
    return household_service.backfill_null_records(db, household_id, current_user.id)
