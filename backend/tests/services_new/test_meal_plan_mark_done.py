"""Tests for meal_plan.mark_done: flips local done flag and (optionally)
records the shadow recipe id captured at consume time.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.meal_plan import MealPlan
from app.services.meal_plan import mark_done

HH_ID = 9101


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="MarkDone HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


def _product_row(grocy_meal_plan_id: int) -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=None,
        type="product",
        day=date(2026, 5, 13),
        section_id=1,
        product_grocy_id=546,
        product_amount=Decimal("22"),
        product_amount_stock=Decimal("0.063"),
        product_qu_id=82,
        grocy_meal_plan_id=grocy_meal_plan_id,
        status="synced",
        created_at=datetime.now(UTC),
    )


def _recipe_row(grocy_meal_plan_id: int) -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=None,
        type="recipe",
        day=date(2026, 5, 13),
        section_id=2,
        recipe_grocy_id=100,
        recipe_servings=Decimal("1"),
        grocy_meal_plan_id=grocy_meal_plan_id,
        status="synced",
        created_at=datetime.now(UTC),
    )


def test_mark_done_sets_done_and_shadow_when_provided(db: Session, hh: Household) -> None:
    row = _recipe_row(grocy_meal_plan_id=5500)
    db.add(row)
    db.commit()
    db.refresh(row)

    mark_done(db, household_id=HH_ID, grocy_meal_plan_id=5500, grocy_shadow_recipe_id=-44435)
    db.commit()
    db.refresh(row)

    assert row.done is True
    assert row.done_at is not None
    assert row.grocy_shadow_recipe_id == -44435


def test_mark_done_sets_done_only_when_no_shadow(db: Session, hh: Household) -> None:
    row = _product_row(grocy_meal_plan_id=5499)
    db.add(row)
    db.commit()
    db.refresh(row)

    mark_done(db, household_id=HH_ID, grocy_meal_plan_id=5499)
    db.commit()
    db.refresh(row)

    assert row.done is True
    assert row.done_at is not None
    assert row.grocy_shadow_recipe_id is None


def test_mark_done_no_op_for_unknown_grocy_meal_plan_id(db: Session, hh: Household) -> None:
    row = _product_row(grocy_meal_plan_id=5499)
    db.add(row)
    db.commit()
    db.refresh(row)

    # Should not raise; simply matches zero rows.
    mark_done(db, household_id=HH_ID, grocy_meal_plan_id=9999999)
    db.commit()
    db.refresh(row)

    assert row.done is False
    assert row.done_at is None
    assert row.grocy_shadow_recipe_id is None


def test_mark_done_does_not_cross_households(db: Session, hh: Household) -> None:
    """A Grocy meal plan id colliding across two households must not bleed.

    Both Grocy servers (one per household) may legitimately use the same id 42;
    mark_done must scope the UPDATE by household_id.
    """
    other_hh = Household(id=HH_ID + 1, name="Other HH", created_at=datetime.now(UTC))
    db.add(other_hh)
    db.commit()

    mine = _product_row(grocy_meal_plan_id=42)
    theirs = MealPlan(
        household_id=other_hh.id,
        user_id=None,
        type="product",
        day=date(2026, 5, 13),
        section_id=1,
        product_grocy_id=999,
        product_amount=Decimal("1"),
        product_amount_stock=Decimal("1"),
        product_qu_id=1,
        grocy_meal_plan_id=42,
        status="synced",
        created_at=datetime.now(UTC),
    )
    db.add(mine)
    db.add(theirs)
    db.commit()
    db.refresh(mine)
    db.refresh(theirs)

    mark_done(db, household_id=HH_ID, grocy_meal_plan_id=42)
    db.commit()
    db.refresh(mine)
    db.refresh(theirs)

    assert mine.done is True
    assert theirs.done is False
