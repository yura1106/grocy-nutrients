"""Service-layer tests for `type="note"` meal plan rows:
- edit (`update_line_amount` with note field)
- toggle_note_done (note-only done flag, no consumption flow)
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
from app.services.meal_plan import toggle_note_done, update_line_amount

HH_ID = 8401
USER_ID = 8501
DAY = date(2026, 5, 20)


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Note HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@pytest.fixture()
def user(db: Session, hh: Household) -> User:
    u = User(
        id=USER_ID,
        email="note@example.com",
        username="note-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _synced_note_row(**overrides) -> MealPlan:
    row = MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        grocy_meal_plan_id=9100,
        type="note",
        day=DAY,
        section_id=2,
        note="lunch out",
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


# ---------------------------------------------------------------- edit


def test_edit_note_happy_path(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_note_row())
    grocy = MagicMock()

    updated = update_line_amount(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row.id,
        grocy_api=grocy,
        note="new text",
    )

    grocy.put.assert_called_once_with(
        "/objects/meal_plan/9100",
        data={
            "day": DAY.isoformat(),
            "type": "note",
            "section_id": 2,
            "note": "new text",
        },
    )
    db.refresh(updated)
    assert updated.note == "new text"


def test_edit_note_trims_value(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_note_row())
    grocy = MagicMock()

    updated = update_line_amount(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row.id,
        grocy_api=grocy,
        note="  trim me  ",
    )

    db.refresh(updated)
    assert updated.note == "trim me"


def test_edit_note_rejects_empty(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_note_row())
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            note="   ",
        )

    assert exc.value.status_code == 400
    grocy.put.assert_not_called()


def test_edit_note_rejects_amount_fields(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_note_row())
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            note="x",
            recipe_servings=Decimal("1"),
        )

    assert exc.value.status_code == 400
    grocy.put.assert_not_called()


def test_edit_product_rejects_note_field(db: Session, hh: Household, user: User) -> None:
    """Cross-type guard: product rows cannot accept a note patch."""
    row = MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        grocy_meal_plan_id=9101,
        type="product",
        day=DAY,
        section_id=2,
        product_grocy_id=10,
        product_amount=Decimal("1"),
        product_amount_stock=Decimal("1"),
        product_qu_id=5,
        status="synced",
        done=False,
        created_at=datetime.now(UTC),
    )
    _persist(db, row)
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc:
        update_line_amount(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            grocy_api=grocy,
            product_amount=Decimal("2"),
            product_amount_stock=Decimal("2"),
            note="some note",
        )

    assert exc.value.status_code == 400
    grocy.put.assert_not_called()


# ---------------------------------------------------------------- done toggle


def test_toggle_note_done_marks_done(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_note_row())
    grocy = MagicMock()

    updated = toggle_note_done(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row.id,
        done=True,
        grocy_api=grocy,
    )

    grocy.put.assert_called_once_with("/objects/meal_plan/9100", data={"done": 1})
    db.refresh(updated)
    assert updated.done is True
    assert updated.done_at is not None


def test_toggle_note_done_marks_undone(db: Session, hh: Household, user: User) -> None:
    row = _persist(
        db,
        _synced_note_row(done=True, done_at=datetime.now(UTC)),
    )
    grocy = MagicMock()

    updated = toggle_note_done(
        db,
        household_id=HH_ID,
        user_id=USER_ID,
        line_id=row.id,
        done=False,
        grocy_api=grocy,
    )

    grocy.put.assert_called_once_with("/objects/meal_plan/9100", data={"done": 0})
    db.refresh(updated)
    assert updated.done is False
    assert updated.done_at is None


def test_toggle_done_rejects_product_row(db: Session, hh: Household, user: User) -> None:
    row = MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        grocy_meal_plan_id=9102,
        type="product",
        day=DAY,
        section_id=2,
        product_grocy_id=10,
        product_amount=Decimal("1"),
        product_amount_stock=Decimal("1"),
        product_qu_id=5,
        status="synced",
        done=False,
        created_at=datetime.now(UTC),
    )
    _persist(db, row)
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc:
        toggle_note_done(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            done=True,
            grocy_api=grocy,
        )

    assert exc.value.status_code == 400
    grocy.put.assert_not_called()


def test_toggle_done_rejects_pending_status(db: Session, hh: Household, user: User) -> None:
    row = _persist(db, _synced_note_row(status="pending", grocy_meal_plan_id=None))
    grocy = MagicMock()

    with pytest.raises(HTTPException) as exc:
        toggle_note_done(
            db,
            household_id=HH_ID,
            user_id=USER_ID,
            line_id=row.id,
            done=True,
            grocy_api=grocy,
        )

    assert exc.value.status_code == 409
    grocy.put.assert_not_called()
