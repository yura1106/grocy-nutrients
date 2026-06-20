"""search_products_fuzzy — exercises the SQLite fallback branch (pg_trgm is Postgres-only)."""

from datetime import UTC, datetime

from sqlmodel import Session

from app.models.product import Product
from app.services.product import search_products_fuzzy

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


def test_fallback_substring_match_on_sqlite(db: Session):
    _add_product(db, "Деруни картопляні", 1)
    _add_product(db, "Медовик", 2)

    results = search_products_fuzzy(db, query="деруни", household_id=HH)
    names = [r.name for r in results]
    assert "Деруни картопляні" in names
    assert "Медовик" not in names


def test_scoped_to_household(db: Session):
    _add_product(db, "Деруни", 1)
    db.add(
        Product(
            grocy_id=99,
            name="Деруни",
            product_group_id=1,
            household_id=999,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    results = search_products_fuzzy(db, query="деруни", household_id=HH)
    assert all(r.grocy_id == 1 for r in results)


def test_respects_limit(db: Session):
    for i in range(10):
        _add_product(db, f"Деруни {i}", i + 1)

    results = search_products_fuzzy(db, query="деруни", household_id=HH, limit=3)
    assert len(results) == 3


def test_no_match_returns_empty(db: Session):
    _add_product(db, "Медовик", 1)
    results = search_products_fuzzy(db, query="борщ", household_id=HH)
    assert results == []
