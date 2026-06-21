"""_fuzzy_match — SQLite casefold fallback over Product and Recipe."""

from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models.product import Product
from app.models.recipe import Recipe
from app.services._search import _fuzzy_match

HH = 1


def _add_product(db: Session, name: str, grocy_id: int) -> None:
    db.add(
        Product(
            grocy_id=grocy_id,
            name=name,
            product_group_id=1,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()


def _add_recipe(db: Session, name: str, grocy_id: int) -> None:
    db.add(Recipe(grocy_id=grocy_id, name=name, household_id=HH, created_at=datetime.now(UTC)))
    db.commit()


def test_product_substring_casefold(db: Session) -> None:
    _add_product(db, "Деруни картопляні", 1)
    _add_product(db, "Медовик", 2)

    base = select(Product).where(Product.household_id == HH)
    results = _fuzzy_match(db, base, col(Product.name), "деруни", 5)

    names = [r.name for r in results]
    assert "Деруни картопляні" in names
    assert "Медовик" not in names


def test_recipe_substring_casefold(db: Session) -> None:
    _add_recipe(db, "Борщ український", 1)
    _add_recipe(db, "Плов", 2)

    base = select(Recipe).where(Recipe.household_id == HH)
    results = _fuzzy_match(db, base, col(Recipe.name), "БОРЩ", 5)

    names = [r.name for r in results]
    assert "Борщ український" in names
    assert "Плов" not in names


def test_respects_limit(db: Session) -> None:
    for i in range(10):
        _add_product(db, f"Деруни {i}", i + 1)

    base = select(Product).where(Product.household_id == HH)
    results = _fuzzy_match(db, base, col(Product.name), "деруни", 3)
    assert len(results) == 3
