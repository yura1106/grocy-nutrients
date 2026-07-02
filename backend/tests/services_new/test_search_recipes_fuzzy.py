"""search_recipes_fuzzy — local id + per-serving nutrients, no grocy_id, scoped."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.product import Product, ProductData
from app.models.recipe import Recipe, RecipeConsumedProduct, RecipeData
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


def _link_consumed_product(
    db: Session,
    recipe: Recipe,
    product_name: str,
    *,
    grocy_id: int,
    household_id: int = HH,
    consumed_at: datetime | None = None,
) -> None:
    """Record `product_name` in `recipe`'s consumption history (via its RecipeData)."""
    product = Product(
        grocy_id=grocy_id,
        name=product_name,
        product_group_id=1,
        household_id=household_id,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    pd = ProductData(product_id=product.id, calories=10.0, created_at=datetime.now(UTC))
    db.add(pd)
    db.commit()
    db.refresh(pd)
    rd = db.exec(select(RecipeData).where(RecipeData.recipe_id == recipe.id)).first()
    assert rd is not None
    if consumed_at is not None:
        rd.consumed_at = consumed_at
        db.add(rd)
    db.add(RecipeConsumedProduct(recipe_data_id=rd.id, product_data_id=pd.id, quantity=1.0))
    db.commit()


def test_returns_local_id_and_nutrients_no_grocy_id(db: Session) -> None:
    recipe = _add_recipe(db, "Борщ український", 10, calories=500.0)

    results = search_recipes_fuzzy(db, query="борщ", household_id=HH)
    assert len(results) == 1
    row = results[0]
    assert row["id"] == recipe.id
    assert row["name"] == "Борщ український"
    assert row["calories"] == 500.0
    assert row["match_reason"] == "name"
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


def test_matches_by_consumed_product_when_name_misses(db: Session) -> None:
    recipe = _add_recipe(db, "Смузі ранковий", 20)
    _link_consumed_product(db, recipe, "Полуниця", grocy_id=100)

    results = search_recipes_fuzzy(db, query="полуниця", household_id=HH)
    assert len(results) == 1
    assert results[0]["id"] == recipe.id
    assert results[0]["match_reason"] == "consumed_product"


def test_name_match_ranks_first_and_dedupes(db: Session) -> None:
    named = _add_recipe(db, "Смузі з полуниця", 21)
    other = _add_recipe(db, "Йогурт домашній", 22)
    _link_consumed_product(db, named, "Полуниця", grocy_id=100)
    _link_consumed_product(db, other, "Полуниця свіжа", grocy_id=101)

    results = search_recipes_fuzzy(db, query="полуниця", household_id=HH)
    ids = [r["id"] for r in results]
    assert ids.count(named.id) == 1
    assert results[0]["id"] == named.id
    assert results[0]["match_reason"] == "name"
    assert {r["id"]: r["match_reason"] for r in results}[other.id] == "consumed_product"


def test_consumed_product_branch_scoped_to_household(db: Session) -> None:
    recipe = _add_recipe(db, "Смузі ранковий", 20)
    _link_consumed_product(db, recipe, "Полуниця", grocy_id=100, household_id=999)

    results = search_recipes_fuzzy(db, query="полуниця", household_id=HH)
    assert results == []


def test_name_matches_fill_limit_before_consumed(db: Session) -> None:
    for i in range(3):
        _add_recipe(db, f"Десерт з полуниця {i}", 30 + i)
    consumed_only = _add_recipe(db, "Безіменний", 40)
    _link_consumed_product(db, consumed_only, "Полуниця", grocy_id=100)

    results = search_recipes_fuzzy(db, query="полуниця", household_id=HH, limit=3)
    assert len(results) == 3
    assert all(r["match_reason"] == "name" for r in results)
    assert consumed_only.id not in [r["id"] for r in results]


def test_excluded_name_match_does_not_steal_consumed_slot(db: Session) -> None:
    named = _add_recipe(db, "Смузі з полуниця", 50)
    _link_consumed_product(db, named, "Полуниця", grocy_id=100)
    consumed_only = _add_recipe(db, "Безіменний десерт", 51)
    _link_consumed_product(db, consumed_only, "Полуниця свіжа", grocy_id=101)

    results = search_recipes_fuzzy(db, query="полуниця", household_id=HH, limit=2)
    ids = [r["id"] for r in results]
    assert ids.count(named.id) == 1
    assert consumed_only.id in ids
    assert len(results) == 2


def test_consumed_product_matches_ranked_most_recent_first(db: Session) -> None:
    older = _add_recipe(db, "Безіменний старий", 60)
    newer = _add_recipe(db, "Безіменний новий", 61)
    _link_consumed_product(
        db, older, "Полуниця", grocy_id=100, consumed_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    _link_consumed_product(
        db, newer, "Полуниця свіжа", grocy_id=101, consumed_at=datetime(2026, 6, 1, tzinfo=UTC)
    )

    results = search_recipes_fuzzy(db, query="полуниця", household_id=HH, limit=1)
    assert len(results) == 1
    assert results[0]["id"] == newer.id
    assert results[0]["match_reason"] == "consumed_product"
