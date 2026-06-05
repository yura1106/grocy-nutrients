# Consumed-Product Attribution Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the stock_log-leaf → attributed-`ConsumedProduct`-rows decision into one deep module with a single interface, so the resolve→origins→split glue (where the «Приправка» substitution bug lived) is testable with captured Grocy JSON and no DB.

**Architecture:** A new pure module `app/services/consumption_attribution.py` exposes one function, `attribute_consumed_products(...)`, taking the resolved positions, the stock_log leaves, the top-level recipe id, and a `parent_lookup` callable. It returns a flat list of `AttributedRow` rows (grocy_product_id, originating_recipe_grocy_id, amount, cost). The four existing helpers (`_resolve_product_origins`, `_origins_for_consumed_product`, `_split_consumed_amount`, `_coerce_real_recipe_id`) move into it as private implementation. The consume save-loop in `consumption.py` calls the new function once per meal and just persists.

**Tech Stack:** Python 3.11 (per `backend/mypy.ini`; `from __future__ import annotations` keeps the `int | None` / `list[dict]` / `Callable[...]` annotations valid), FastAPI, SQLModel, pytest. All commands run inside Docker (`docker compose exec backend ...`). Per project rules, the implementing engineer does NOT run tests, `make`/lint targets, or `git commit` — **the USER runs every `pytest` / `make lint-python` / `git commit` step below**; they are listed for reference only, treat them as the user's action.

**Sequencing note:** This plan is independent but reads cleaner after plan #3 (typed GrocyAPI methods). It can be done first; the `parent_lookup` callable abstracts the only Grocy call the attribution logic needs, so it does not depend on #3.

---

### Task 1: Create the attribution module skeleton with the row type and Grocy-free origin indexing

**Files:**
- Create: `backend/app/services/consumption_attribution.py`
- Test: `backend/tests/services_new/test_consumption_attribution.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services_new/test_consumption_attribution.py`:

```python
from app.services.consumption_attribution import index_origins


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.consumption_attribution'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/consumption_attribution.py`:

```python
"""Consumed-product attribution: stock_log leaves + resolved recipe positions
-> attributed ConsumedProduct rows (which originating sub-recipe each consumed
amount belongs to). Pure module — no DB, no live Grocy. The only external need,
resolving a product's parent for substitution fallback, is injected as a
callable. See docs/adr/0001-bundle-recipe-attribution-at-consume-time.md.
"""

from __future__ import annotations


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumption_attribution.py backend/tests/services_new/test_consumption_attribution.py
git commit -m "feat: add consumption_attribution.index_origins (Grocy-free origin indexing)"
```

---

### Task 2: Add origins-for-product with injected parent lookup

**Files:**
- Modify: `backend/app/services/consumption_attribution.py`
- Test: `backend/tests/services_new/test_consumption_attribution.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services_new/test_consumption_attribution.py`:

```python
from app.services.consumption_attribution import origins_for_product


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py::TestOriginsForProduct -v`
Expected: FAIL with `ImportError: cannot import name 'origins_for_product'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/consumption_attribution.py`:

```python
from collections.abc import Callable


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py::TestOriginsForProduct -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumption_attribution.py backend/tests/services_new/test_consumption_attribution.py
git commit -m "feat: add origins_for_product with injected parent lookup"
```

---

### Task 3: Add the proportional amount split

**Files:**
- Modify: `backend/app/services/consumption_attribution.py`
- Test: `backend/tests/services_new/test_consumption_attribution.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services_new/test_consumption_attribution.py`:

```python
from app.services.consumption_attribution import split_amount


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py::TestSplitAmount -v`
Expected: FAIL with `ImportError: cannot import name 'split_amount'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/consumption_attribution.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py::TestSplitAmount -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumption_attribution.py backend/tests/services_new/test_consumption_attribution.py
git commit -m "feat: add split_amount proportional reconciliation"
```

---

### Task 4: Add the top-level `attribute_consumed_products` interface (the seam)

This is the deep interface the whole module exists for: feed it captured Grocy JSON, get attributed rows. This is the test the «Приправка» bug needed and could not have at the helper level.

**Files:**
- Modify: `backend/app/services/consumption_attribution.py`
- Test: `backend/tests/services_new/test_consumption_attribution.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services_new/test_consumption_attribution.py`:

```python
from app.services.consumption_attribution import (
    AttributedRow,
    attribute_consumed_products,
)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py::TestAttributeConsumedProducts -v`
Expected: FAIL with `ImportError: cannot import name 'AttributedRow'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/consumption_attribution.py` (add `from dataclasses import dataclass` at top):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py::TestAttributeConsumedProducts -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumption_attribution.py backend/tests/services_new/test_consumption_attribution.py
git commit -m "feat: add attribute_consumed_products top-level seam"
```

---

### Task 5: Wire the consume save-loop to the new module; delete the moved helpers

**Files:**
- Modify: `backend/app/services/consumption.py` (the recipe consume loop ~lines 998-1027; the helper defs `_resolve_product_origins`, `_origins_for_consumed_product`, `_split_consumed_amount`, `_coerce_real_recipe_id` ~lines 1192-1340)
- Modify: `backend/tests/api/test_consumption_endpoints.py` (the helper test classes now import from the new module, OR are deleted in favor of the new module's tests)

- [ ] **Step 1: Read the current call site and helpers**

Run: `docker compose exec backend grep -n "_resolve_product_origins\|_origins_for_consumed_product\|_split_consumed_amount\|_coerce_real_recipe_id\|product_origins" app/services/consumption.py`
Expected: the call site in the consume loop and the four helper definitions.

- [ ] **Step 2: Replace the in-loop attribution with the new module**

In `backend/app/services/consumption.py`, add the import near the other service imports at the top of the file:

```python
from app.services.consumption_attribution import attribute_consumed_products
```

Replace the per-`stock_log`-leaf block (the `for log_entry in stock_log:` body that builds `origin_rows` and calls `_save_consumed_product`) so the attribution comes from the module. The loop currently looks like:

```python
                for log_entry in stock_log:
                    grocy_product_id = log_entry.get("product_id")
                    amount = abs(float(log_entry.get("amount", 0)))
                    price_per_unit = float(log_entry.get("price", 0))
                    entry_cost = round(amount * price_per_unit, 4) if price_per_unit else None

                    origins = _origins_for_consumed_product(
                        grocy_api, product_origins, grocy_product_id
                    )
                    origin_rows = _split_consumed_amount(
                        amount,
                        entry_cost,
                        origins,
                        fallback_origin=meal["recipe_id"],
                    )

                    for originating_id, split_amount, split_cost in origin_rows:
                        _save_consumed_product(
                            db,
                            grocy_api,
                            grocy_product_id,
                            split_amount,
                            consume_date,
                            recipe_grocy_id=meal["recipe_id"],
                            recipe_grocy_id_shadow=shadow_id,
                            originating_recipe_grocy_id=originating_id,
                            household_id=household_id,
                            user_id=user_id,
                            cost=split_cost,
                        )
                    # ... nutrient accumulation below stays
```

Change it to compute attributed rows once before the loop, then persist.

**RESOLVED (grill 2026-06-05): plan #3 is already merged on `main`.** The live code at
`consumption.py` already calls `grocy_api.get_resolved_positions(shadow_id)` (the typed
method). So the `_resolve_positions` raw-`get()` helper below is **dead — do not write it**.
Call the typed method directly at the call site and own the `try/except GrocyError` there
(the pure module no longer swallows it, by design):

```python
                try:
                    resolved = grocy_api.get_resolved_positions(shadow_id)
                except GrocyError:
                    resolved = []

                def _parent_lookup(pid: int) -> int | None:
                    # Launder to a typed value before returning. get_product is
                    # untyped -> .get(...) is Any, and returning Any from an
                    # int|None function trips mypy warn_return_any (hard CI gate,
                    # mypy.ini). MUST accept a STRING parent_product_id like "26"
                    # (Grocy returns ids as strings) — int(parent) does, matching
                    # live behavior; the architect review flagged that an
                    # isinstance(parent, int) check would wrongly reject string
                    # parents and break substitution resolution.
                    # origins_for_product re-validates the result via the module's
                    # _coerce_real_recipe_id (idempotent), so this only needs to
                    # produce a clean int|None, not a vetted positive recipe id.
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

                attributed = attribute_consumed_products(
                    resolved=resolved,
                    stock_log=stock_log,
                    top_level_recipe_id=meal["recipe_id"],
                    parent_lookup=_parent_lookup,
                )
                for row in attributed:
                    _save_consumed_product(
                        db,
                        grocy_api,
                        row.grocy_product_id,
                        row.amount,
                        consume_date,
                        recipe_grocy_id=meal["recipe_id"],
                        recipe_grocy_id_shadow=shadow_id,
                        originating_recipe_grocy_id=row.originating_recipe_grocy_id,
                        household_id=household_id,
                        user_id=user_id,
                        cost=row.cost,
                    )
```

(The old standalone `_resolve_positions` raw-`get()` helper described in earlier plan
drafts is **deleted** — plan #3's `get_resolved_positions` typed method supersedes it.)

**RESOLVED (grill 2026-06-05): loop split.** The old single `for log_entry in stock_log:`
loop did THREE things per leaf: (a) save `ConsumedProduct` rows, (b) accumulate recipe
nutrients (`recipe_total_nutrients` / `recipe_products_for_data`), (c) append to
`consumed_products_list`. Split into **two loops**:

- **Loop 1** over `attributed` (the `AttributedRow`s) → only `_save_consumed_product`.
- **Loop 2** over `stock_log` (unchanged) → nutrients (b) + `consumed_products_list` (c),
  recomputing `amount`/`entry_cost` from each `log_entry`.

This is verified cleanly separable: (b)/(c) share no mutable cross-leaf state with the
save; `entry_cost` is trivially recomputed from `log_entry`. **Loop 2 MUST iterate
`stock_log`, never `attributed`** — `RecipeData` is the top-level recipe aggregate
(origin-agnostic, full unsplit amount per ADR-0001); iterating the per-origin split rows
would inflate recipe nutrient totals. `_save_consumed_product` already calls
`get_product_by_grocy_id` internally, so the split adds **no new** per-leaf Grocy/DB calls
vs today (the inline nutrient block already called it too) — behavior-preserving.

- [ ] **Step 3: Delete the four moved helpers from consumption.py**

Remove the definitions of `_resolve_product_origins`, `_origins_for_consumed_product`, `_split_consumed_amount`, and `_coerce_real_recipe_id` from `backend/app/services/consumption.py` (they now live in `consumption_attribution.py`). Confirm no other references remain:

Run: `docker compose exec backend grep -rn "_resolve_product_origins\|_origins_for_consumed_product\|_split_consumed_amount\|_coerce_real_recipe_id" app/`
Expected: no matches in `app/` (only the new module's internal use, which is `index_origins`/`origins_for_product`/`split_amount`/`_coerce_real_recipe_id` — different names except the coerce helper which is now private to the module).

- [ ] **Step 4: Delete the old helper tests AND write new call-site glue tests**

In `backend/tests/api/test_consumption_endpoints.py`, delete the now-obsolete test classes `TestSplitConsumedAmount`, `TestResolveProductOrigins`, `TestOriginsForConsumedProduct`, and `TestCoerceRealRecipeId`. Their *logic* is now covered by the pure-module tests in `tests/services_new/test_consumption_attribution.py` (Tasks 1–4). Keep `TestIsSugarExcluded` and `TestBundleRecipeSugarsExclusion` (read-path, unaffected).

**RESOLVED (grill 2026-06-05): don't just delete — write NEW, better glue tests.** The old helper tests tangled attribution logic with the Grocy-call wiring. The new pure-module tests cover the logic; the *wiring the pure module deliberately externalized* now needs its own tests. Add a small focused test class covering these THREE call-site behaviors (location is the engineer's call — either a new `tests/services_new/test_consumption_attribution_wiring.py` or a class in `tests/api/test_consumption_endpoints.py`, whichever reads cleanest once the call site is refactored):

1. **`_parent_lookup` is consulted only on a miss** — a direct effective-id hit does NOT call `grocy_api.get_product` (no N+1); an unmatched child DOES, reading `["parent_product_id"]`.
2. **`_parent_lookup` swallows `GrocyError`** → returns `None` → that leaf falls back to the top-level origin (never crashes).
3. **The resolved-positions call is guarded**: `grocy_api.get_resolved_positions(shadow_id)` wrapped in `try/except GrocyError → []`, so a Grocy failure degrades to "everything attributes to top-level" rather than raising.

- [ ] **Step 5: Run the full consumption suite**

Run: `docker compose exec backend pytest tests/services_new/test_consumption_attribution.py tests/api/test_consumption_endpoints.py -v`
Expected: PASS. No import errors from the deleted helpers.

- [ ] **Step 6: Lint**

Run: `make lint-python`
Expected: clean (ruff + mypy).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/consumption.py backend/tests/api/test_consumption_endpoints.py
# also add the new glue-test file if created as a separate file:
# git add backend/tests/services_new/test_consumption_attribution_wiring.py
git commit -m "refactor: route consume save-loop through consumption_attribution module"
```

---

## Self-Review

- **Spec coverage:** Candidate #1 = one deep attribution module with a single testable interface; the four helpers become private. ✓ Tasks 1-4 build the module bottom-up culminating in the `attribute_consumed_products` seam (Task 4); Task 5 wires it in and deletes the originals. ✓
- **Placeholder scan:** No TBD/TODO; all code shown. ✓
- **Type consistency:** `index_origins` / `origins_for_product` / `split_amount` / `attribute_consumed_products` / `AttributedRow(grocy_product_id, originating_recipe_grocy_id, amount, cost)` used consistently across tasks. `_parent_lookup` returns `parent_product_id` (an int|None), passed to `origins_for_product` which re-validates via `_coerce_real_recipe_id`. ✓
- **Domain language:** "originating sub-recipe", "bundle", "stock_log is the amount authority", "attribution" — matches CONTEXT.md and ADR-0001. ✓
- **Note:** Task 5's nutrient-accumulation loop must remain separate (origin-agnostic, full amount) — called out explicitly so the engineer doesn't fold it into the split rows.
