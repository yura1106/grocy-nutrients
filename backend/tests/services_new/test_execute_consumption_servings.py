"""Regression: meal-plan recipe consumption must store PER-SERVING RecipeData.

The shadow recipe Grocy consumes is scaled to the meal's `recipe_servings`, so
the stock_log (and the nutrients/cost/weight accumulated from it) is a TOTAL for
all servings. RecipeData is the per-serving record (every reader multiplies by
servings — see compute_daily_totals + the frontend MealPlanLineRow). So
execute_consumption must divide the accumulated total by `recipe_servings` and
store `servings = recipe_servings`. Storing the total with servings=1 (the old
bug) made multi-serving meal-plan recipes under-count the daily total.

See CONTEXT.md "RecipeData servings convention (per-serving invariant)".
"""

from sqlmodel import Session, select

from app.models.household import Household
from app.models.product import Product, ProductData
from app.models.recipe import Recipe, RecipeData
from app.models.user import User
from app.services import consumption
from app.services.grocy_api import GrocyAPI

RECIPE_ID = 84
SHADOW_ID = -44725
MEAL_ID = 5536
GROCY_PRODUCT_ID = 491
DATE = "2026-06-07"
GRAM_UNIT = 2
ML_UNIT = 3

# Two servings planned; stock_log holds the 2-serving total.
RECIPE_SERVINGS = 2
TOTAL_AMOUNT = 280.0  # grams Grocy actually deducted for BOTH servings
PRICE_PER_UNIT = 0.10  # → total cost 28.0 for both servings
CALORIES_PER_GRAM = 1.0  # → 280 kcal total, 140 kcal per serving


class FakeGrocy(GrocyAPI):
    """Canned Grocy for one 2-serving recipe meal with a single stock_log leaf."""

    def __init__(self):  # bypass real __init__ (needs url/key)
        self.calls: list[tuple] = []

    @property
    def gram_unit_id(self) -> int:
        return GRAM_UNIT

    @property
    def ml_unit_id(self) -> int:
        return ML_UNIT

    def get(self, path, params=None):
        self.calls.append(("GET", path, params))
        if path == "/objects/meal_plan":
            return [
                {
                    "id": MEAL_ID,
                    "type": "recipe",
                    "recipe_id": RECIPE_ID,
                    "recipe_servings": str(RECIPE_SERVINGS),
                    "day": DATE,
                    "userfields": {"user_id": "1"},
                }
            ]
        if path.startswith("/objects/recipes/"):
            # base recipe object (no linked product → no nutrient write-back)
            return {"id": RECIPE_ID, "name": "Молочний коктейль", "product_id": None}
        if path == "/objects/recipes":  # get_meal_plan_recipe
            return [{"id": SHADOW_ID}]
        if path.endswith("/fulfillment"):
            return {"missing_products_count": 0, "costs": 28.0}
        if path == "/objects/recipes_pos_resolved":
            return [
                {
                    "product_id": GROCY_PRODUCT_ID,
                    "product_id_effective": GROCY_PRODUCT_ID,
                    "recipe_amount": TOTAL_AMOUNT,
                    "is_nested_recipe_pos": 0,
                    "child_recipe_id": None,
                }
            ]
        if path == "/objects/stock_log":
            return [
                {
                    "product_id": GROCY_PRODUCT_ID,
                    "amount": -TOTAL_AMOUNT,
                    "price": PRICE_PER_UNIT,
                }
            ]
        if path.startswith("/stock/products/"):
            return {"stock_amount": 999, "stock_amount_aggregated": 999, "product": {}}
        return []

    def post(self, path, data=None, params=None):
        self.calls.append(("POST", path, data))
        return []

    def put(self, path, data=None, params=None):
        self.calls.append(("PUT", path, data))
        return {}

    # accumulation loop + _save_consumed_product call these
    def get_conversion_factor_safe(self, product_id, qu_id_stock, units):
        return 1.0

    def get_product(self, product_id):
        return {"qu_id_stock": GRAM_UNIT, "parent_product_id": None}


def _seed_product(db: Session, household_id: int) -> None:
    product = Product(
        grocy_id=GROCY_PRODUCT_ID,
        name="Молоко",
        active=True,
        product_group_id=1,
        qu_id_stock=GRAM_UNIT,
        household_id=household_id,
    )
    db.add(product)
    db.flush()
    db.add(
        ProductData(
            product_id=product.id,
            calories=CALORIES_PER_GRAM,
            proteins=0.0,
            carbohydrates=0.0,
            carbohydrates_of_sugars=0.0,
            fats=0.0,
            fats_saturated=0.0,
            salt=0.0,
            fibers=0.0,
        )
    )
    db.add(
        Recipe(
            grocy_id=RECIPE_ID,
            name="Молочний коктейль",
            household_id=household_id,
        )
    )
    db.commit()


def test_multi_serving_recipe_stores_per_serving_nutrients(
    db: Session, test_user: User, test_household: Household
):
    household_id, user_id = test_household.id, test_user.id
    _seed_product(db, household_id)

    consumption.execute_consumption(
        db, FakeGrocy(), DATE, household_id=household_id, user_id=user_id
    )

    recipe = db.exec(select(Recipe).where(Recipe.grocy_id == RECIPE_ID)).first()
    rdata = db.exec(
        select(RecipeData).where(RecipeData.recipe_id == recipe.id)
    ).first()

    assert rdata is not None
    # servings reflects the meal plan, not a hardcoded 1
    assert rdata.servings == RECIPE_SERVINGS
    # 280 kcal total / 2 servings = 140 kcal per serving
    assert rdata.calories == 140.0
    # 28.0 total cost / 2 = 14.0 per serving (Grocy fulfillment.costs is a total)
    assert rdata.price_per_serving == 14.0
    # 280 g total / 2 = 140 g per serving
    assert rdata.weight_per_serving == 140.0
