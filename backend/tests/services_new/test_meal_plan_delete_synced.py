"""Tests for `delete_synced_line` — Grocy DELETE then local hard-delete.

Grocy 404 is treated as "already gone": warning + local delete proceeds.
Any other Grocy error → 502, local row preserved.
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
from app.services.meal_plan import delete_synced_line

HH_ID = 8401
USER_ID = 8501
DAY = date(2026, 5, 18)


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Del HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@pytest.fixture()
def user(db: Session, hh: Household) -> User:
    u = User(
        id=USER_ID,
        email="del@example.com",
        username="del-user",
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
        grocy_meal_plan_id=7001,
        type="product",
        day=DAY,
        section_id=2,
        product_id=87,
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


def _persist(db: Session, row: MealPlan) -> MealPlan:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_delete_synced_happy_path(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_product_row())
    row_id = row.id
    grocy = MagicMock()

    delete_synced_line(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row_id,
        grocy_api=grocy,
    )

    grocy.delete.assert_called_once_with("/objects/meal_plan/7001")
    assert db.get(MealPlan, row_id) is None


def test_delete_grocy_404_proceeds_locally(
    db: Session, hh: Household, user: User
) -> None:
    """If Grocy says the row is already gone, the local hard delete still happens."""
    row = _persist(db, _synced_product_row())
    row_id = row.id

    grocy = MagicMock()
    grocy.delete.side_effect = GrocyError("not found", http_status=404)

    delete_synced_line(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row_id,
        grocy_api=grocy,
    )

    assert db.get(MealPlan, row_id) is None


def test_delete_grocy_500_returns_502_and_preserves_row(
    db: Session, hh: Household, user: User
) -> None:
    row = _persist(db, _synced_product_row())
    row_id = row.id

    grocy = MagicMock()
    grocy.delete.side_effect = GrocyError("server error", http_status=500)

    with pytest.raises(HTTPException) as exc_info:
        delete_synced_line(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row_id,
            grocy_api=grocy,
        )

    assert exc_info.value.status_code == 502
    db.expire_all()
    assert db.get(MealPlan, row_id) is not None


def test_delete_grocy_network_error_returns_502_and_preserves_row(
    db: Session, hh: Household, user: User
) -> None:
    row = _persist(db, _synced_product_row())
    row_id = row.id

    grocy = MagicMock()
    grocy.delete.side_effect = GrocyRequestError("connection refused")

    with pytest.raises(HTTPException) as exc_info:
        delete_synced_line(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row_id,
            grocy_api=grocy,
        )

    assert exc_info.value.status_code == 502
    db.expire_all()
    assert db.get(MealPlan, row_id) is not None


def test_delete_rejects_done_row(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_product_row(done=True, done_at=datetime.now(UTC)))
    row_id = row.id
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        delete_synced_line(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row_id,
            grocy_api=grocy,
        )

    assert exc_info.value.status_code == 409
    assert "marked done" in exc_info.value.detail
    grocy.delete.assert_not_called()
    assert db.get(MealPlan, row_id) is not None


@pytest.mark.parametrize(
    "status_value,expected_fragment",
    [
        ("pending", "queued for sync"),
        ("syncing", "currently syncing"),
        ("failed", "local delete action"),
    ],
)
def test_delete_rejects_non_synced_status(
    db: Session, hh: Household, user: User, status_value: str, expected_fragment: str
) -> None:
    row = _persist(db, _synced_product_row(status=status_value))
    row_id = row.id
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        delete_synced_line(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row_id,
            grocy_api=grocy,
        )

    assert exc_info.value.status_code == 409
    assert expected_fragment in exc_info.value.detail
    grocy.delete.assert_not_called()
    assert db.get(MealPlan, row_id) is not None


def test_delete_rejects_other_users_row(db: Session, hh: Household, user: User) -> None:
    other = User(
        id=USER_ID + 1,
        email="other-del@example.com",
        username="other-del",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(other)
    db.commit()

    row = _persist(db, _synced_product_row(user_id=other.id))
    row_id = row.id
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        delete_synced_line(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row_id,
            grocy_api=grocy,
        )

    assert exc_info.value.status_code == 404
    grocy.delete.assert_not_called()
    assert db.get(MealPlan, row_id) is not None
