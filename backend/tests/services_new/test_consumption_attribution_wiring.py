"""Wiring tests for the consume save-loop's use of consumption_attribution.

The save-loop builds a `_parent_lookup` closure over `grocy_api` and guards the
resolved-positions fetch. These behaviors are the glue the pure module
deliberately externalizes, so they get their own tests here. `_parent_lookup`
is a local closure (not importable); we reconstruct its exact semantics and
assert the three contract guarantees the wiring must hold.
"""

from unittest.mock import MagicMock

from app.services.consumption_attribution import attribute_consumed_products
from app.services.grocy_api import GrocyError


def _make_parent_lookup(grocy_api):
    # EXACT reconstruction of the closure built in
    # consumption.py's consume save-loop. Keep in sync with that code.
    def _parent_lookup(pid: int):
        try:
            parent = grocy_api.get_product(pid).get("parent_product_id")
        except GrocyError:
            return None
        if parent is None:
            return None
        try:
            return int(parent)
        except (TypeError, ValueError):
            return None

    return _parent_lookup


class TestParentLookupConsultedOnlyOnMiss:
    def test_direct_effective_hit_does_not_call_get_product(self):
        grocy_api = MagicMock()
        resolved = [
            {
                "product_id": 25,
                "product_id_effective": 25,
                "recipe_amount": 100,
                "is_nested_recipe_pos": 1,
                "child_recipe_id": 3,
            },
        ]
        stock_log = [{"product_id": 25, "amount": -100.0, "price": 0.0}]
        rows = attribute_consumed_products(
            resolved=resolved,
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=_make_parent_lookup(grocy_api),
        )
        assert rows[0].originating_recipe_grocy_id == 3
        grocy_api.get_product.assert_not_called()

    def test_unmatched_child_calls_get_product_for_parent(self):
        grocy_api = MagicMock()
        grocy_api.get_product.return_value = {"parent_product_id": "26"}
        resolved = [
            {
                "product_id": 26,
                "product_id_effective": 491,
                "recipe_amount": 2,
                "is_nested_recipe_pos": 1,
                "child_recipe_id": 3,
            },
        ]
        stock_log = [{"product_id": 42, "amount": -2.0, "price": 0.0}]
        rows = attribute_consumed_products(
            resolved=resolved,
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=_make_parent_lookup(grocy_api),
        )
        # parent "26" (a STRING, as Grocy returns) resolves to sub-recipe 3
        assert rows[0].originating_recipe_grocy_id == 3
        grocy_api.get_product.assert_called_once_with(42)


class TestParentLookupSwallowsGrocyError:
    def test_grocy_error_falls_back_to_top_level(self):
        grocy_api = MagicMock()
        grocy_api.get_product.side_effect = GrocyError("boom")
        resolved = [
            {
                "product_id": 26,
                "product_id_effective": 491,
                "recipe_amount": 2,
                "is_nested_recipe_pos": 1,
                "child_recipe_id": 3,
            },
        ]
        stock_log = [{"product_id": 42, "amount": -2.0, "price": 0.0}]
        rows = attribute_consumed_products(
            resolved=resolved,
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=_make_parent_lookup(grocy_api),
        )
        # get_product raised -> parent None -> fall back to top-level recipe 75
        assert rows[0].originating_recipe_grocy_id == 75


class TestResolvedPositionsGuard:
    def test_empty_resolved_attributes_everything_to_top_level(self):
        # Mirrors the call-site guard: get_resolved_positions raising GrocyError
        # degrades to resolved=[], so every leaf attributes to top-level.
        grocy_api = MagicMock()
        stock_log = [{"product_id": 42, "amount": -2.0, "price": 0.0}]
        rows = attribute_consumed_products(
            resolved=[],
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=_make_parent_lookup(grocy_api),
        )
        assert rows[0].originating_recipe_grocy_id == 75
        # with no resolved positions there is nothing to look up a parent for,
        # but even if consulted it must not crash
