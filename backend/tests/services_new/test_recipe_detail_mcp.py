"""get_recipe_detail_for_mcp — local id only, per-serving history + last breakdown."""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from app.models.product import Product, ProductData
from app.models.recipe import Recipe, RecipeConsumedProduct, RecipeData
from app.services.recipe import RecipeCalculationError, get_recipe_detail_for_mcp

HH = 1
USER = 901


def _recipe_with_consumption(db: Session) -> Recipe:
    recipe = Recipe(grocy_id=5, name="Борщ", household_id=HH, created_at=datetime.now(UTC))
    db.add(recipe)
    db.commit()
    db.refresh(recipe)

    rdata = RecipeData(
        recipe_id=recipe.id, servings=2, calories=500.0, proteins=25.0, user_id=USER,
        consumed_at=datetime.now(UTC),
    )
    db.add(rdata)
    db.commit()
    db.refresh(rdata)

    product = Product(
        grocy_id=1, name="Буряк", product_group_id=1, household_id=HH,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    pd = ProductData(product_id=product.id, calories=0.5, created_at=datetime.now(UTC))
    db.add(pd)
    db.commit()
    db.refresh(pd)
    db.add(
        RecipeConsumedProduct(
            recipe_data_id=rdata.id, product_data_id=pd.id, quantity=200, cost=None
        )
    )
    db.commit()
    return recipe


def test_detail_local_id_history_and_breakdown(db: Session) -> None:
    recipe = _recipe_with_consumption(db)

    out = get_recipe_detail_for_mcp(db, recipe.id, HH, USER)
    assert out["id"] == recipe.id
    assert "grocy_id" not in out
    assert len(out["history"]) == 1
    assert out["history"][0]["calories"] == 500.0
    assert len(out["last_consumed_products"]) == 1
    assert out["last_consumed_products"][0]["product_name"] == "Буряк"
    # 0.5 kcal/g x 200 g = 100
    assert out["last_consumed_products"][0]["total_calories"] == 100.0


def test_other_household_not_found(db: Session) -> None:
    recipe = _recipe_with_consumption(db)
    with pytest.raises(RecipeCalculationError):
        get_recipe_detail_for_mcp(db, recipe.id, HH + 99, USER)
