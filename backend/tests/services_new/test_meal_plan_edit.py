"""Tests for `update_line_amount` — editing the amount/servings of a synced
meal plan row. Grocy is PUT first; local row only mutates on Grocy success.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.models.household import Household
from app.models.meal_plan import MealPlan
from app.models.user import User
from app.services.grocy_api import GrocyError, GrocyRequestError
from app.services.meal_plan import update_line_amount

HH_ID = 8201
USER_ID = 8301
DAY = date(2026, 5, 18)


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Edit HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@pytest.fixture()
def user(db: Session, hh: Household) -> User:
    u = User(
        id=USER_ID,
        email="edit@example.com",
        username="edit-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _synced_product_row(**overrides) -> MealPlan:
    row = MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        grocy_meal_plan_id=9001,
        type="product",
        day=DAY,
        section_id=2,
        product_grocy_id=87,
        product_amount=Decimal("10"),
        product_amount_stock=Decimal("10"),
        product_qu_id=85,
        status="synced",
        done=False,
        created_at=datetime.now(UTC),
    )
    for k, v in overrides.items():
        setattr(row, k, v)
    return row


def _synced_recipe_row(**overrides) -> MealPlan:
    row = MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        grocy_meal_plan_id=9002,
        type="recipe",
        day=DAY,
        section_id=2,
        recipe_grocy_id=44,
        recipe_servings=Decimal("1"),
        status="synced",
        done=False,
        created_at=datetime.now(UTC),
    )
    for k, v in overrides.items():
        setattr(row, k, v)
    return row


def _persist(db: Session, row: MealPlan) -> MealPlan:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_edit_product_happy_path_puts_payload_and_updates_row(
    db: Session, hh: Household, user: User
) -> None:
    """PUT shape must include all create fields with the new stock amount;
    local row's product_amount and product_amount_stock must be persisted."""
    row = _persist(db, _synced_product_row())
    grocy = MagicMock()

    updated = update_line_amount(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row.id,
        grocy_api=grocy,
        product_amount=Decimal("15"),
        product_amount_stock=Decimal("15"),
    )

    grocy.put.assert_called_once_with(
        "/objects/meal_plan/9001",
        data={
            "day": DAY.isoformat(),
            "type": "product",
            "section_id": 2,
            "product_id": 87,
            "product_amount": "15",
            "product_qu_id": 85,
        },
    )
    db.refresh(updated)
    assert updated.product_amount == Decimal("15")
    assert updated.product_amount_stock == Decimal("15")


def test_edit_recipe_happy_path(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_recipe_row())
    grocy = MagicMock()

    updated = update_line_amount(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row.id,
        grocy_api=grocy,
        recipe_servings=Decimal("2.5"),
    )

    grocy.put.assert_called_once_with(
        "/objects/meal_plan/9002",
        data={
            "day": DAY.isoformat(),
            "type": "recipe",
            "section_id": 2,
            "recipe_id": 44,
            "recipe_servings": "2.5",
        },
    )
    db.refresh(updated)
    assert updated.recipe_servings == Decimal("2.5")


def test_edit_rejects_done_row(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_product_row(done=True, done_at=datetime.now(UTC)))
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 409
    assert "marked done" in exc_info.value.detail
    grocy.put.assert_not_called()


@pytest.mark.parametrize(
    "status_value,expected_fragment",
    [
        ("pending", "queued for sync"),
        ("syncing", "currently syncing"),
        ("failed", "Failed lines cannot be edited"),
    ],
)
def test_edit_rejects_non_synced_status(
    db: Session, hh: Household, user: User, status_value: str, expected_fragment: str
) -> None:
    row = _persist(db, _synced_product_row(status=status_value))
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 409
    assert expected_fragment in exc_info.value.detail
    grocy.put.assert_not_called()


def test_edit_rejects_other_users_row(db: Session, hh: Household, user: User) -> None:
    other = User(
        id=USER_ID + 1,
        email="other-edit@example.com",
        username="other-edit",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(other)
    db.commit()

    row = _persist(db, _synced_product_row(user_id=other.id))
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 404
    grocy.put.assert_not_called()


def test_edit_rejects_cross_household(db: Session, hh: Household, user: User) -> None:
    other_hh = Household(id=HH_ID + 1, name="Other HH", created_at=datetime.now(UTC))
    db.add(other_hh)
    db.commit()

    row = _persist(db, _synced_product_row(household_id=other_hh.id))
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 404
    grocy.put.assert_not_called()


def test_edit_product_with_recipe_body_returns_400(
    db: Session, hh: Household, user: User
) -> None:
    row = _persist(db, _synced_product_row())
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            recipe_servings=Decimal("2"),
        )

    assert exc_info.value.status_code == 400
    grocy.put.assert_not_called()


def test_edit_recipe_with_product_body_returns_400(
    db: Session, hh: Household, user: User
) -> None:
    row = _persist(db, _synced_recipe_row())
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 400
    grocy.put.assert_not_called()


def test_edit_product_with_only_product_amount_returns_400(
    db: Session, hh: Household, user: User
) -> None:
    """Product edits must send BOTH product_amount and product_amount_stock."""
    row = _persist(db, _synced_product_row())
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
        )

    assert exc_info.value.status_code == 400
    grocy.put.assert_not_called()


def test_edit_grocy_error_returns_502_and_preserves_row(
    db: Session, hh: Household, user: User
) -> None:
    row = _persist(db, _synced_product_row())
    grocy = MagicMock()
    grocy.put.side_effect = GrocyError("boom", http_status=500)

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 502

    db.expire_all()
    fresh = db.get(MealPlan, row.id)
    assert fresh is not None
    assert fresh.product_amount == Decimal("10")
    assert fresh.product_amount_stock == Decimal("10")


def test_edit_grocy_network_error_returns_502_and_preserves_row(
    db: Session, hh: Household, user: User
) -> None:
    row = _persist(db, _synced_product_row())
    grocy = MagicMock()
    grocy.put.side_effect = GrocyRequestError("connection refused")

    with pytest.raises(HTTPException) as exc_info:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("15"),
            product_amount_stock=Decimal("15"),
        )

    assert exc_info.value.status_code == 502

    db.expire_all()
    fresh = db.get(MealPlan, row.id)
    assert fresh is not None
    assert fresh.product_amount == Decimal("10")
    assert fresh.product_amount_stock == Decimal("10")
