# Bundle-recipe fresh-sugar attribution is resolved and stored at consume time

## Status

accepted

## Context

A local-only `Recipe.is_bundle` flag marks recipes that are not real cooked dishes
but just groupings of products eaten together (e.g. "Вечеря №5"). For a bundle, the
fresh-sugar exclusion that normally applies only to standalone products
(`is_fresh AND recipe_grocy_id IS NULL`) must also apply to fresh products consumed
inside the bundle — and, per the user, this must work even when a bundle is **nested
as a sub-recipe inside a different consumed dish** ("real and common").

The daily sugar total is computed live at read time and the read paths never call
Grocy. But knowing which sub-recipe a consumed leaf product originated from requires
Grocy data (`recipes_pos_resolved`) only available at consume time.

## Decision

Resolve each consumed product's **originating** sub-recipe at consume time and store
it on `ConsumedProduct.originating_recipe_grocy_id` (the REAL, positive grocy id from
`recipes_pos_resolved.child_recipe_id` when `is_nested_recipe_pos`, else the
top-level `meal["recipe_id"]`). The daily aggregation joins
`COALESCE(originating_recipe_grocy_id, recipe_grocy_id)` to `Recipe.is_bundle`.

This requires rewriting the consume save-loop from "one `ConsumedProduct` per
`stock_log` leaf" to "one row per `recipes_pos_resolved` position (carrying its
`child_recipe_id`)", with each effective product's planned position amounts **scaled
to match the authoritative `stock_log` consumed totals**. A leaf split across a
bundle and a non-bundle origin therefore becomes multiple rows with proportionally
split quantity/cost.

## Considered options

- **Freeze a `sugar_excluded` boolean at consume time** — simpler reads, but loses
  retroactivity (toggling `is_bundle` later wouldn't re-classify past days), which
  conflicts with the project's "retroactive by design" principle. Rejected.
- **Keep one row per `stock_log` leaf, attribute by any/dominant bundle origin** —
  much smaller change, but over-excludes when one product spans a bundle and a
  non-bundle origin in the same consumption. Rejected.
- **Flag on the sub-recipe / walk `recipes_nestings`** — unnecessary:
  `recipes_pos_resolved.child_recipe_id` already gives the real originating
  sub-recipe id directly, with no shadow→real mapping or tree walk.

## Consequences

- The authoritative consumption-recording logic changes shape; amount reconciliation
  against `stock_log` must stay correct (substitutions, rounding).
- Historical `ConsumedProduct` rows have NULL `originating_recipe_grocy_id` and fall
  back to `recipe_grocy_id` (top-level) — top-level bundles still work retroactively;
  nested attribution is simply absent for pre-feature data. No backfill job.
- `is_bundle` is local-only (never synced to Grocy), mirroring `is_fresh`.
- Attribution **degrades gracefully**: `child_recipe_id` is only used as the
  originating id when it is a real positive recipe id; a missing / zero /
  shadow / non-numeric value falls back to the top-level recipe rather than
  storing an id that can never match a `Recipe`. So if the Grocy
  `recipes_pos_resolved` schema assumption is ever wrong, nested attribution
  becomes an inert no-op (sugars simply not excluded) — never a crash or a
  wrongly-attributed row.
