"""Tests for enrich_lines: attaches product/recipe names to meal plan rows
and lazy-syncs missing ones from Grocy.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.meal_plan import MealPlan
from app.models.product import Product
from app.models.recipe import Recipe
from app.services.meal_plan import enrich_lines

HH_ID = 9001


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Enrichment HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


def _product_row(grocy_id: int) -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=None,
        type="product",
        day=date(2026, 5, 12),
        section_id=1,
        product_id=grocy_id,
        product_amount=Decimal("22"),
        product_amount_stock=Decimal("0.063"),
        product_qu_id=82,
        status="pending",
        created_at=datetime.now(UTC),
    )


def _recipe_row(grocy_id: int) -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=None,
        type="recipe",
        day=date(2026, 5, 12),
        section_id=2,
        recipe_id=grocy_id,
        recipe_servings=Decimal("1"),
        status="pending",
        created_at=datetime.now(UTC),
    )


def test_enrich_attaches_local_product_and_recipe_names(db: Session, hh: Household) -> None:
    db.add(Product(grocy_id=546, name="Хліб", product_group_id=1, household_id=HH_ID))
    db.add(Recipe(grocy_id=75, name="Борщ", household_id=HH_ID))
    db.commit()

    rows = [_product_row(546), _recipe_row(75)]
    for row in rows:
        db.add(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    out = enrich_lines(db, household_id=HH_ID, rows=rows, grocy_api=None)

    assert out[0].product_name == "Хліб"
    assert out[1].recipe_name == "Борщ"


def test_enrich_lazy_syncs_missing_product_via_grocy(
    db: Session, hh: Household, monkeypatch: pytest.MonkeyPatch
) -> None:
    grocy_api = MagicMock()

    def fake_sync(db_arg, grocy_api_arg, grocy_product_id, household_id=None):
        db_arg.add(
            Product(
                grocy_id=grocy_product_id,
                name="Lazy-synced product",
                product_group_id=1,
                household_id=household_id,
            )
        )
        db_arg.commit()

    monkeypatch.setattr("app.services.product.sync_single_grocy_product", fake_sync)

    rows = [_product_row(777)]
    for row in rows:
        db.add(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    out = enrich_lines(db, household_id=HH_ID, rows=rows, grocy_api=grocy_api)

    assert out[0].product_name == "Lazy-synced product"


def test_enrich_leaves_name_none_when_grocy_unavailable(
    db: Session, hh: Household, monkeypatch: pytest.MonkeyPatch
) -> None:
    grocy_api = MagicMock()

    def raising_sync(*args, **kwargs):
        raise RuntimeError("Grocy down")

    monkeypatch.setattr("app.services.product.sync_single_grocy_product", raising_sync)

    rows = [_product_row(404)]
    for row in rows:
        db.add(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    out = enrich_lines(db, household_id=HH_ID, rows=rows, grocy_api=grocy_api)

    assert out[0].product_name is None
    assert out[0].product_id == 404


def test_enrich_attaches_product_qu_name_from_units_cache(
    db: Session, hh: Household, monkeypatch: pytest.MonkeyPatch
) -> None:
    db.add(Product(grocy_id=546, name="Хліб", product_group_id=1, household_id=HH_ID))
    db.commit()
    grocy_api = MagicMock()

    def fake_units(household_id, product_id, api):
        return {
            "units": [
                {"qu_id": 82, "name": "Грам", "is_stock_default": False, "factor_to_stock": 0.001},
                {"qu_id": 80, "name": "Пачка", "is_stock_default": True, "factor_to_stock": 1.0},
            ],
            "stock_to_grams_ml": 1000.0,
        }

    monkeypatch.setattr("app.services.meal_plan.get_or_load_units_for_product", fake_units)

    rows = [_product_row(546)]
    for row in rows:
        db.add(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    out = enrich_lines(db, household_id=HH_ID, rows=rows, grocy_api=grocy_api)

    assert out[0].product_qu_name == "Грам"
