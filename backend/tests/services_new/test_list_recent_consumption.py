"""list_recent_consumption — per-user product + recipe consumption over N days."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.models.product import ConsumedProduct, Product, ProductData
from app.models.recipe import Recipe, RecipeData
from app.services.product import list_recent_consumption

HH = 1
USER = 601


def _today():
    return datetime.now(UTC).date()


def _add_consumed_product(db: Session, *, days_ago: int, qty: float, calories: float) -> None:
    product = Product(
        grocy_id=1,
        name="Банан",
        product_group_id=1,
        household_id=HH,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    pd = ProductData(product_id=product.id, calories=calories, created_at=datetime.now(UTC))
    db.add(pd)
    db.commit()
    db.refresh(pd)
    db.add(
        ConsumedProduct(
            product_data_id=pd.id,
            date=_today() - timedelta(days=days_ago),
            quantity=qty,
            user_id=USER,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()


def _add_consumed_recipe(db: Session, *, days_ago: int, servings: int) -> None:
    recipe = Recipe(grocy_id=2, name="Борщ", household_id=HH, created_at=datetime.now(UTC))
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    db.add(
        RecipeData(
            recipe_id=recipe.id,
            servings=servings,
            calories=500.0,
            user_id=USER,
            consumed_date=_today() - timedelta(days=days_ago),
            consumed_at=datetime.now(UTC),
        )
    )
    db.commit()


def test_within_window(db: Session) -> None:
    _add_consumed_product(db, days_ago=2, qty=100, calories=2.0)
    _add_consumed_recipe(db, days_ago=1, servings=2)

    out = list_recent_consumption(db, USER, HH, days=7)
    assert len(out["products"]) == 1
    assert out["products"][0]["calories"] == 200.0
    assert len(out["recipes"]) == 1
    assert out["recipes"][0]["servings"] == 2


def test_excludes_outside_window(db: Session) -> None:
    _add_consumed_product(db, days_ago=30, qty=100, calories=2.0)
    out = list_recent_consumption(db, USER, HH, days=7)
    assert out["products"] == []


def test_scoped_to_user(db: Session) -> None:
    product = Product(
        grocy_id=1,
        name="Банан",
        product_group_id=1,
        household_id=HH,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    pd = ProductData(product_id=product.id, calories=2.0, created_at=datetime.now(UTC))
    db.add(pd)
    db.commit()
    db.refresh(pd)
    db.add(
        ConsumedProduct(
            product_data_id=pd.id,
            date=_today(),
            quantity=100,
            user_id=USER + 1,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = list_recent_consumption(db, USER, HH, days=7)
    assert out["products"] == []
