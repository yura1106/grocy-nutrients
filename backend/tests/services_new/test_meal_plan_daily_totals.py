"""Tests for compute_daily_totals: sums nutrition for all non-failed meal plan
rows on a given day, surfacing products/recipes that lack nutrient data.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.meal_plan import MealPlan
from app.models.product import Product, ProductData
from app.models.recipe import Recipe, RecipeData
from app.models.user import User
from app.services.meal_plan import compute_daily_totals

HH_ID = 7001
USER_ID = 7101
DAY = date(2026, 5, 13)


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Totals HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@pytest.fixture()
def user(db: Session) -> User:
    u = User(
        id=USER_ID,
        email="totals@example.com",
        username="totals-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _product_row(
    grocy_id: int,
    *,
    amount: str = "100",
    amount_stock: str = "100",
    status: str = "pending",
    day: date = DAY,
    user_id: int | None = USER_ID,
) -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=user_id,
        type="product",
        day=day,
        section_id=1,
        product_id=grocy_id,
        product_amount=Decimal(amount),
        product_amount_stock=Decimal(amount_stock),
        product_qu_id=82,
        status=status,
        created_at=datetime.now(UTC),
    )


def _recipe_row(
    grocy_id: int,
    *,
    servings: str = "1",
    status: str = "pending",
    day: date = DAY,
    user_id: int | None = USER_ID,
) -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=user_id,
        type="recipe",
        day=day,
        section_id=2,
        recipe_id=grocy_id,
        recipe_servings=Decimal(servings),
        status=status,
        created_at=datetime.now(UTC),
    )


def _add_product(
    db: Session,
    grocy_id: int,
    *,
    name: str = "Test product",
    calories: float | None = 2.0,
    proteins: float | None = 0.1,
    carbohydrates: float | None = 0.2,
    carbohydrates_of_sugars: float | None = 0.05,
    fats: float | None = 0.3,
    fats_saturated: float | None = 0.15,
    fibers: float | None = 0.02,
) -> Product:
    """Create Product + a single ProductData snapshot (per-gram nutrient values)."""
    product = Product(
        grocy_id=grocy_id,
        active=True,
        name=name,
        product_group_id=1,
        qu_id_stock=3,
        household_id=HH_ID,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db.add(
        ProductData(
            product_id=product.id,
            calories=calories,
            proteins=proteins,
            carbohydrates=carbohydrates,
            carbohydrates_of_sugars=carbohydrates_of_sugars,
            fats=fats,
            fats_saturated=fats_saturated,
            fibers=fibers,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return product


def _add_recipe(
    db: Session,
    grocy_id: int,
    *,
    name: str = "Test recipe",
    calories: float | None = 500.0,
    proteins: float | None = 25.0,
    carbohydrates: float | None = 60.0,
    carbohydrates_of_sugars: float | None = 10.0,
    fats: float | None = 15.0,
    fats_saturated: float | None = 5.0,
    fibers: float | None = 8.0,
) -> Recipe:
    """Create Recipe + a single RecipeData snapshot (per-serving nutrient values)."""
    recipe = Recipe(
        grocy_id=grocy_id,
        name=name,
        household_id=HH_ID,
        created_at=datetime.now(UTC),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    db.add(
        RecipeData(
            recipe_id=recipe.id,
            servings=1,
            calories=calories,
            proteins=proteins,
            carbohydrates=carbohydrates,
            carbohydrates_of_sugars=carbohydrates_of_sugars,
            fats=fats,
            fats_saturated=fats_saturated,
            fibers=fibers,
            consumed_at=datetime.now(UTC),
        )
    )
    db.commit()
    return recipe


def _mock_grocy_api(stock_to_grams_by_product: dict[int, float | None]) -> MagicMock:
    """Mock that returns the requested stock_to_grams_ml per product_id, via
    monkeypatched get_or_load_units_for_product (see fixture below).
    """
    return MagicMock()


@pytest.fixture()
def patch_units(monkeypatch: pytest.MonkeyPatch):
    """Patch get_or_load_units_for_product to return controlled stock_to_grams_ml
    per product_id. Returns a setter callable test bodies use to register values.
    """
    registry: dict[int, float | None] = {}

    def fake_get(household_id: int, product_id: int, grocy_api):
        return {
            "units": [],
            "stock_to_grams_ml": registry.get(product_id, 1.0),
        }

    monkeypatch.setattr("app.services.meal_plan.get_or_load_units_for_product", fake_get)

    def set_for(product_id: int, value: float | None) -> None:
        registry[product_id] = value

    return set_for


def test_product_only_day_sums_correctly(db: Session, hh: Household, user: User, patch_units) -> None:
    """100 g of product with calories=2/g → 200 kcal. Stock unit = grams.
    factor_to_stock = 1 (already in stock), stock_to_grams_ml = 1.
    """
    _add_product(db, grocy_id=546)
    patch_units(546, 1.0)

    row = _product_row(546, amount="100", amount_stock="100")
    db.add(row)
    db.commit()
    db.refresh(row)

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == pytest.approx(200.0)
    assert result["protein"] == pytest.approx(10.0)
    assert result["carbs"] == pytest.approx(20.0)
    assert result["sugars"] == pytest.approx(5.0)
    assert result["fat"] == pytest.approx(30.0)
    assert result["sat_fat"] == pytest.approx(15.0)
    assert result["fibers"] == pytest.approx(2.0)
    assert result["missing_items"] == []


def test_recipe_only_day_scales_by_servings(db: Session, hh: Household, user: User, patch_units) -> None:
    """2 servings of a recipe whose latest snapshot is 500 kcal/serving → 1000 kcal."""
    _add_recipe(db, grocy_id=75)

    row = _recipe_row(75, servings="2")
    db.add(row)
    db.commit()
    db.refresh(row)

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == pytest.approx(1000.0)
    assert result["protein"] == pytest.approx(50.0)
    assert result["carbs"] == pytest.approx(120.0)
    assert result["sugars"] == pytest.approx(20.0)
    assert result["fat"] == pytest.approx(30.0)
    assert result["sat_fat"] == pytest.approx(10.0)
    assert result["fibers"] == pytest.approx(16.0)
    assert result["missing_items"] == []


def test_mixed_day_product_and_recipe(db: Session, hh: Household, user: User, patch_units) -> None:
    _add_product(db, grocy_id=546)
    _add_recipe(db, grocy_id=75)
    patch_units(546, 1.0)

    db.add(_product_row(546, amount="100", amount_stock="100"))
    db.add(_recipe_row(75, servings="1"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    # 200 (product) + 500 (recipe) = 700 kcal
    assert result["kcal"] == pytest.approx(700.0)
    assert result["missing_items"] == []


def test_failed_rows_are_excluded(db: Session, hh: Household, user: User, patch_units) -> None:
    _add_product(db, grocy_id=546)
    patch_units(546, 1.0)

    db.add(_product_row(546, amount="100", amount_stock="100", status="pending"))
    db.add(_product_row(546, amount="100", amount_stock="100", status="failed"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    # Only the pending row counts → 200 kcal, not 400.
    assert result["kcal"] == pytest.approx(200.0)


def test_all_failed_day_returns_zeros(db: Session, hh: Household, user: User, patch_units) -> None:
    _add_product(db, grocy_id=546)
    patch_units(546, 1.0)

    db.add(_product_row(546, amount="100", amount_stock="100", status="failed"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 0
    assert result["protein"] == 0
    assert result["carbs"] == 0
    assert result["sugars"] == 0
    assert result["fat"] == 0
    assert result["sat_fat"] == 0
    assert result["fibers"] == 0
    assert result["missing_items"] == []


def test_product_without_nutrient_data_lands_in_missing(
    db: Session, hh: Household, user: User, patch_units
) -> None:
    """A product whose latest ProductData has calories=None is flagged as
    missing and contributes zero to totals.
    """
    _add_product(
        db,
        grocy_id=999,
        name="No-nutrition cheese",
        calories=None,
        proteins=None,
        carbohydrates=None,
        carbohydrates_of_sugars=None,
        fats=None,
        fats_saturated=None,
        fibers=None,
    )
    patch_units(999, 1.0)

    db.add(_product_row(999, amount="100", amount_stock="100"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 0
    assert len(result["missing_items"]) == 1
    item = result["missing_items"][0]
    assert item["type"] == "product"
    assert item["grocy_id"] == 999
    assert item["name"] == "No-nutrition cheese"


def test_recipe_without_latest_data_lands_in_missing(
    db: Session, hh: Household, user: User, patch_units
) -> None:
    """A recipe with zero RecipeData rows yields a missing entry, not a crash."""
    recipe = Recipe(
        grocy_id=404,
        name="Empty recipe",
        household_id=HH_ID,
        created_at=datetime.now(UTC),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)

    db.add(_recipe_row(404, servings="1"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 0
    assert len(result["missing_items"]) == 1
    item = result["missing_items"][0]
    assert item["type"] == "recipe"
    assert item["grocy_id"] == 404
    assert item["name"] == "Empty recipe"


def test_stock_to_grams_none_marks_product_missing(
    db: Session, hh: Household, user: User, patch_units
) -> None:
    """If we cannot resolve stock_to_grams_ml for a product, we cannot scale
    its nutrient values reliably — flag it as missing and skip its contribution.
    """
    _add_product(db, grocy_id=546)
    patch_units(546, None)

    db.add(_product_row(546, amount="100", amount_stock="100"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == 0
    assert len(result["missing_items"]) == 1
    assert result["missing_items"][0]["type"] == "product"
    assert result["missing_items"][0]["grocy_id"] == 546


def test_non_stock_unit_scales_through_factor_and_stock_to_grams(
    db: Session, hh: Household, user: User, patch_units
) -> None:
    """User enters 11 g of a product stocked in 'pack'. Grocy stores it as
    11 * 1/1 packs = depends. Our compute uses product_amount_stock * stock_to_grams_ml
    as the gram-weight. Example: 0.0667 packs * 165 g/pack = 11 g → 22 kcal.
    """
    _add_product(db, grocy_id=546, calories=2.0)
    patch_units(546, 165.0)

    db.add(_product_row(546, amount="11", amount_stock="0.0667"))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    # 0.0667 packs * 165 g/pack = 11.0055 g → 22.011 kcal
    assert result["kcal"] == pytest.approx(22.011, rel=1e-3)


def test_other_household_rows_excluded(
    db: Session, hh: Household, user: User, patch_units, monkeypatch: pytest.MonkeyPatch
) -> None:
    other_hh = Household(id=HH_ID + 1, name="Other", created_at=datetime.now(UTC))
    db.add(other_hh)
    db.commit()

    _add_product(db, grocy_id=546)
    patch_units(546, 1.0)

    row_ours = _product_row(546, amount="100", amount_stock="100")
    row_theirs = _product_row(546, amount="100", amount_stock="100")
    row_theirs.household_id = HH_ID + 1
    db.add(row_ours)
    db.add(row_theirs)
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == pytest.approx(200.0)


def test_other_user_rows_excluded(
    db: Session, hh: Household, user: User, patch_units
) -> None:
    """Daily totals must scope by user_id — another member's rows in the same
    household must not contribute.
    """
    other_user = User(
        id=USER_ID + 1,
        email="other@example.com",
        username="other-totals-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(other_user)
    db.commit()

    _add_product(db, grocy_id=546)
    patch_units(546, 1.0)

    row_ours = _product_row(546, amount="100", amount_stock="100", user_id=USER_ID)
    row_theirs = _product_row(
        546, amount="100", amount_stock="100", user_id=USER_ID + 1
    )
    db.add(row_ours)
    db.add(row_theirs)
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == pytest.approx(200.0)


def test_other_day_rows_excluded(db: Session, hh: Household, user: User, patch_units) -> None:
    _add_product(db, grocy_id=546)
    patch_units(546, 1.0)

    db.add(_product_row(546, amount="100", amount_stock="100", day=DAY))
    db.add(_product_row(546, amount="100", amount_stock="100", day=date(2026, 5, 14)))
    db.commit()

    result = compute_daily_totals(
        db, household_id=HH_ID, user_id=USER_ID, day=DAY, grocy_api=MagicMock()
    )

    assert result["kcal"] == pytest.approx(200.0)
