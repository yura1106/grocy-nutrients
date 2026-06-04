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
    """Everything a consumed recipe meal yields, decided without DB writes."""

    top_level_recipe_id: int
    shadow_id: int
    attributed_rows: list[AttributedRow] = field(default_factory=list)


def build_recipe_result(
    top_level_recipe_id: int,
    shadow_id: int,
    stock_log: list[dict],
    resolved: list[dict],
    parent_lookup: Callable[[int], int | None],
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
    )
```

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
    def _lookup(pid: int) -> int | None:
        try:
            return grocy_api.get_product(pid).get("parent_product_id")
        except GrocyError:
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
    """
    recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
    shadow_id = recipe_meal["id"]

    fulfillment = grocy_api.get_recipe_fulfillment(shadow_id)
    missing = fulfillment.get("missing_products_count", 0)
    if missing > 0:
        return None, f"Missing {missing} products"

    grocy_api.consume_recipe(shadow_id)
    grocy_api.mark_meal_plan_done(meal["id"])

    stock_log = (
        grocy_api.get(
            "/objects/stock_log",
            {"query[]": [f"recipe_id={shadow_id}", "transaction_type=consume"]},
        )
        or []
    )
    resolved = grocy_api.get_resolved_positions(shadow_id)

    result = build_recipe_result(
        top_level_recipe_id=meal["recipe_id"],
        shadow_id=shadow_id,
        stock_log=stock_log,
        resolved=resolved,
        parent_lookup=_parent_lookup_factory(grocy_api),
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

Append to `backend/tests/services_new/test_consume_recipe.py`. This test uses the project's in-memory DB fixture pattern (see `tests/conftest.py` — `Session(bind=connection)` rollback isolation; remember `created_at=datetime.now(UTC)` must be set explicitly because SQLite won't fire `server_default`). It seeds one Product + ProductData so `_save_consumed_product` can resolve the row:

```python
from datetime import UTC, datetime, date

from app.models.consumed_product import ConsumedProduct
from app.models.product import Product, ProductData
from app.services.consume_recipe import (
    ConsumedRecipeResult,
    persist_recipe_result,
)
from app.services.consumption_attribution import AttributedRow


def test_persist_writes_one_row_per_attributed_row(session_factory):
    # session_factory: project fixture yielding an isolated Session (see conftest)
    db = session_factory()
    product = Product(
        grocy_id=42, name="Приправка", is_active=True, household_id=1,
        qu_id_stock=82, created_at=datetime.now(UTC),
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

(Adjust `session_factory` to whatever the actual conftest fixture is named — confirm via `grep -n "def .*session\|def db" tests/conftest.py`. The assertion shape is the contract; the fixture wiring follows the existing pattern.)

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
- Modify: `backend/app/services/consumption.py` (the recipe branch ~lines 898-1090)
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

Keep AFTER this block (unchanged): the `MealPlanConsumption` dedup insert, the `_mark_meal_plan_done` denormalization call (both keyed on `shadow_id`), the `consumed_meals.append(...)`, the `RecipeData` nutrient-accumulation loop over `stock_log`, and the per-meal `db.commit()` / rollback.

IMPORTANT: the `RecipeData` accumulation loop needs `stock_log`. `process_recipe_meal` currently consumes it internally. To keep RecipeData working, add `stock_log` and `recipe_name` to `ConsumedRecipeResult` (extend the dataclass with `stock_log: list[dict] = field(default_factory=list)` and set it in `build_recipe_result`), then iterate `result.stock_log` for the nutrient aggregate. This keeps the orchestrator's RecipeData logic intact while moving the Grocy read into the processor.

- [ ] **Step 3: Extend `ConsumedRecipeResult` with `stock_log`**

In `backend/app/services/consume_recipe.py`, add to the dataclass and builder:

```python
@dataclass(frozen=True)
class ConsumedRecipeResult:
    top_level_recipe_id: int
    shadow_id: int
    attributed_rows: list[AttributedRow] = field(default_factory=list)
    stock_log: list[dict] = field(default_factory=list)
```

and in `build_recipe_result`, pass `stock_log=stock_log` when constructing the result. Update the Task 1 test if it asserts equality on the whole object (it asserts fields individually, so no change needed).

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
- **Placeholder scan:** One soft spot — Task 3's `session_factory` fixture name is marked "confirm via grep" because the exact conftest fixture name isn't quoted here. The assertion contract is concrete; only the fixture wiring follows the existing pattern. Flagged, not hidden. All other steps show full code. ✓
- **Type consistency:** `ConsumedRecipeResult(top_level_recipe_id, shadow_id, attributed_rows, stock_log)` consistent across Tasks 1-4. `build_recipe_result` / `process_recipe_meal` (returns `tuple[result|None, str|None]`) / `persist_recipe_result` signatures stable. `AttributedRow(grocy_product_id, originating_recipe_grocy_id, amount, cost)` matches plan #1. ✓
- **Dependency on plan #1:** `attribute_consumed_products` and `AttributedRow` come from plan #1's `consumption_attribution.py`. Stated in the header. ✓
- **Behavior preservation:** Task 4 keeps `MealPlanConsumption` dedup, `_mark_meal_plan_done`, RecipeData accumulation, commit/rollback in the orchestrator; `persist_recipe_result` reuses the existing `_save_consumed_product`. The existing endpoint tests are the regression guard. ✓
- **ADR-0001:** SHAPE (per-position split, stock_log authoritative) unchanged; only the seam moves. Task 5 locks the reconciliation invariant. No ADR re-litigation. ✓
