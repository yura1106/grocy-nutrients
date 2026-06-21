"""MCP tool cores — called directly (the MCP app is not mounted in the test app).

Covers: search returns local id only + last_consumption; get_day strips
missing_items (grocy_id) and counts unsynced lines in omitted_lines, not breakdown.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app.mcp.server import _get_day_core, _resolve_date, _search_product_core
from app.models.meal_plan import MealPlan
from app.models.product import ConsumedProduct, Product, ProductData
from app.models.user import User

HH = 1
USER_ID = 1001
DAY = date(2026, 6, 15)


@pytest.fixture()
def user(db: Session) -> User:
    u = User(
        id=USER_ID,
        email="mcp@example.com",
        username="mcp-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _product(db: Session, grocy_id: int, name: str, *, calories: float) -> Product:
    product = Product(
        grocy_id=grocy_id,
        name=name,
        product_group_id=1,
        household_id=HH,
        qu_id_stock=3,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db.add(ProductData(product_id=product.id, calories=calories, created_at=datetime.now(UTC)))
    db.commit()
    return product


def test_resolve_date_aliases() -> None:
    today = datetime.now(UTC).date()
    assert _resolve_date("today") == today
    assert _resolve_date("2026-06-15") == date(2026, 6, 15)


def test_search_product_local_id_and_last_consumption(db: Session, user: User) -> None:
    product = _product(db, 546, "Деруни", calories=2.0)
    pd = db.exec(select(ProductData).where(ProductData.product_id == product.id)).first()
    db.add(
        ConsumedProduct(
            product_data_id=pd.id,
            date=DAY,
            quantity=100,
            user_id=USER_ID,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = _search_product_core(db, user, HH, "деруни", 5)
    assert len(out) == 1
    row = out[0]
    assert row["id"] == product.id
    assert "grocy_id" not in row
    assert row["last_consumption"] is not None
    assert row["last_consumption"]["calories"] == 200.0


def test_get_day_strips_missing_items_and_counts_omitted(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A synced product resolves into breakdown; an unsynced product (no local
    row) is counted in omitted_lines and never appears in breakdown — and the
    response never carries missing_items (grocy_id)."""
    _product(db, 546, "Деруни", calories=2.0)

    # Cache hit for the synced product; the unsynced one has no local row anyway.
    fake_r = MagicMock()
    fake_r.get.return_value = json.dumps({"units": [], "stock_to_grams_ml": 1.0})
    monkeypatch.setattr("app.services.meal_plan.get_redis", lambda: fake_r)

    db.add(
        MealPlan(
            household_id=HH,
            user_id=USER_ID,
            type="product",
            day=DAY,
            section_id=1,
            product_grocy_id=546,
            product_amount=Decimal("100"),
            product_amount_stock=Decimal("100"),
            product_qu_id=82,
            status="pending",
            created_at=datetime.now(UTC),
        )
    )
    db.add(
        MealPlan(
            household_id=HH,
            user_id=USER_ID,
            type="product",
            day=DAY,
            section_id=1,
            product_grocy_id=999,
            product_amount=Decimal("100"),
            product_amount_stock=Decimal("100"),
            product_qu_id=82,
            status="pending",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = _get_day_core(db, user, HH, "2026-06-15")
    assert out["date"] == "2026-06-15"
    assert "missing_items" not in out
    assert out["omitted_lines"] == 1
    assert len(out["breakdown"]) == 1
    line = out["breakdown"][0]
    assert line["id"] is not None
    # Breakdown speaks the same long-form vocabulary as totals (not kcal/protein).
    assert line["calories"] == pytest.approx(200.0)
    assert "kcal" not in line
    assert out["totals"]["calories"] == pytest.approx(200.0)
    # Salt is tracked across the whole day view (totals + breakdown).
    assert "salt" in out["totals"]
    assert "salt" in line
