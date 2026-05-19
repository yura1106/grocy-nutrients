"""compute_daily_totals — contribution from `type="note"` rows.

Notes with a Cyrillic-keyed nutrient format add to the day totals; notes
without the format contribute nothing and are NOT listed in missing_items
(missing_items is for product/recipe rows that lack stored nutrition).
"""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.meal_plan import MealPlan
from app.models.user import User
from app.services.meal_plan import compute_daily_totals

HH_ID = 7301
USER_ID = 7401
DAY = date(2026, 5, 20)


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Note Totals HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@pytest.fixture()
def user(db: Session, hh: Household) -> User:
    u = User(
        id=USER_ID,
        email="note-totals@example.com",
        username="note-totals-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _note_row(note: str, *, status: str = "synced") -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        type="note",
        day=DAY,
        section_id=1,
        note=note,
        status=status,
        created_at=datetime.now(UTC),
    )


def test_note_with_format_contributes_to_totals(db: Session, hh, user) -> None:
    db.add(
        _note_row(
            "Калорій:500/Білків:30/Вуглеводів:60/Вуглеводів цукрів:5/"
            "Жирів:15/Жирів нас.:3/Клітковини:7"
        )
    )
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 500.0
    assert result["protein"] == 30.0
    assert result["carbs"] == 60.0
    assert result["sugars"] == 5.0
    assert result["fat"] == 15.0
    assert result["sat_fat"] == 3.0
    assert result["fibers"] == 7.0
    assert result["missing_items"] == []


def test_plain_note_contributes_zero(db: Session, hh, user) -> None:
    db.add(_note_row("просто текст про обід"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 0.0
    assert result["protein"] == 0.0
    assert result["missing_items"] == []


def test_multiple_notes_sum_together(db: Session, hh, user) -> None:
    db.add(_note_row("Калорій:200/Білків:10"))
    db.add(_note_row("Калорій:300/Білків:15"))
    db.add(_note_row("plain text — counts as zero"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 500.0
    assert result["protein"] == 25.0


def test_failed_note_excluded_from_totals(db: Session, hh, user) -> None:
    db.add(_note_row("Калорій:1000", status="failed"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 0.0
