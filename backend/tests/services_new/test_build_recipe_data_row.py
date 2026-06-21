"""Unit tests for the shared per-serving RecipeData persist core.

`_build_recipe_data_row` is the deduplicated heart of the two persistence
paths (meal-plan `_save_recipe_data` and manual `save_recipe_consumption_data`).
It takes FINISHED per-serving figures, builds the RecipeData row plus its
RecipeConsumedProduct children, flushes, and returns the row WITHOUT committing
— the caller owns the transaction (ADR-0001: meal-plan orchestrator must keep
the consume atomic; manual path commits itself).

See CONTEXT.md "RecipeData servings convention (per-serving invariant)".
"""

from sqlmodel import Session, select

from app.models.household import Household
from app.models.recipe import Recipe, RecipeConsumedProduct
from app.schemas.recipe import RecipeNutrients
from app.services.recipe import _build_recipe_data_row


def _per_serving() -> RecipeNutrients:
    return RecipeNutrients(
        calories=140.0,
        proteins=1.0,
        carbohydrates=2.0,
        carbohydrates_of_sugars=3.0,
        fats=4.0,
        fats_saturated=5.0,
        salt=6.0,
        fibers=7.0,
    )


def _seed_recipe(db: Session, household_id: int) -> Recipe:
    recipe = Recipe(grocy_id=84, name="Молочний коктейль", household_id=household_id)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def test_builds_per_serving_row_without_committing(db: Session, test_household: Household):
    recipe = _seed_recipe(db, test_household.id)

    rdata = _build_recipe_data_row(
        db,
        recipe,
        servings=2,
        price_per_serving=14.0,
        weight_per_serving=140.0,
        nutrients=_per_serving(),
        user_id=1,
        consumed_date=None,
    )

    # Row is populated from the per-serving figures verbatim — no division here.
    assert rdata.recipe_id == recipe.id
    assert rdata.servings == 2
    assert rdata.price_per_serving == 14.0
    assert rdata.weight_per_serving == 140.0
    assert rdata.calories == 140.0
    assert rdata.fibers == 7.0

    # Helper must NOT commit — the row is still pending (no flush, no commit),
    # so the caller owns the transaction (ADR-0001).
    assert rdata in db.new
    assert rdata.id is None


def test_persists_consumed_products_as_children(db: Session, test_household: Household):
    recipe = _seed_recipe(db, test_household.id)

    rdata = _build_recipe_data_row(
        db,
        recipe,
        servings=1,
        price_per_serving=None,
        weight_per_serving=None,
        nutrients=_per_serving(),
        user_id=1,
        consumed_products_data=[
            {"product_data_id": 11, "quantity": 280.0, "cost": 28.0},
        ],
    )
    db.commit()

    children = db.exec(
        select(RecipeConsumedProduct).where(RecipeConsumedProduct.recipe_data_id == rdata.id)
    ).all()
    assert len(children) == 1
    # Child rows carry BATCH totals (mixed convention) — stored verbatim.
    assert children[0].quantity == 280.0
    assert children[0].cost == 28.0
