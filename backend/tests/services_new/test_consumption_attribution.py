from app.services.consumption_attribution import (
    AttributedRow,
    attribute_consumed_products,
    index_origins,
    origins_for_product,
    split_amount,
)


class TestIndexOrigins:
    """index_origins maps product id -> [(origin_recipe_id, planned_amount)].
    Each resolved position is indexed under BOTH its effective product id and
    its planned product_id, so a substituted child can recover origin via parent.
    """

    def test_nested_position_indexed_by_both_ids(self):
        resolved = [
            {
                "product_id": 26,
                "product_id_effective": 491,
                "recipe_amount": 2.0,
                "is_nested_recipe_pos": 1,
                "child_recipe_id": 3,
            }
        ]
        origins = index_origins(resolved, top_level_recipe_id=75)
        assert origins[491] == [(3, 2.0)]
        assert origins[26] == [(3, 2.0)]

    def test_non_nested_uses_top_level(self):
        resolved = [
            {
                "product_id": 11,
                "product_id_effective": 11,
                "recipe_amount": 3.0,
                "is_nested_recipe_pos": 0,
            }
        ]
        origins = index_origins(resolved, top_level_recipe_id=600)
        assert origins == {11: [(600, 3.0)]}

    def test_shadow_or_bad_child_falls_back_to_top_level(self):
        for bad in (0, -7, None, "abc"):
            resolved = [
                {
                    "product_id": 12,
                    "product_id_effective": 12,
                    "recipe_amount": 1.0,
                    "is_nested_recipe_pos": 1,
                    "child_recipe_id": bad,
                }
            ]
            origins = index_origins(resolved, top_level_recipe_id=600)
            assert origins == {12: [(600, 1.0)]}, f"bad child={bad!r}"

    def test_zero_planned_amount_skipped(self):
        resolved = [
            {"product_id_effective": 13, "recipe_amount": 0.0, "is_nested_recipe_pos": 0}
        ]
        assert index_origins(resolved, top_level_recipe_id=600) == {}


class TestOriginsForProduct:
    """Direct hit wins; else retry via parent_lookup; else None."""

    def test_direct_hit_skips_parent_lookup(self):
        calls = []

        def parent_lookup(pid):
            calls.append(pid)
            return None

        result = origins_for_product({491: [(3, 2.0)]}, 491, parent_lookup)
        assert result == [(3, 2.0)]
        assert calls == []

    def test_substituted_child_resolves_via_parent(self):
        result = origins_for_product(
            {26: [(3, 2.0)], 491: [(3, 2.0)]}, 42, lambda pid: 26
        )
        assert result == [(3, 2.0)]

    def test_no_parent_returns_none(self):
        assert origins_for_product({26: [(3, 2.0)]}, 99, lambda pid: None) is None

    def test_parent_not_a_position_returns_none(self):
        assert origins_for_product({999: [(3, 2.0)]}, 42, lambda pid: 26) is None

    def test_parent_lookup_none_for_missing(self):
        assert origins_for_product({26: [(3, 2.0)]}, 42, lambda pid: 0) is None


class TestSplitAmount:
    def test_no_origins_uses_fallback(self):
        assert split_amount(5.0, 2.0, None, fallback_origin=75) == [(75, 5.0, 2.0)]

    def test_single_origin(self):
        assert split_amount(5.0, 2.0, [(3, 1.0)], fallback_origin=75) == [(3, 5.0, 2.0)]

    def test_two_origins_split_proportionally_last_gets_remainder(self):
        rows = split_amount(10.0, 4.0, [(3, 1.0), (75, 4.0)], fallback_origin=99)
        assert rows[0] == (3, 2.0, 0.8)
        # last row gets remainder so it reconciles exactly to the total
        assert rows[1] == (75, 8.0, 3.2)
        assert round(sum(r[1] for r in rows), 4) == 10.0
        assert round(sum(r[2] for r in rows), 4) == 4.0

    def test_zero_planned_sum_uses_fallback(self):
        assert split_amount(5.0, None, [(3, 0.0)], fallback_origin=75) == [(75, 5.0, None)]

    def test_none_cost_propagates(self):
        rows = split_amount(10.0, None, [(3, 1.0), (75, 1.0)], fallback_origin=99)
        assert rows == [(3, 5.0, None), (75, 5.0, None)]


class TestAttributeConsumedProducts:
    """End-to-end seam: resolved positions + stock_log -> attributed rows."""

    def _resolved_recipe75(self):
        # Mirrors real Grocy data: bundle 75 nests sub-recipe 3. Spice slot
        # plans product 26 (effective 491). «Приправка» 42 is a child of 26.
        return [
            {"product_id": 25, "product_id_effective": 25, "recipe_amount": 100,
             "is_nested_recipe_pos": 1, "child_recipe_id": 3},
            {"product_id": 26, "product_id_effective": 491, "recipe_amount": 2,
             "is_nested_recipe_pos": 1, "child_recipe_id": 3},
            {"product_id": 76, "product_id_effective": 361, "recipe_amount": 25,
             "is_nested_recipe_pos": 0, "child_recipe_id": 75},
        ]

    def test_substituted_child_attributes_to_real_sub_recipe(self):
        # stock_log recorded the substituted child 42 (parent 26).
        stock_log = [{"product_id": 42, "amount": -2.0, "price": 0.5}]
        rows = attribute_consumed_products(
            resolved=self._resolved_recipe75(),
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=lambda pid: 26 if pid == 42 else None,
        )
        assert rows == [AttributedRow(grocy_product_id=42, originating_recipe_grocy_id=3,
                                      amount=2.0, cost=1.0)]

    def test_unmatched_product_falls_back_to_top_level(self):
        stock_log = [{"product_id": 999, "amount": -3.0, "price": 0.0}]
        rows = attribute_consumed_products(
            resolved=self._resolved_recipe75(),
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=lambda pid: None,
        )
        assert rows == [AttributedRow(grocy_product_id=999, originating_recipe_grocy_id=75,
                                      amount=3.0, cost=None)]

    def test_direct_effective_product_attributes_without_parent(self):
        stock_log = [{"product_id": 25, "amount": -100.0, "price": 0.1}]
        rows = attribute_consumed_products(
            resolved=self._resolved_recipe75(),
            stock_log=stock_log,
            top_level_recipe_id=75,
            parent_lookup=lambda pid: None,
        )
        assert rows == [AttributedRow(grocy_product_id=25, originating_recipe_grocy_id=3,
                                      amount=100.0, cost=10.0)]
