"""Consumed-product attribution: stock_log leaves + resolved recipe positions
-> attributed ConsumedProduct rows (which originating sub-recipe each consumed
amount belongs to). Pure module — no DB, no live Grocy. The only external need,
resolving a product's parent for substitution fallback, is injected as a
callable. See docs/adr/0001-bundle-recipe-attribution-at-consume-time.md.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


def _coerce_real_recipe_id(value: str | int | float | None) -> int | None:
    """Return value as a real (positive) grocy recipe id, else None.

    Grocy's recipes_pos_resolved.child_recipe_id is expected to be the REAL
    positive sub-recipe id, but may be absent, non-numeric, or a shadow id (<=0).
    Anything that isn't a positive int is rejected.
    """
    if value is None:
        return None
    try:
        rid = int(value)
    except (TypeError, ValueError):
        return None
    return rid if rid > 0 else None


def index_origins(
    resolved: list[dict],
    top_level_recipe_id: int,
) -> dict[int, list[tuple[int, float]]]:
    """Map product id -> [(originating_recipe_grocy_id, planned_amount), ...].

    Each resolved position is indexed under BOTH its product_id_effective and
    its planned product_id, so a consumed child that is a parent/child
    substitution of the planned ingredient can recover the origin via its parent.
    """
    origins: dict[int, list[tuple[int, float]]] = {}
    for pos in resolved:
        effective_id = pos.get("product_id_effective")
        if effective_id is None:
            continue
        planned = abs(float(pos.get("recipe_amount", 0) or 0))
        if planned <= 0:
            continue
        origin = top_level_recipe_id
        if pos.get("is_nested_recipe_pos"):
            child_id = _coerce_real_recipe_id(pos.get("child_recipe_id"))
            if child_id is not None:
                origin = child_id
        entry = (origin, planned)
        keys = {effective_id}
        planned_id = pos.get("product_id")
        if planned_id is not None:
            keys.add(planned_id)
        for key in keys:
            origins.setdefault(key, []).append(entry)
    return origins


def origins_for_product(
    product_origins: dict[int, list[tuple[int, float]]],
    grocy_product_id: int,
    parent_lookup: Callable[[int], int | None],
) -> list[tuple[int, float]] | None:
    """Resolve origin(s) for an actually-consumed product.

    Direct hit on the indexed map wins. On a miss (the consumed product is a
    parent/child substitution of the planned ingredient), retry with the
    product's parent id via parent_lookup, which index_origins surfaces through
    the planned product_id. Returns None when neither resolves, so the caller
    falls back to the top-level recipe.
    """
    direct = product_origins.get(grocy_product_id)
    if direct is not None:
        return direct
    parent_id = _coerce_real_recipe_id(parent_lookup(grocy_product_id))
    if parent_id is None:
        return None
    return product_origins.get(parent_id)


def split_amount(
    total_amount: float,
    total_cost: float | None,
    origins: list[tuple[int, float]] | None,
    fallback_origin: int,
) -> list[tuple[int, float, float | None]]:
    """Split an authoritative consumed (amount, cost) across originating recipes.

    origins is the resolved-position breakdown (origin id, planned proportion).
    Split is proportional to planned amounts; with no origins (standalone or
    unmatched) the whole amount goes to fallback_origin. The final row receives
    the remainder so the split reconciles EXACTLY with the authoritative
    stock_log total (no rounding drift). Returns [(origin, amount, cost), ...].
    """
    if not origins:
        return [(fallback_origin, total_amount, total_cost)]
    planned_sum = sum(p for _, p in origins)
    if planned_sum <= 0:
        return [(fallback_origin, total_amount, total_cost)]

    rows: list[tuple[int, float, float | None]] = []
    assigned_amt = 0.0
    assigned_cost = 0.0
    for i, (origin, planned) in enumerate(origins):
        is_last = i == len(origins) - 1
        if is_last:
            amt = round(total_amount - assigned_amt, 4)
            cost = round(total_cost - assigned_cost, 4) if total_cost is not None else None
        else:
            frac = planned / planned_sum
            amt = round(total_amount * frac, 4)
            cost = round(total_cost * frac, 4) if total_cost is not None else None
            assigned_amt += amt
            assigned_cost += cost if cost is not None else 0.0
        rows.append((origin, amt, cost))
    return rows


@dataclass(frozen=True)
class AttributedRow:
    """One ConsumedProduct's worth of attributed consumption."""

    grocy_product_id: int
    originating_recipe_grocy_id: int
    amount: float
    cost: float | None


def attribute_consumed_products(
    resolved: list[dict],
    stock_log: list[dict],
    top_level_recipe_id: int,
    parent_lookup: Callable[[int], int | None],
) -> list[AttributedRow]:
    """Attribute each authoritative stock_log leaf to its originating recipe(s).

    stock_log is the AMOUNT authority (what Grocy actually deducted, including
    substitutions/rounding); resolved positions supply attribution + split
    proportions. A leaf spanning a bundle and a non-bundle origin yields
    multiple rows. Products that resolve to no position (directly or via parent)
    fall back to top_level_recipe_id.
    """
    product_origins = index_origins(resolved, top_level_recipe_id)
    rows: list[AttributedRow] = []
    for entry in stock_log:
        grocy_product_id = entry.get("product_id")
        if grocy_product_id is None:
            continue
        amount = abs(float(entry.get("amount", 0)))
        price_per_unit = float(entry.get("price", 0))
        cost = round(amount * price_per_unit, 4) if price_per_unit else None
        origins = origins_for_product(product_origins, grocy_product_id, parent_lookup)
        for origin_id, split_amt, split_cost in split_amount(
            amount, cost, origins, fallback_origin=top_level_recipe_id
        ):
            rows.append(
                AttributedRow(
                    grocy_product_id=grocy_product_id,
                    originating_recipe_grocy_id=origin_id,
                    amount=split_amt,
                    cost=split_cost,
                )
            )
    return rows
