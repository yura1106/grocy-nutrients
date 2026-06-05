from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from app.models.product import ConsumedProduct, Product, ProductData
from app.services.consume_recipe import (
    ConsumedRecipeResult,
    build_recipe_result,
    persist_recipe_result,
    process_recipe_meal,
)
from app.services.consumption_attribution import AttributedRow


class TestBuildRecipeResult:
    """Pure decision: stock_log + resolved + top-level id -> result object.
    No Grocy, no DB. Attribution is delegated to the attribution module."""

    def _resolved(self):
        return [
            {"product_id": 26, "product_id_effective": 491, "recipe_amount": 2,
             "is_nested_recipe_pos": 1, "child_recipe_id": 3},
        ]

    def test_attributes_rows_and_carries_shadow_and_top_level(self):
        result = build_recipe_result(
            top_level_recipe_id=75,
            shadow_id=-44663,
            stock_log=[{"product_id": 42, "amount": -2.0, "price": 0.5}],
            resolved=self._resolved(),
            parent_lookup=lambda pid: 26 if pid == 42 else None,
        )
        assert isinstance(result, ConsumedRecipeResult)
        assert result.shadow_id == -44663
        assert result.top_level_recipe_id == 75
        assert len(result.attributed_rows) == 1
        row = result.attributed_rows[0]
        assert row.grocy_product_id == 42
        assert row.originating_recipe_grocy_id == 3
        assert row.amount == 2.0
        assert row.cost == 1.0

    def test_empty_stock_log_yields_no_rows(self):
        result = build_recipe_result(
            top_level_recipe_id=75,
            shadow_id=-44663,
            stock_log=[],
            resolved=self._resolved(),
            parent_lookup=lambda pid: None,
        )
        assert result.attributed_rows == []


class TestProcessRecipeMeal:
    """Side-effecting: drives Grocy (fulfillment, consume, stock_log, resolved),
    returns (result, skip_reason). Uses a fake GrocyAPI — no live Grocy."""

    def _api(self, missing=0):
        api = MagicMock()
        api.get_meal_plan_recipe.return_value = {"id": -44663}
        api.get_recipe_fulfillment.return_value = {"missing_products_count": missing}
        api.get_resolved_positions.return_value = [
            {"product_id": 26, "product_id_effective": 491, "recipe_amount": 2,
             "is_nested_recipe_pos": 1, "child_recipe_id": 3},
        ]
        api.get.return_value = [{"product_id": 42, "amount": -2.0, "price": 0.5}]
        api.get_product.return_value = {"parent_product_id": 26}
        return api

    def test_consumes_and_returns_attributed_result(self):
        api = self._api()
        meal = {"id": 5531, "recipe_id": 75, "day": "2026-06-04"}
        result, skip = process_recipe_meal(api, meal)
        assert skip is None
        assert result.top_level_recipe_id == 75
        assert result.shadow_id == -44663
        assert result.attributed_rows[0].originating_recipe_grocy_id == 3
        api.consume_recipe.assert_called_once_with(-44663)
        api.mark_meal_plan_done.assert_called_once_with(5531)

    def test_missing_products_skips_without_consuming(self):
        api = self._api(missing=2)
        meal = {"id": 5531, "recipe_id": 75, "day": "2026-06-04"}
        result, skip = process_recipe_meal(api, meal)
        assert result is None
        assert "Missing 2" in skip
        api.consume_recipe.assert_not_called()


def test_persist_writes_one_row_per_attributed_row(db):
    # `db`: real conftest fixture — a live Session, rollback-isolated per test.
    product = Product(
        grocy_id=42, name="Приправка", active=True, product_group_id=1,
        household_id=1, qu_id_stock=82, created_at=datetime.now(UTC),
    )
    db.add(product)
    db.flush()
    db.add(ProductData(
        product_id=product.id, carbohydrates_of_sugars=0.0,
        created_at=datetime.now(UTC),
    ))
    db.commit()

    grocy_api = MagicMock()
    grocy_api.get_conversion_factor_safe.return_value = 1.0
    grocy_api.gram_ml_units = []

    result = ConsumedRecipeResult(
        top_level_recipe_id=75, shadow_id=-44663,
        attributed_rows=[AttributedRow(42, 3, 2.0, 1.0)],
    )
    persist_recipe_result(
        db, grocy_api, result, consume_date=date(2026, 6, 4),
        household_id=1, user_id=1,
    )
    db.commit()

    rows = db.query(ConsumedProduct).all()
    assert len(rows) == 1
    assert rows[0].recipe_grocy_id == 75
    assert rows[0].originating_recipe_grocy_id == 3


def test_split_rows_reconcile_to_stock_log_total():
    """A leaf spanning two origins must sum EXACTLY to the consumed total
    (ADR-0001 reconciliation invariant — no rounding drift)."""
    resolved = [
        {"product_id": 20, "product_id_effective": 20, "recipe_amount": 1.0,
         "is_nested_recipe_pos": 1, "child_recipe_id": 3},
        {"product_id": 20, "product_id_effective": 20, "recipe_amount": 4.0,
         "is_nested_recipe_pos": 0, "child_recipe_id": 75},
    ]
    result = build_recipe_result(
        top_level_recipe_id=75, shadow_id=-1,
        stock_log=[{"product_id": 20, "amount": -10.0, "price": 0.33}],
        resolved=resolved, parent_lookup=lambda pid: None,
    )
    rows = result.attributed_rows
    assert len(rows) == 2
    assert round(sum(r.amount for r in rows), 4) == 10.0
    assert round(sum(r.cost for r in rows), 4) == round(10.0 * 0.33, 4)
    # origins distinct
    assert {r.originating_recipe_grocy_id for r in rows} == {3, 75}
