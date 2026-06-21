"""get_daily_nutrition_range — per-user DailyNutrition rows in [start, end]."""

from datetime import UTC, date, datetime

from sqlmodel import Session

from app.models.daily_nutrition import DailyNutrition
from app.services.daily_nutrition import get_daily_nutrition_range

USER = 701


def _add(db: Session, day: date, *, calories: float, user_id: int = USER) -> None:
    db.add(
        DailyNutrition(date=day, user_id=user_id, calories=calories, created_at=datetime.now(UTC))
    )
    db.commit()


def test_inclusive_range_ordered_asc(db: Session) -> None:
    _add(db, date(2026, 6, 1), calories=1000)
    _add(db, date(2026, 6, 3), calories=1500)
    _add(db, date(2026, 6, 5), calories=2000)

    rows = get_daily_nutrition_range(db, USER, date(2026, 6, 1), date(2026, 6, 3))
    assert [r.day for r in rows] == ["2026-06-01", "2026-06-03"]
    assert rows[0].calories == 1000


def test_excludes_outside_range(db: Session) -> None:
    _add(db, date(2026, 5, 31), calories=1)
    _add(db, date(2026, 6, 6), calories=1)
    rows = get_daily_nutrition_range(db, USER, date(2026, 6, 1), date(2026, 6, 5))
    assert rows == []


def test_scoped_to_user(db: Session) -> None:
    _add(db, date(2026, 6, 2), calories=1, user_id=USER + 1)
    rows = get_daily_nutrition_range(db, USER, date(2026, 6, 1), date(2026, 6, 5))
    assert rows == []
