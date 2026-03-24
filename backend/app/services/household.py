from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.daily_nutrition import DailyNutrition
from app.models.household import Household, HouseholdUser, Role
from app.models.product import (
    ConsumedProduct,
    MealPlanConsumption,
    NoteNutrients,
    Product,
    ProductData,
)
from app.models.recipe import Recipe, RecipeData
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

    return get_household_detail(db, household.id, creator_id)  # type: ignore[arg-type]


def get_user_households(db: Session, user_id: int) -> list[HouseholdWithRole]:
    statement = (
        select(Household, Role.name)
        .join(HouseholdUser, HouseholdUser.household_id == Household.id)  # type: ignore[arg-type]
        .join(Role, Role.id == HouseholdUser.role_id)  # type: ignore[arg-type]
        .where(HouseholdUser.user_id == user_id, HouseholdUser.is_active == True)  # noqa: E712
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
        select(  # type: ignore[call-overload]
            HouseholdUser.user_id,
            User.username,
            User.email,
            Role.name,
            HouseholdUser.grocy_api_key,
            HouseholdUser.last_products_sync_at,
        )
        .join(User, User.id == HouseholdUser.user_id)
        .join(Role, Role.id == HouseholdUser.role_id)
        .where(HouseholdUser.household_id == household_id, HouseholdUser.is_active == True)  # noqa: E712
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
        .join(HouseholdUser, HouseholdUser.household_id == Household.id)  # type: ignore[arg-type]
        .join(Role, Role.id == HouseholdUser.role_id)  # type: ignore[arg-type]
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
            HouseholdUser.is_active == True,  # noqa: E712
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

    # Check for existing membership (including inactive)
    existing = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == target_user_id,
        )
    ).first()

    role = get_or_create_role(db, role_name)

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User already in household"
            )
        # Reactivate inactive membership
        existing.is_active = True
        existing.deactivated_at = None
        existing.role_id = role.id  # type: ignore[assignment]
        db.add(existing)
        db.commit()
        return

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
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    membership.is_active = False
    membership.deactivated_at = datetime.now(UTC)
    db.add(membership)
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


def search_users(db: Session, query: str, current_user_id: int, limit: int = 10) -> list:
    # Only return users who share at least one household with the current user
    my_household_ids = select(HouseholdUser.household_id).where(
        HouseholdUser.user_id == current_user_id,
        HouseholdUser.is_active == True,  # noqa: E712
    )
    fellow_user_ids = (
        select(HouseholdUser.user_id)
        .where(
            HouseholdUser.household_id.in_(my_household_ids),  # type: ignore
            HouseholdUser.is_active == True,  # noqa: E712
            HouseholdUser.user_id != current_user_id,
        )
        .distinct()
    )
    statement = (
        select(User)
        .where(
            User.id.in_(fellow_user_ids),  # type: ignore
            (User.username.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%")),  # type: ignore
        )
        .limit(limit)
    )
    return list(db.exec(statement).all())


def get_user_data_summary(db: Session, household_id: int, user_id: int) -> dict:
    """Count user's data records in a household for deletion warning."""
    tables_with_both = [
        "consumed_products",
        "meal_plan_consumptions",
        "note_nutrients",
        "daily_nutrition",
    ]
    counts: dict[str, int] = {}
    total = 0

    for table in tables_with_both:
        result = db.exec(  # type: ignore[call-overload]
            text(f"SELECT COUNT(*) FROM {table} WHERE household_id = :hid AND user_id = :uid"),
            params={"hid": household_id, "uid": user_id},
        )
        count = result.scalar() or 0
        counts[table] = count
        total += count

    # recipes_data only has user_id
    result = db.exec(  # type: ignore[call-overload]
        text("SELECT COUNT(*) FROM recipes_data WHERE user_id = :uid"),
        params={"uid": user_id},
    )
    count = result.scalar() or 0
    counts["recipes_data"] = count
    total += count

    counts["total"] = total
    return counts


def get_backfill_null_counts(db: Session) -> dict:
    """Count records with NULL household_id or user_id across all affected tables."""
    household_tables = [
        "products",
        "recipes",
        "consumed_products",
        "meal_plan_consumptions",
        "note_nutrients",
        "daily_nutrition",
    ]
    user_tables = [
        "consumed_products",
        "recipes_data",
        "meal_plan_consumptions",
        "note_nutrients",
        "daily_nutrition",
    ]

    all_tables = sorted(set(household_tables + user_tables))
    counts: dict[str, int] = {}
    total = 0

    for table in all_tables:
        conditions = []
        if table in household_tables:
            conditions.append("household_id IS NULL")
        if table in user_tables:
            conditions.append("user_id IS NULL")
        where_clause = " OR ".join(conditions)
        result = db.exec(text(f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"))  # type: ignore[call-overload]
        count = result.scalar() or 0
        counts[table] = count
        total += count

    counts["total"] = total
    return counts


def backfill_null_records(db: Session, household_id: int, user_id: int) -> dict:
    """Fill NULL household_id and user_id values in all affected tables."""
    household_tables = [
        "products",
        "recipes",
        "consumed_products",
        "meal_plan_consumptions",
        "note_nutrients",
        "daily_nutrition",
    ]
    user_tables = [
        "consumed_products",
        "recipes_data",
        "meal_plan_consumptions",
        "note_nutrients",
        "daily_nutrition",
    ]

    updated_household_id = 0
    updated_user_id = 0

    for table in household_tables:
        result = db.exec(  # type: ignore[call-overload]
            text(f"UPDATE {table} SET household_id = :hid WHERE household_id IS NULL"),
            params={"hid": household_id},
        )
        updated_household_id += result.rowcount  # type: ignore[union-attr]

    for table in user_tables:
        result = db.exec(  # type: ignore[call-overload]
            text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
            params={"uid": user_id},
        )
        updated_user_id += result.rowcount  # type: ignore[union-attr]

    db.commit()
    return {
        "updated_household_id": updated_household_id,
        "updated_user_id": updated_user_id,
    }


def _serialize_rows(rows: list) -> list[dict]:
    """Convert SQLModel rows to JSON-serializable dicts."""
    result = []
    for row in rows:
        d = row.model_dump()
        for key, val in d.items():
            if isinstance(val, datetime) or hasattr(val, "isoformat"):
                d[key] = val.isoformat()
        result.append(d)
    return result


def export_user_data(db: Session, user_id: int) -> dict:
    """Collect all user data across tables for export."""
    data: dict[str, list] = {}

    consumed = db.exec(select(ConsumedProduct).where(ConsumedProduct.user_id == user_id)).all()
    data["consumed_products"] = _serialize_rows(list(consumed))

    recipes_data = db.exec(select(RecipeData).where(RecipeData.user_id == user_id)).all()
    data["recipes_data"] = _serialize_rows(list(recipes_data))

    meal_plans = db.exec(
        select(MealPlanConsumption).where(MealPlanConsumption.user_id == user_id)
    ).all()
    data["meal_plan_consumptions"] = _serialize_rows(list(meal_plans))

    notes = db.exec(select(NoteNutrients).where(NoteNutrients.user_id == user_id)).all()
    data["note_nutrients"] = _serialize_rows(list(notes))

    daily = db.exec(select(DailyNutrition).where(DailyNutrition.user_id == user_id)).all()
    data["daily_nutrition"] = _serialize_rows(list(daily))

    return data


def export_household_data(db: Session, household_id: int) -> dict:
    """Collect all household data across tables for export."""
    data: dict[str, list] = {}

    products = db.exec(select(Product).where(Product.household_id == household_id)).all()
    data["products"] = _serialize_rows(list(products))

    product_ids = [p.id for p in products]
    if product_ids:
        products_data = db.exec(
            select(ProductData).where(ProductData.product_id.in_(product_ids))  # type: ignore[attr-defined]
        ).all()
        data["products_data"] = _serialize_rows(list(products_data))
    else:
        data["products_data"] = []

    recipes = db.exec(select(Recipe).where(Recipe.household_id == household_id)).all()
    data["recipes"] = _serialize_rows(list(recipes))

    recipe_ids = [r.id for r in recipes]
    if recipe_ids:
        recipes_data = db.exec(
            select(RecipeData).where(RecipeData.recipe_id.in_(recipe_ids))  # type: ignore[attr-defined]
        ).all()
        data["recipes_data"] = _serialize_rows(list(recipes_data))
    else:
        data["recipes_data"] = []

    consumed = db.exec(
        select(ConsumedProduct).where(ConsumedProduct.household_id == household_id)
    ).all()
    data["consumed_products"] = _serialize_rows(list(consumed))

    meal_plans = db.exec(
        select(MealPlanConsumption).where(MealPlanConsumption.household_id == household_id)
    ).all()
    data["meal_plan_consumptions"] = _serialize_rows(list(meal_plans))

    notes = db.exec(select(NoteNutrients).where(NoteNutrients.household_id == household_id)).all()
    data["note_nutrients"] = _serialize_rows(list(notes))

    daily = db.exec(
        select(DailyNutrition).where(DailyNutrition.household_id == household_id)
    ).all()
    data["daily_nutrition"] = _serialize_rows(list(daily))

    return data


def delete_household(db: Session, household_id: int) -> None:
    """Hard delete a household. CASCADE FK handles all child data."""
    household = db.exec(select(Household).where(Household.id == household_id)).first()
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

    db.delete(household)
    db.commit()


def delete_user_account(db: Session, user_id: int) -> None:
    """Hard delete a user and all their data. CASCADE FK handles child records."""
    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()
