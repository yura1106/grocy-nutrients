# Typed GrocyAPI Methods Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the holes in the `GrocyAPI` interface where `consumption.py` reaches through it with raw `/objects/...` path strings and `query[]=...` encoding, by adding typed methods for the consumption endpoints actually used, so callers express intent and the Grocy REST quirks live in one file.

**Architecture:** Add five typed methods to `GrocyAPI` — `get_resolved_positions(shadow_id)`, `get_recipe_fulfillment(shadow_id)`, `consume_recipe(shadow_id)`, `mark_meal_plan_done(meal_id)`, and `get_recipe(recipe_id)` — each wrapping the raw `get`/`post`/`put` call (and its `query[]` encoding) currently inlined in `consumption.py`. Then replace the raw call sites. The generic `get`/`post`/`put`/`delete` stay (still used for genuinely one-off paths).

**Tech Stack:** Python 3.11 (mypy/ruff target; CI runner uses 3.14), FastAPI, httpx, pytest. All commands run inside Docker.

> **Per-session override (2026-06-04, grill-with-docs):** For THIS implementation session ONLY, the engineer (Claude) runs pytest, `make lint-python`, and makes the git commits. This is a deliberate one-time exception to the project's standing rule ("user runs tests/lint/make/git manually") — that standing rule is NOT changed.

**mypy note:** `backend/mypy.ini` sets `warn_return_any = true`. `GrocyAPI.get/post/put` are unannotated (return `Any`). Any new method with a declared non-`Any` return type that does `return self.get(...)` directly WILL fail the lint/CI gate (`mypy app` in `.github/workflows/ci.yml`). Follow the existing in-file idiom (`get_meal_plan`, lines 156-167): assign to an annotated local, then return it. Unannotated methods (`get_recipe`, `consume_recipe`, `mark_meal_plan_done`) are exempt but should still be annotated for consistency.

**Sequencing note:** Independent of plans #1 and #2, but doing it FIRST makes them cleaner — `_resolve_positions` in plan #1 Task 5 collapses to `get_resolved_positions`, and plan #2's orchestration tests mock typed methods instead of URL strings.

**Scope guard (YAGNI):** Only wrap endpoints that are called with raw strings in `consumption.py` today (verified: `/objects/recipes/{id}`, `/recipes/{shadow}/fulfillment`, `/recipes/{shadow}/consume`, `/objects/recipes_pos_resolved`, `PUT /objects/meal_plan/{id}` done-flag). Do NOT wrap `/stock/products/{id}` reads — those are widely used elsewhere and out of scope for this slice.

---

### Task 1: Add `get_recipe` and `get_resolved_positions`

**Files:**
- Modify: `backend/app/services/grocy_api.py` (near the existing typed methods, ~line 131 after `get_product`)
- Test: `backend/tests/services_new/test_grocy_api_methods.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services_new/test_grocy_api_methods.py`:

```python
from unittest.mock import MagicMock

from app.services.grocy_api import GrocyAPI


def _api():
    api = GrocyAPI.__new__(GrocyAPI)  # bypass __init__ (needs url/key)
    api.get = MagicMock()  # type: ignore[method-assign]
    api.post = MagicMock()  # type: ignore[method-assign]
    api.put = MagicMock()  # type: ignore[method-assign]
    return api


class TestGetRecipe:
    def test_calls_objects_recipes_path(self):
        api = _api()
        api.get.return_value = {"id": 75, "name": "Вечеря №1"}
        result = api.get_recipe(75)
        api.get.assert_called_once_with("/objects/recipes/75")
        assert result == {"id": 75, "name": "Вечеря №1"}


class TestGetResolvedPositions:
    def test_queries_recipes_pos_resolved_for_shadow(self):
        api = _api()
        api.get.return_value = [{"product_id_effective": 491}]
        result = api.get_resolved_positions(-44663)
        api.get.assert_called_once_with(
            "/objects/recipes_pos_resolved", {"query[]": ["recipe_id=-44663"]}
        )
        assert result == [{"product_id_effective": 491}]

    def test_none_response_returns_empty_list(self):
        api = _api()
        api.get.return_value = None
        assert api.get_resolved_positions(-44663) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_grocy_api_methods.py -v`
Expected: FAIL with `AttributeError: 'GrocyAPI' object has no attribute 'get_recipe'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/grocy_api.py` after `get_product`:

```python
    def get_recipe(self, recipe_id) -> dict:
        """Fetch a recipe object by id (shadow ids allowed)."""
        result: dict = self.get(f"/objects/recipes/{recipe_id}")
        return result

    def get_resolved_positions(self, shadow_id) -> list[dict]:
        """Resolved ingredient positions for a (shadow) recipe.

        Each position carries product_id, product_id_effective,
        is_nested_recipe_pos, child_recipe_id, recipe_amount. Returns [] when
        Grocy returns nothing (so callers can iterate unconditionally — note
        this hardens unguarded raw call sites that would TypeError on a None
        response; see Task 3 Step 2).
        """
        result: list[dict] = self.get(
            "/objects/recipes_pos_resolved",
            {"query[]": [f"recipe_id={shadow_id}"]},
        )
        return result or []
```

> Laundering via the annotated local (`result: dict = ...`) is required for `warn_return_any` — see the mypy note above.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_grocy_api_methods.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/grocy_api.py backend/tests/services_new/test_grocy_api_methods.py
git commit -m "feat: add GrocyAPI.get_recipe + get_resolved_positions typed methods"
```

---

### Task 2: Add `get_recipe_fulfillment`, `consume_recipe`, `mark_meal_plan_done`

**Files:**
- Modify: `backend/app/services/grocy_api.py`
- Test: `backend/tests/services_new/test_grocy_api_methods.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services_new/test_grocy_api_methods.py`:

```python
class TestGetRecipeFulfillment:
    def test_calls_fulfillment_path(self):
        api = _api()
        api.get.return_value = {"missing_products_count": 0}
        result = api.get_recipe_fulfillment(-44663)
        api.get.assert_called_once_with("/recipes/-44663/fulfillment")
        assert result == {"missing_products_count": 0}


class TestConsumeRecipe:
    def test_posts_consume_path(self):
        api = _api()
        api.consume_recipe(-44663)
        api.post.assert_called_once_with("/recipes/-44663/consume")


class TestMarkMealPlanDone:
    def test_puts_done_flag(self):
        api = _api()
        api.mark_meal_plan_done(5531)
        api.put.assert_called_once_with("/objects/meal_plan/5531", data={"done": 1})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/services_new/test_grocy_api_methods.py::TestConsumeRecipe -v`
Expected: FAIL with `AttributeError: 'GrocyAPI' object has no attribute 'consume_recipe'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/grocy_api.py`:

```python
    def get_recipe_fulfillment(self, shadow_id) -> dict:
        """Fulfillment summary for a shadow recipe (missing_products_count etc.)."""
        result: dict = self.get(f"/recipes/{shadow_id}/fulfillment")
        return result

    def consume_recipe(self, shadow_id):
        """Consume a shadow recipe in Grocy (deducts stock, writes stock_log)."""
        return self.post(f"/recipes/{shadow_id}/consume")

    def mark_meal_plan_done(self, meal_plan_id):
        """Flip a meal_plan entry's done flag in Grocy."""
        return self.put(f"/objects/meal_plan/{meal_plan_id}", data={"done": 1})
```

> `consume_recipe`/`mark_meal_plan_done` are intentionally unannotated on return (call sites discard the value); `post`/`put` return `Any` and there's no declared type to clash with `warn_return_any`.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/services_new/test_grocy_api_methods.py -v`
Expected: PASS (6 tests total)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/grocy_api.py backend/tests/services_new/test_grocy_api_methods.py
git commit -m "feat: add fulfillment/consume/mark-done typed GrocyAPI methods"
```

---

### Task 3: Replace raw call sites in `consumption.py`

**Files:**
- Modify: `backend/app/services/consumption.py`

- [ ] **Step 0: Add URL-level regression tests BEFORE swapping (the real safety net)**

The existing `tests/api/test_consumption_endpoints.py` mocks at the *service* boundary (`return_value`/`side_effect` on the service functions), so it does NOT exercise the raw `grocy_api.get(url)` calls — a wrong substitution (e.g. the line-1517 `recipe_meal['id']` site) would pass green. The swap also runs inside Celery workers (`execute_consumption`, `range_check`/`check_range_availability`, `day_check`/`check_products_availability`). So before touching call sites, pin the emitted-URL contract.

First check whether any existing test asserts on raw URLs (those would break after the swap and must be migrated to the typed-method name):

Run: `docker compose exec backend grep -rn "assert_called.*recipes\|side_effect.*recipes\|/objects/recipes\|recipes_pos_resolved" tests/ | grep -i consum`

Then create `backend/tests/services_new/test_consumption_grocy_calls.py` that, for each rewritten loop entry point (`check_products_availability`, `check_range_availability`, the save-loop in `execute_consumption`, and the aggregation path at ~1517), invokes the function with a `GrocyAPI` whose `get/post/put` are `MagicMock`s and asserts the **exact** paths/params emitted (`/objects/recipes/{id}`, `/recipes/{shadow}/fulfillment`, `/objects/recipes_pos_resolved` with `{"query[]": ["recipe_id=..."]}`, `/recipes/{shadow}/consume`, `PUT /objects/meal_plan/{id}` `data={"done": 1}`). These tests must pass against the CURRENT (pre-swap) code first — that's what makes them a regression net.

Run: `docker compose exec backend pytest tests/services_new/test_consumption_grocy_calls.py -v`
Expected: PASS against pre-swap code.

- [ ] **Step 1: Inventory the raw calls to replace**

Run: `docker compose exec backend grep -n 'grocy_api\.get(f"/objects/recipes/\|/fulfillment"\|recipes_pos_resolved\|/consume")\|meal_plan/{.*}", data={"done"' app/services/consumption.py`
Expected: the raw sites for recipe fetch, fulfillment, resolved positions, consume, and meal_plan done-flag (note: some appear in multiple loops — meal-plan recipe loop AND check/preview loops).

- [ ] **Step 2: Replace each raw call with the typed method — match by ARGUMENT EXPRESSION, not by a canonical variable name**

The raw calls appear across multiple loops (save / preview / check / aggregation), and the id is held by *different* local expressions at different sites. Convert by passing whatever expression is already there. Verified call sites (line numbers approximate — re-grep before editing):

| Pattern | Sites | Typed replacement (use the local expr at that site) |
|---------|-------|------------------------------------------------------|
| `get(f"/objects/recipes/{meal['recipe_id']}")` | 80, 421, 626, 901, 1528 | `get_recipe(meal["recipe_id"])` |
| `get(f"/recipes/{shadow_id}/fulfillment")` | 84, 633, 907 | `get_recipe_fulfillment(shadow_id)` |
| `get("/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={shadow_id}"]})` | 88, 425, 638, 1221 | `get_resolved_positions(shadow_id)` |
| same, but arg is `recipe_meal['id']` (no `shadow_id` in scope) | **1517** | `get_resolved_positions(recipe_meal["id"])` |
| `post(f"/recipes/{shadow_id}/consume")` | 919 | `consume_recipe(shadow_id)` |
| `put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})` | **807, 835, 920** | `mark_meal_plan_done(meal["id"])` |

**Note the three meal-plan-done sites (807 note-branch, 835 standalone-product branch, 920 recipe-branch)** — all use `meal["id"]` and sit inside existing `GrocyError` handlers (`contextlib.suppress` at 807; `try/except` around 835). `mark_meal_plan_done` raises the same `GrocyError`, so the handlers still work.

Do NOT touch `grocy_api.get(f"/stock/products/{...}")` calls (out of scope per the scope guard).

**Behavior caveat (correct the old "behavior unchanged" claim):** at the four resolved-positions sites that today do NOT guard `None` (88, 425, 638, 1517), `get_resolved_positions`'s `or []` means a `None` Grocy response now iterates empty instead of raising `TypeError`. This is intentional hardening and strictly safer, but it is NOT byte-identical behavior. The `GrocyError` path is unchanged. Only `_resolve_product_origins` (1221) already had `try/except` + `or []`, so its inner `or []` becomes redundant — keep the OUTER try/except, the redundancy is harmless.

For the `recipes_pos_resolved` replacement: the existing `_resolve_product_origins` wraps that raw call inside a `try/except GrocyError: return {}`. Since `get_resolved_positions` already returns `[]` on an empty response (but NOT on GrocyError), keep the surrounding `try/except` in `_resolve_product_origins` and just swap the inner `grocy_api.get(...)` for `grocy_api.get_resolved_positions(shadow_id)`. (If plan #1 already moved this logic out, apply the swap there instead.)

- [ ] **Step 3: Confirm no raw sites remain (except stock/products)**

Run: `docker compose exec backend grep -n '/objects/recipes/\|/fulfillment"\|recipes_pos_resolved\|/consume")\|"done": 1' app/services/consumption.py`
Expected: no matches except possibly inside the new typed methods if they were inlined (they live in grocy_api.py, so expect zero in consumption.py).

- [ ] **Step 4: Run the consumption + regression suite**

Run: `docker compose exec backend pytest tests/api/test_consumption_endpoints.py tests/services_new/test_grocy_api_methods.py tests/services_new/test_consumption_grocy_calls.py -v`
Expected: PASS. The Step-0 regression tests (same asserted URLs) passing AFTER the swap is the proof the typed methods emit identical requests — that's the real "behavior preserved" check, not the service-boundary suite. (Caveat: the `or []` hardening at the four unguarded sites is a deliberate, strictly-safer change, not byte-identical — see Step 2.)

- [ ] **Step 5: Lint**

Run: `make lint-python`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/consumption.py backend/tests/services_new/test_consumption_grocy_calls.py
git commit -m "refactor: use typed GrocyAPI methods across consumption loops"
```

> Commit the Step-0 regression test together with the call-site swap (it was authored to pin the pre-swap contract; it now also guards the post-swap code).

---

## Self-Review

- **Spec coverage:** Candidate #3 = replace raw `/objects/...` path strings with typed methods so Grocy quirks concentrate in `grocy_api.py`. ✓ Tasks 1-2 add the five methods (TDD), Task 3 repoints every in-scope raw call. ✓
- **Placeholder scan:** No TBD/TODO; all method bodies and substitutions shown. ✓
- **Type consistency:** Method names `get_recipe`, `get_resolved_positions`, `get_recipe_fulfillment`, `consume_recipe`, `mark_meal_plan_done` identical across tasks and the substitution table. ✓
- **Scope:** Explicitly excludes `/stock/products/...` to avoid over-reach (YAGNI). ✓
- **Test seam note:** Tests bypass `__init__` via `__new__` and mock `get/post/put`, asserting on the exact path/params — verifying the interface translation without a live Grocy. This is the leverage the typed methods buy: tests assert on intent-shaped calls.
