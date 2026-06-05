"""Recipe-meal consumption: separates the DECISION (what a consumed recipe meal
produces) from the EFFECT (Grocy mutations + DB writes). build_recipe_result is
pure; process_recipe_meal (added later) wraps it with the Grocy side-effects.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date as _date

from sqlmodel import Session

from app.services.consumption_attribution import (
    AttributedRow,
    attribute_consumed_products,
)
from app.services.grocy_api import GrocyAPI, GrocyError


@dataclass(frozen=True)
class ConsumedRecipeResult:
    """Everything a consumed recipe meal yields, decided without DB writes.

    stock_log AND fulfillment are carried (not just attributed_rows) because the
    orchestrator still needs them AFTER the split: stock_log drives the RecipeData
    nutrient accumulation + the outer consumed_products_list (origin-agnostic, full
    unsplit amounts); fulfillment drives _save_recipe_data's price_per_serving
    (=fulfillment["costs"]) and the linked-product nutrient write-back gate. Added
    here in Task 1 (NOT deferred) so the dataclass never changes shape mid-plan.
    """

    top_level_recipe_id: int
    shadow_id: int
    attributed_rows: list[AttributedRow] = field(default_factory=list)
    stock_log: list[dict] = field(default_factory=list)
    fulfillment: dict = field(default_factory=dict)


def build_recipe_result(
    top_level_recipe_id: int,
    shadow_id: int,
    stock_log: list[dict],
    resolved: list[dict],
    parent_lookup: Callable[[int], int | None],
    fulfillment: dict | None = None,
) -> ConsumedRecipeResult:
    """Pure: turn fetched Grocy data into the rows that should be persisted."""
    rows = attribute_consumed_products(
        resolved=resolved,
        stock_log=stock_log,
        top_level_recipe_id=top_level_recipe_id,
        parent_lookup=parent_lookup,
    )
    return ConsumedRecipeResult(
        top_level_recipe_id=top_level_recipe_id,
        shadow_id=shadow_id,
        attributed_rows=rows,
        stock_log=stock_log,
        fulfillment=fulfillment or {},
    )


def _parent_lookup_factory(grocy_api: GrocyAPI) -> Callable[[int], int | None]:
    """Build the parent_product_id lookup attribution needs for substitutions.

    Body is the PROVEN version ported verbatim from the pre-split consume loop:
    it MUST int()-coerce because Grocy returns parent_product_id as a STRING
    ("26"), and it must launder to a clean int|None — get_product is untyped so
    .get(...) is Any, and returning Any from int|None trips mypy warn_return_any
    (a hard CI gate). Do NOT slim this to a bare `.get(...)` return.
    """

    def _lookup(pid: int) -> int | None:
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

    return _lookup


def process_recipe_meal(
    grocy_api: GrocyAPI,
    meal: dict,
) -> tuple[ConsumedRecipeResult | None, str | None]:
    """Drive Grocy for one recipe meal; return (result, skip_reason).

    Checks fulfillment (skips on missing products WITHOUT consuming), consumes
    the shadow recipe, marks the meal done, then reads the authoritative
    stock_log + resolved positions and builds the result. No DB writes.

    Divergence rule (grilled): a GrocyError BEFORE consume is a clean skip (bubbles
    to the orchestrator). But once consume_recipe has run, Grocy stock is already
    deducted — get_resolved_positions failing must NOT abort recording, so it
    degrades to [] (mirrors the pre-split loop). The post-consume stock_log read and
    mark_meal_plan_done keep their pre-split behavior (a GrocyError there still
    bubbles → skip), preserving — not widening — the known consume/DB divergence.
    Fixing that divergence is the separate deferred plan
    docs/superpowers/plans/2026-06-05-consume-grocy-db-divergence-fix.md.
    """
    recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
    shadow_id = recipe_meal["id"]

    fulfillment = grocy_api.get_recipe_fulfillment(shadow_id)
    missing = fulfillment.get("missing_products_count", 0)
    if missing > 0:
        return None, f"Missing {missing} products"

    grocy_api.consume_recipe(shadow_id)
    # Grocy "done" flag (UI). The LOCAL DB done denormalization is a separate call
    # the orchestrator still owns (meal_plan.mark_done) — keep them paired.
    grocy_api.mark_meal_plan_done(meal["id"])

    stock_log = (
        grocy_api.get(
            "/objects/stock_log",
            {"query[]": [f"recipe_id={shadow_id}", "transaction_type=consume"]},
        )
        or []
    )
    # Guarded: a post-consume GrocyError here must degrade to fallback attribution,
    # NOT skip the meal Grocy already consumed. Verbatim from the pre-split loop.
    try:
        resolved = grocy_api.get_resolved_positions(shadow_id)
    except GrocyError:
        resolved = []

    result = build_recipe_result(
        top_level_recipe_id=meal["recipe_id"],
        shadow_id=shadow_id,
        stock_log=stock_log,
        resolved=resolved,
        parent_lookup=_parent_lookup_factory(grocy_api),
        fulfillment=fulfillment,
    )
    return result, None


def persist_recipe_result(
    db: Session,
    grocy_api: GrocyAPI,
    result: ConsumedRecipeResult,
    consume_date: _date,
    household_id: int | None,
    user_id: int | None,
) -> None:
    """Persist a ConsumedRecipeResult: one ConsumedProduct per attributed row.

    Reuses consumption._save_consumed_product so per-row save (unit conversion,
    latest-data lookup) behavior is identical to the pre-split loop.
    """
    from app.services.consumption import _save_consumed_product

    for row in result.attributed_rows:
        _save_consumed_product(
            db,
            grocy_api,
            row.grocy_product_id,
            row.amount,
            consume_date,
            recipe_grocy_id=result.top_level_recipe_id,
            recipe_grocy_id_shadow=result.shadow_id,
            originating_recipe_grocy_id=row.originating_recipe_grocy_id,
            household_id=household_id,
            user_id=user_id,
            cost=row.cost,
        )
