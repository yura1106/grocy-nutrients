"""search_recipes_fuzzy — local id + per-serving nutrients, no grocy_id, scoped."""

from datetime import UTC, datetime

from sqlmodel import Session

from app.models.recipe import Recipe, RecipeData
from app.services.recipe import search_recipes_fuzzy

HH = 1


def _add_recipe(
    db: Session, name: str, grocy_id: int, *, calories: float | None = 500.0, servings: int = 2
) -> Recipe:
    recipe = Recipe(grocy_id=grocy_id, name=name, household_id=HH, created_at=datetime.now(UTC))
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    if calories is not None:
        db.add(
            RecipeData(
                recipe_id=recipe.id,
                servings=servings,
                calories=calories,
                proteins=25.0,
                consumed_at=datetime.now(UTC),
            )
        )
        db.commit()
    return recipe


def test_returns_local_id_and_nutrients_no_grocy_id(db: Session) -> None:
    recipe = _add_recipe(db, "Борщ український", 10, calories=500.0)

    results = search_recipes_fuzzy(db, query="борщ", household_id=HH)
    assert len(results) == 1
    row = results[0]
    assert row["id"] == recipe.id
    assert row["name"] == "Борщ український"
    assert row["calories"] == 500.0
    assert "grocy_id" not in row


def test_scoped_to_household(db: Session) -> None:
    _add_recipe(db, "Борщ", 10)
    other = Recipe(grocy_id=99, name="Борщ", household_id=999, created_at=datetime.now(UTC))
    db.add(other)
    db.commit()

    results = search_recipes_fuzzy(db, query="борщ", household_id=HH)
    assert len(results) == 1


def test_no_recipe_data_yields_none_nutrients(db: Session) -> None:
    _add_recipe(db, "Плов", 11, calories=None)
    results = search_recipes_fuzzy(db, query="плов", household_id=HH)
    assert results[0]["calories"] is None
