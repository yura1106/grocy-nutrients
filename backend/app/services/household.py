from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.household import Household, HouseholdUser, Role
from app.models.user import User
from app.schemas.household import (
    HouseholdCreate,
    HouseholdDetail,
    HouseholdMemberRead,
    HouseholdUpdate,
    HouseholdWithRole,
)


def get_or_create_role(db: Session, role_name: str) -> Role:
    role = db.exec(select(Role).where(Role.name == role_name)).first()
    if not role:
        role = Role(name=role_name)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def create_household(db: Session, data: HouseholdCreate, creator_id: int) -> HouseholdDetail:
    household = Household(**data.model_dump())
    db.add(household)
    db.commit()
    db.refresh(household)

    admin_role = get_or_create_role(db, "admin")
    membership = HouseholdUser(
        household_id=household.id,
        user_id=creator_id,
        role_id=admin_role.id,
    )
    db.add(membership)
    db.commit()

    return get_household_detail(db, household.id, creator_id)


def get_user_households(db: Session, user_id: int) -> list[HouseholdWithRole]:
    statement = (
        select(Household, Role.name)
        .join(HouseholdUser, HouseholdUser.household_id == Household.id)
        .join(Role, Role.id == HouseholdUser.role_id)
        .where(HouseholdUser.user_id == user_id)
    )
    results = db.exec(statement).all()
    return [
        HouseholdWithRole(
            id=h.id,
            name=h.name,
            grocy_url=h.grocy_url,
            address=h.address,
            created_at=h.created_at,
            updated_at=h.updated_at,
            role_name=role_name,
        )
        for h, role_name in results
    ]


def get_household_members(db: Session, household_id: int) -> list[HouseholdMemberRead]:
    statement = (
        select(
            HouseholdUser.user_id,
            User.username,
            User.email,
            Role.name,
            HouseholdUser.grocy_api_key,
            HouseholdUser.last_products_sync_at,
        )
        .join(User, User.id == HouseholdUser.user_id)
        .join(Role, Role.id == HouseholdUser.role_id)
        .where(HouseholdUser.household_id == household_id)
    )
    results = db.exec(statement).all()
    return [
        HouseholdMemberRead(
            user_id=user_id,
            username=username,
            email=email,
            role_name=role_name,
            has_grocy_key=bool(grocy_api_key),
            last_products_sync_at=last_sync,
        )
        for user_id, username, email, role_name, grocy_api_key, last_sync in results
    ]


def get_household_detail(db: Session, household_id: int, user_id: int) -> HouseholdDetail:
    statement = (
        select(Household, Role.name)
        .join(HouseholdUser, HouseholdUser.household_id == Household.id)
        .join(Role, Role.id == HouseholdUser.role_id)
        .where(Household.id == household_id, HouseholdUser.user_id == user_id)
    )
    result = db.exec(statement).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

    household, role_name = result
    members = get_household_members(db, household_id)

    return HouseholdDetail(
        id=household.id,
        name=household.name,
        grocy_url=household.grocy_url,
        address=household.address,
        created_at=household.created_at,
        updated_at=household.updated_at,
        role_name=role_name,
        members=members,
    )


def check_admin(db: Session, household_id: int, user_id: int) -> None:
    admin_role = db.exec(select(Role).where(Role.name == "admin")).first()
    if not admin_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == user_id,
            HouseholdUser.role_id == admin_role.id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def add_user_to_household(
    db: Session,
    household_id: int,
    target_user_id: int,
    role_name: str,
) -> None:
    # Verify household exists
    household = db.exec(select(Household).where(Household.id == household_id)).first()
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

    # Verify target user exists
    user = db.exec(select(User).where(User.id == target_user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check duplicate
    existing = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == target_user_id,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already in household"
        )

    role = get_or_create_role(db, role_name)
    membership = HouseholdUser(
        household_id=household_id,
        user_id=target_user_id,
        role_id=role.id,
    )
    db.add(membership)
    db.commit()


def remove_user_from_household(db: Session, household_id: int, target_user_id: int) -> None:
    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == target_user_id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    db.delete(membership)
    db.commit()


def update_household(db: Session, household_id: int, data: HouseholdUpdate) -> Household:
    household = db.exec(select(Household).where(Household.id == household_id)).first()
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(household, field, value)

    db.add(household)
    db.commit()
    db.refresh(household)
    return household


def search_users(db: Session, query: str, limit: int = 10) -> list:
    statement = (
        select(User)
        .where(
            (User.username.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%"))  # type: ignore
        )
        .limit(limit)
    )
    return list(db.exec(statement).all())
