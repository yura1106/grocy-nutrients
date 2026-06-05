# Consume Grocy↔DB Divergence Fix — Plan (deferred)

> **Status:** PLAN ONLY — not scheduled. Created 2026-06-05 during the grilling of the
> orchestration/persistence split (`2026-06-04-2-orchestration-persistence-split.md`).
> That split is **behavior-preserving** and deliberately does NOT fix this bug. This is
> the separate follow-up.

## The bug

`consume_recipe(shadow_id)` is an **irreversible Grocy mutation** (deducts stock, writes
stock_log) that is **not transactional** with the local Postgres commit. The recipe branch
of `execute_consumption` runs, in order:

1. `consume_recipe(shadow_id)` — Grocy stock deducted (consumption.py:914)
2. `grocy_api.mark_meal_plan_done(meal["id"])` — Grocy `done=1` flag (consumption.py:915)
3. read `stock_log` (consumption.py:920)
4. DB writes (MealPlanConsumption, ConsumedProduct rows, RecipeData) + per-meal `db.commit()`

If **any step after #1 raises GrocyError** (or DB commit fails), the meal is skipped with a
`reason`, **zero rows land in the DB**, but Grocy stock is already gone. The user sees
"meal skipped" and assumes nothing happened — silent data divergence.

### Why re-run makes it WORSE (the sharp edge)

Meal-plan dedup is keyed on the Grocy `done` flag: `if meal.get("done"): continue`
(consumption.py:769). But `mark_meal_plan_done` runs at step #2, *after* consume. So if step
#2 itself (or #3/#4) failed last time, `done` stays **false** → the next run calls
`consume_recipe` **again** → **stock is deducted twice in Grocy** while still zero DB rows.

This is the dangerous part: it's not just "DB missing a row," it's "Grocy double-charged."

### Status quo per ADR-0001

ADR-0001 acknowledges the consume-then-DB non-atomicity as an accepted property (hard to make
atomic without a distributed transaction across an external HTTP API). The split refactor must
not widen it; this plan would actually fix it.

## Goal

Make the recipe-consume path **idempotent and divergence-safe** so that:
- A failure after `consume_recipe` never leaves Grocy mutated with no local record.
- A re-run never double-consumes the same meal in Grocy.

## Candidate approaches (decide before implementing — ADR-worthy)

### A. Mark-done-first / claim-before-consume
Flip the local dedup key off the Grocy `done` flag onto a **local** claim row written BEFORE
`consume_recipe`. On entry, insert a `MealPlanConsumption` (or a dedicated claim) keyed by
`(meal_plan_id, date)`; if it already exists, skip — Grocy was already consumed. Then consume.
- Pro: re-run can never double-consume (the local claim is the gate, written first, committed).
- Con: a claim written but consume failing leaves a claim with no consumption → need a
  reconcile/cleanup path, or treat the claim as "attempted, verify against stock_log."

### B. Reconcile-on-reentry via stock_log
Before consuming, query Grocy stock_log for `recipe_id=shadow_id, transaction_type=consume`.
If rows already exist, the shadow was already consumed — **skip the consume, just (re)build
the DB rows** from the existing stock_log. Makes the whole branch idempotent against Grocy's
own record.
- Pro: self-healing — a previously-consumed-but-not-recorded meal gets its DB rows on re-run
  WITHOUT double-consuming.
- Con: extra Grocy read per meal; shadow_id must be recoverable on re-run (it is —
  `get_meal_plan_recipe(day, meal_id)`).

### C. Outbox / two-phase
Persist intent locally, commit, then perform Grocy mutation, then mark complete. Heaviest;
likely overkill for a single-user-household self-hosted app.

**Lean:** **B (reconcile-on-reentry via stock_log)** — it directly kills the double-consume
re-run and self-heals divergence, reuses the stock_log read the branch already does, and needs
no schema change. Possibly combined with making post-consume Grocy reads/`mark_done`
**best-effort** (catch GrocyError, default to `[]`, never skip-after-consume) so a transient
read failure no longer drops the DB write.

## Sketch (approach B)

In `process_recipe_meal` (after the split lands):
1. `shadow_id = get_meal_plan_recipe(...)`
2. fulfillment skip check (unchanged — this is pre-consume, clean skip is correct)
3. read stock_log for `recipe_id=shadow_id, consume` FIRST.
   - if non-empty → already consumed; skip `consume_recipe`, proceed to build result from it.
   - if empty → `consume_recipe(shadow_id)`, then re-read stock_log.
4. `mark_meal_plan_done` and `get_resolved_positions` → best-effort (GrocyError → degrade,
   never re-raise once consume has happened).

Then the meal is recorded exactly once regardless of how many times the batch is re-run.

## Risks / open questions
- Does Grocy ever write a partial stock_log for a half-failed consume? If so, "non-empty
  stock_log" is not a clean "fully consumed" signal — need to confirm consume is atomic on
  Grocy's side.
- `_save_recipe_data` / `update_grocy_product_nutrients` idempotency on re-run (RecipeData rows
  would duplicate unless deduped like MealPlanConsumption).

## Tests
- Re-run after simulated post-consume GrocyError → exactly one set of DB rows, no second
  `consume_recipe` call.
- Re-run after simulated DB-commit failure → second run records the rows (self-heal), no
  double-consume.

## ADR
This is **ADR-worthy** (hard to reverse: changes the consume idempotency contract; surprising:
a future reader will wonder why consume reads stock_log before mutating; real trade-off:
B vs A vs C). Write `docs/adr/0002-consume-idempotency-and-divergence.md` when the approach is
chosen.
