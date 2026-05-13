"""Tests for stock-amount handling in meal_plan service.

Covers:
- build_grocy_payload sends product_amount_stock (not the user-introduced amount).
- assign_grocy_ids_in_order matches on stock-amount so reconciliation works for
  products entered in a non-stock unit (e.g. user enters 22 g, Grocy stores
  0.0667 packs).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.meal_plan import MealPlan
from app.services.meal_plan import (
    assign_grocy_ids_in_order,
    build_grocy_payload,
)


def _row(**overrides) -> MealPlan:
    base = dict(
        id=1,
        household_id=1,
        user_id=1,
        type="product",
        day=date(2026, 5, 12),
        section_id=2,
        product_id=546,
        product_amount=Decimal("22"),
        product_amount_stock=Decimal("0.062857"),
        product_qu_id=82,
        status="syncing",
        created_at=datetime.now(UTC),
    )
    base.update(overrides)
    return MealPlan(**base)


def test_build_grocy_payload_uses_stock_amount() -> None:
    row = _row()
    payload = build_grocy_payload(row)
    assert payload["product_amount"] == "0.062857"
    assert payload["product_qu_id"] == 82
    assert payload["product_id"] == 546


def test_assign_grocy_ids_matches_on_stock_amount() -> None:
    row = _row()
    # Grocy returns product_amount in stock units (its internal representation).
    candidates = [
        {
            "id": 9001,
            "day": "2026-05-12",
            "section_id": 2,
            "type": "product",
            "product_id": 546,
            "product_amount": "0.062857",
            "product_qu_id": 82,
        }
    ]

    matched, unmatched = assign_grocy_ids_in_order([row], candidates)

    assert len(matched) == 1
    assert len(unmatched) == 0
    assert matched[0].grocy_meal_plan_id == 9001
    assert matched[0].status == "synced"


def test_assign_grocy_ids_does_not_match_on_user_introduced_amount() -> None:
    """Sanity check: a candidate with the user-introduced amount (22) must NOT
    match a row whose stock amount is 0.062857 — that would silently re-introduce
    the very bug this change exists to fix."""
    row = _row()
    candidates = [
        {
            "id": 9001,
            "day": "2026-05-12",
            "section_id": 2,
            "type": "product",
            "product_id": 546,
            "product_amount": "22",
            "product_qu_id": 82,
        }
    ]

    matched, unmatched = assign_grocy_ids_in_order([row], candidates)

    assert matched == []
    assert len(unmatched) == 1
