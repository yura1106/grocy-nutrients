# Consume Orchestration / Persistence Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the 415-line `execute_consumption` save-loop a test seam by separating the per-meal **decision** (what consumption happened + which rows should exist) from the **effect** (Grocy mutations + DB writes), so the recipe consume path can be tested end-to-end with a fake Grocy and no live world.

**Architecture:** Introduce a `ConsumedRecipeResult` dataclass describing everything a consumed recipe meal yields: the shadow id, the attributed `ConsumedProduct` rows (from the plan #1 attribution module), the `RecipeData` nutrient aggregate, and the meal-plan bookkeeping. A new `process_recipe_meal(...)` function performs the Grocy side-effects (fulfillment check, `consume_recipe`, read stock_log) and returns that result; persistence becomes a separate `persist_recipe_result(...)`. `execute_consumption` shrinks to a thin orchestrator: iterate meals, call the right processor, persist, collect skips, commit/rollback.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, pytest, SQLite in-memory test DB. All commands run inside Docker. Engineer does NOT run tests/make targets — user does.

**Sequencing note:** Depends on **plan #1** (the `attribute_consumed_products` module — `process_recipe_meal` calls it) and is much cleaner after **plan #3** (typed GrocyAPI methods — the processor calls `get_recipe_fulfillment`/`consume_recipe`/`get_resolved_positions`/`mark_meal_plan_done` instead of raw strings). **Do plans #3 then #1, then this.** This is the biggest and riskiest plan — it touches the authoritative consumption-recording logic blessed by ADR-0001; the per-position save-loop SHAPE must not change, only where its seam sits.

**Risk control:** This plan is behavior-preserving. After every task the existing `tests/api/test_consumption_endpoints.py` endpoint tests must still pass. ADR-0001's amount-reconciliation-against-stock_log invariant is the thing most at risk — Task 2's test asserts it directly on real captured data.

---

### Task 1: Define `ConsumedRecipeResult` and a pure result-builder over attributed rows

Pull the "what should this recipe meal produce" decision into a pure function that takes already-fetched Grocy data (stock_log + resolved positions + recipe object) and returns a result object. No Grocy calls, no DB.

**Files:**
- Create: `backend/app/services/consume_recipe.py`
- Test: `backend/tests/services_new/test_consume_recipe.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services_new/test_consume_recipe.py`:

```python
from app.services.consume_recipe import ConsumedRecipeResult, build_recipe_result


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.consume_recipe'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/consume_recipe.py`:

```python
"""Recipe-meal consumption: separates the DECISION (what a consumed recipe meal
produces) from the EFFECT (Grocy mutations + DB writes). build_recipe_result is
pure; process_recipe_meal (added later) wraps it with the Grocy side-effects.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from app.services.consumption_attribution import (
    AttributedRow,
    attribute_consumed_products,
)


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
```

> **Grilled correction (Task 1):** `stock_log` and `fulfillment` fields are added to
> `ConsumedRecipeResult` NOW, not in Task 4. The Task 1 test below asserts fields
> individually (not whole-object equality), so the extra fields don't break it.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consume_recipe.py backend/tests/services_new/test_consume_recipe.py
git commit -m "feat: add ConsumedRecipeResult + pure build_recipe_result"
```

---

### Task 2: Add `process_recipe_meal` (Grocy side-effects, returns the result)

Wrap the Grocy mutations + reads that currently sit inline in `execute_consumption`'s recipe branch. This is where fulfillment-skip lives. Returns either a result or a skip reason — no DB.

**Files:**
- Modify: `backend/app/services/consume_recipe.py`
- Test: `backend/tests/services_new/test_consume_recipe.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services_new/test_consume_recipe.py`:

```python
from unittest.mock import MagicMock

from app.services.consume_recipe import process_recipe_meal


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py::TestProcessRecipeMeal -v`
Expected: FAIL with `ImportError: cannot import name 'process_recipe_meal'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/consume_recipe.py`:

```python
from app.services.grocy_api import GrocyAPI, GrocyError


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py::TestProcessRecipeMeal -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consume_recipe.py backend/tests/services_new/test_consume_recipe.py
git commit -m "feat: add process_recipe_meal (Grocy side-effects, no DB)"
```

---

### Task 3: Add `persist_recipe_result` (DB writes only)

Move the persistence (one `_save_consumed_product` per attributed row + meal-plan bookkeeping) into a function that takes a `ConsumedRecipeResult` and writes it. No Grocy decisions.

**Files:**
- Modify: `backend/app/services/consume_recipe.py`
- Test: `backend/tests/services_new/test_consume_recipe.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services_new/test_consume_recipe.py`. This test uses the project's real conftest fixture **`db`** (a live `Session` with `Session(bind=connection)` rollback isolation — there is NO `session_factory`; the fixture is named `db` and is passed as a test parameter, like every other `services_new` test). Set `created_at` explicitly because SQLite won't fire `server_default`. It seeds one Product + ProductData so `_save_consumed_product` can resolve the row:

```python
from datetime import UTC, datetime, date

from app.models.product import ConsumedProduct, Product, ProductData
from app.services.consume_recipe import (
    ConsumedRecipeResult,
    persist_recipe_result,
)
from app.services.consumption_attribution import AttributedRow


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
```

> **Grilled correction:** the real fixture is `db` (confirmed in `tests/conftest.py:72`),
> NOT `session_factory` (which does not exist). `ConsumedProduct` lives in
> `app/models/product.py`, not `app/models/consumed_product.py`. `Product` has `active`
> (not `is_active`) and a REQUIRED `product_group_id` — both fixed above.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py::test_persist_writes_one_row_per_attributed_row -v`
Expected: FAIL with `ImportError: cannot import name 'persist_recipe_result'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/consume_recipe.py`. This calls the EXISTING `_save_consumed_product` in `consumption.py` (import it) so the per-row save behavior is unchanged:

```python
from datetime import date as _date

from sqlmodel import Session


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
```

(The `from ... import` is function-local to avoid a circular import: `consumption.py` will import this module in Task 4.)

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py::test_persist_writes_one_row_per_attributed_row -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consume_recipe.py backend/tests/services_new/test_consume_recipe.py
git commit -m "feat: add persist_recipe_result (DB writes from a recipe result)"
```

---

### Task 4: Rewire `execute_consumption`'s recipe branch to orchestrate the new functions

Replace the inline recipe-consume block in `execute_consumption` with: `process_recipe_meal` → on skip, collect; else `persist_recipe_result`. Keep the meal-plan-consumption dedup, `mark_done` denormalization, `RecipeData` accumulation, and commit/rollback in the orchestrator.

**Files:**
- Modify: `backend/app/services/consumption.py` (the recipe branch — real span **894-1152** as of 2026-06-05; the earlier "898-1090" estimate was stale)
- Test: existing `backend/tests/api/test_consumption_endpoints.py` must still pass

- [ ] **Step 1: Read the current recipe branch**

Run: `docker compose exec backend grep -n 'meal\["type"\] == "recipe"\|get_meal_plan_recipe\|consume_recipe\|_save_consumed_product\|recipe_total_nutrients\|MealPlanConsumption' app/services/consumption.py`
Expected: the recipe branch span and the bookkeeping pieces to preserve.

- [ ] **Step 2: Replace the recipe branch body**

In `backend/app/services/consumption.py`, within the recipe branch, replace the section that (a) fetched the shadow + fulfillment, (b) consumed, (c) read stock_log + resolved, (d) looped `_save_consumed_product` with:

```python
                from app.services.consume_recipe import (
                    persist_recipe_result,
                    process_recipe_meal,
                )

                try:
                    result, skip_reason = process_recipe_meal(grocy_api, meal)
                except GrocyError as e:
                    skipped_meals.append({
                        "meal_plan_id": meal["id"],
                        "recipe_name": recipe_name,
                        "reason": str(e),
                    })
                    continue

                if skip_reason is not None:
                    skipped_meals.append({
                        "meal_plan_id": meal["id"],
                        "recipe_name": recipe_name,
                        "reason": skip_reason,
                    })
                    continue

                shadow_id = result.shadow_id
                persist_recipe_result(
                    db, grocy_api, result, consume_date,
                    household_id=household_id, user_id=user_id,
                )
```

**BEFORE this block (unchanged, stays in the orchestrator):** the `recipe_data =
grocy_api.get_recipe(meal["recipe_id"])` fetch and `recipe_name` derivation (consumption.py
~896-897). `process_recipe_meal` does NOT fetch the top-level recipe — the orchestrator needs
`recipe_data` for `weight_per_serving`, `desired_servings`, and the linked-product nutrient
write-back, so it stays. (`recipe_name` is referenced in the skip branches above; it is in
scope because this fetch precedes them.)

**Keep AFTER this block, VERBATIM, in the orchestrator** — the full list (the original plan
under-counted this; ALL of it must survive or behavior regresses):

1. The `MealPlanConsumption` dedup insert (keyed on `meal["id"]`, stores `shadow_id`).
2. The local DB `_mark_meal_plan_done(...)` denormalization (`from app.services.meal_plan
   import mark_done`) — the LOCAL counterpart to the Grocy `mark_meal_plan_done` now done
   inside the processor. Both must stay paired.
3. `consumed_meals.append({...})`.
4. The `recipe_total_nutrients` dict init + the `for log_entry in result.stock_log` loop —
   which keeps BOTH bodies: (a) RecipeData nutrient accumulation, AND (b) the
   `consumed_products_list.append(...)`. **`consumed_products_list` is OUTER-scoped (inits at
   the top of `execute_consumption`) and feeds the API response** — dropping it silently loses
   every recipe-origin product from the response. This loop MUST iterate `result.stock_log`
   (the full unsplit amounts), never the per-origin split rows, or nutrient totals inflate.
5. `weight_per_serving` extraction from `recipe_data.get("product_id")`.
6. `_save_recipe_data(db, meal["recipe_id"], result.fulfillment, recipe_total_nutrients, ...)`
   — note it passes **`result.fulfillment`** (carried on the result; it drives
   `price_per_serving=fulfillment.get("costs")`).
7. The per-meal `db.commit()` / rollback (atomically wrapping items 1-6).
8. `update_grocy_product_nutrients(...)` (gated on `recipe_data.get("desired_servings")`).

The ONLY things this Step removes from the orchestrator are: the shadow lookup + fulfillment
fetch + consume + stock_log/resolved reads (→ `process_recipe_meal`) and the attribution +
`_save_consumed_product` loop (→ `persist_recipe_result`). Everything else above is unchanged;
the two reads it depended on (`stock_log`, `fulfillment`) now come off `result`.

- [ ] **Step 3: (no-op) — `stock_log` + `fulfillment` already on the dataclass**

These fields were added to `ConsumedRecipeResult` and `build_recipe_result` back in **Task 1**
(grilled correction, to avoid the dataclass changing shape mid-plan). Nothing to add here —
just confirm the orchestrator reads `result.stock_log` (item 4) and `result.fulfillment`
(item 6).

- [ ] **Step 4: Run the FULL consumption suite**

Run: `docker compose exec backend pytest tests/api/test_consumption_endpoints.py tests/services_new/test_consume_recipe.py tests/services_new/test_consumption_attribution.py -v`
Expected: PASS. The endpoint tests prove behavior is preserved end-to-end.

- [ ] **Step 5: Confirm the recipe branch shrank and no dead code remains**

Run: `docker compose exec backend grep -n "_save_consumed_product\|get_recipe_fulfillment\|consume_recipe" app/services/consumption.py`
Expected: `_save_consumed_product` still DEFINED (used by `persist_recipe_result` and the product branch) but NO LONGER called inside the recipe branch; fulfillment/consume calls gone from `execute_consumption` (moved to `process_recipe_meal`).

- [ ] **Step 6: Lint**

Run: `make lint-python`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/consumption.py backend/app/services/consume_recipe.py backend/tests/services_new/test_consume_recipe.py
git commit -m "refactor: orchestrate recipe consume via process_recipe_meal + persist_recipe_result"
```

---

### Task 5: Verify against real captured data (ADR-0001 reconciliation invariant)

A targeted test that the split rows reconcile EXACTLY to the stock_log total on a real two-origin case — the invariant ADR-0001 calls out as most at risk.

**Files:**
- Test: `backend/tests/services_new/test_consume_recipe.py`

- [ ] **Step 1: Write the test**

Append to `backend/tests/services_new/test_consume_recipe.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consume_recipe.py::test_split_rows_reconcile_to_stock_log_total -v`
Expected: PASS (the reconciliation logic is unchanged from `split_amount`; this locks it at the new seam).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services_new/test_consume_recipe.py
git commit -m "test: lock stock_log reconciliation invariant at the recipe-result seam"
```

---

## Self-Review

- **Spec coverage:** Candidate #2 = separate decision (what rows) from effect (Grocy + DB) so the recipe consume path is testable. ✓ Task 1 = pure decision; Task 2 = Grocy side-effects; Task 3 = DB persistence; Task 4 = thin orchestrator; Task 5 = ADR invariant lock. ✓
- **Placeholder scan:** Cleared. Task 3's fixture is now the real `db` (conftest.py:72), imports/`Product` fields fixed. No placeholders remain. ✓
- **Type consistency:** `ConsumedRecipeResult(top_level_recipe_id, shadow_id, attributed_rows, stock_log, fulfillment)` consistent across Tasks 1-4 (stock_log + fulfillment added in Task 1). `build_recipe_result` (now takes optional `fulfillment`) / `process_recipe_meal` (returns `tuple[result|None, str|None]`) / `persist_recipe_result` signatures stable. `AttributedRow(grocy_product_id, originating_recipe_grocy_id, amount, cost)` matches plan #1. ✓
- **Dependency on plan #1:** `attribute_consumed_products` and `AttributedRow` come from plan #1's `consumption_attribution.py`. Both DONE on `main`. ✓
- **Behavior preservation:** Task 4 keeps `get_recipe`, `MealPlanConsumption` dedup, local `_mark_meal_plan_done`, the full RecipeData + `consumed_products_list` loop, `weight_per_serving`, `_save_recipe_data` (fed `result.fulfillment`), commit/rollback, and `update_grocy_product_nutrients` in the orchestrator; `persist_recipe_result` reuses `_save_consumed_product`. The existing endpoint tests are the regression guard. ✓
- **Divergence:** `process_recipe_meal` guards `get_resolved_positions` (degrade to `[]`, never skip-after-consume); the known consume/DB non-atomicity is PRESERVED not widened — its fix is the deferred plan `2026-06-05-consume-grocy-db-divergence-fix.md`. ✓
- **ADR-0001:** SHAPE (per-position split, stock_log authoritative) unchanged; only the seam moves. Task 5 locks the reconciliation invariant. No ADR re-litigation. ✓

---

## Grilled-corrections log (2026-06-05)

Applied after a grill-with-docs interview (10 forks) + 3 reviewer subagents (architect/python/devops). See vault `Dev Logs/2026-06-05 — Orchestration persistence split plan grilled`.

1. `get_recipe(meal["recipe_id"])` stays in the orchestrator (Task 4 "BEFORE" note).
2. `consumed_products_list.append` kept in the RecipeData loop (outer-scoped → API response).
3. `get_resolved_positions` wrapped `try/except GrocyError: resolved=[]` in the processor.
4. Circular import broken by function-local imports both ways.
5. `persist_recipe_result` does not commit; per-meal commit stays in the orchestrator.
6. `stock_log` **and** `fulfillment` added to `ConsumedRecipeResult` in Task 1.
7. `_parent_lookup_factory` keeps the proven `int(parent)` body (mypy warn_return_any gate).
8. **[reviewer BLOCKER]** `fulfillment` carried on the result → orchestrator's `_save_recipe_data` (was silently dropped → NULL `price_per_serving`).
9. **[reviewer BLOCKER]** Task 4 "keep AFTER" list completed (`_save_recipe_data`, `weight_per_serving`, `update_grocy_product_nutrients` were missing).
10. **[reviewer BLOCKER]** Task 3 test: `from app.models.product import ConsumedProduct`; `Product(active=..., product_group_id=...)`; fixture `db` not `session_factory`.
