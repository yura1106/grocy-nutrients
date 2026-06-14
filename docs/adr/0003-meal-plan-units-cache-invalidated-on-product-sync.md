# Meal-plan units cache is invalidated on product sync

## Status

accepted

## Context

The meal-plan product-line UI offers a unit dropdown (e.g. "банка", "мілілітри")
and also relies on a `stock_to_grams_ml` factor to turn a planned amount into
nutrients. Both come from `get_or_load_units_for_product`, which reads Grocy's
`quantity_unit_conversions_resolved` endpoint and **caches the result in Redis for
24h** under `meal_plan:units:v2:household:{hh}:product:{pid}`.

Observed bug: a product was first synced with a non-standard stock unit ("банка")
and no unit conversions. A "банка ↔ мілілітри" conversion was then added in Grocy.
After a subsequent sync, "мілілітри" still could not be selected when adding a
meal-plan line — "the system doesn't see the conversion."

Root cause: the units cache is **Grocy-sourced but never invalidated**. Product
sync (`upsert_product`) updates only local product/nutrient rows; it does not touch
the units cache. So the stale 24h entry — built before the conversion existed —
kept serving the old unit list. The same staleness silently breaks
`compute_daily_totals`: a product cached with `stock_to_grams_ml: None` is dropped
as a "missing item" until the TTL expires.

Grocy's `*_resolved` conversions endpoint materializes both directions (and
transitive conversions), so the existing `to_qu_id == stock_qu_id` filter is
correct — this is purely a cache-coherence problem, not a filtering bug.

## Decision

Invalidate the units cache on product sync, at a single chokepoint:
`upsert_product`, on the **existing-product branch only** (a new product has no
cache entry). All sync paths — nightly bulk `sync_grocy_products`, per-product
`sync_single_grocy_product[_detailed]`, and meal-plan lazy sync — funnel through
`upsert_product`, so one eviction there covers every path.

The cache-key builder and an `invalidate_units_cache(household_id,
product_grocy_id)` helper move to a neutral module (`core/meal_plan_cache.py`)
imported by both `services/meal_plan.py` and `services/product.py`, avoiding a
circular import (`meal_plan` already lazy-imports `sync_single_grocy_product` from
`product`).

Eviction timing inside the still-open sync transaction is safe: the cache is
rebuilt from Grocy, not from our DB, so a rebuild is correct even if the sync
commit later rolls back, and even if a concurrent read re-populates between the
DEL and the commit.

## Considered options

- **Drastically lower the TTL** (e.g. 5–15 min). Simpler, but leaves a staleness
  window and multiplies Grocy calls for every meal-plan interaction. Rejected — it
  treats the symptom, not the root cause.
- **Manual "refresh units" button / cache-bust endpoint.** Puts the burden on the
  user to know the cache is stale; adds UI surface. Rejected as the primary fix.
- **Invalidate in each sync function separately.** More duplication and an easy
  path to forget when a new sync entrypoint is added. Rejected in favor of the
  single `upsert_product` chokepoint.

## Consequences

- The dropdown and `stock_to_grams_ml` reflect Grocy conversions after the next
  sync of that product, instead of up to 24h later.
- Each existing-product upsert during the nightly bulk sync issues one extra Redis
  DEL. Negligible at this scale.
- The 24h TTL is retained as a backstop for conversions changed directly in Grocy
  without a subsequent sync.
