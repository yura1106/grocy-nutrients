# Typed GrocyAPI Methods Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the holes in the `GrocyAPI` interface where `consumption.py` reaches through it with raw `/objects/...` path strings and `query[]=...` encoding, by adding typed methods for the consumption endpoints actually used, so callers express intent and the Grocy REST quirks live in one file.

**Architecture:** Add five typed methods to `GrocyAPI` — `get_resolved_positions(shadow_id)`, `get_recipe_fulfillment(shadow_id)`, `consume_recipe(shadow_id)`, `mark_meal_plan_done(meal_id)`, and `get_recipe(recipe_id)` — each wrapping the raw `get`/`post`/`put` call (and its `query[]` encoding) currently inlined in `consumption.py`. Then replace the raw call sites. The generic `get`/`post`/`put`/`delete` stay (still used for genuinely one-off paths).

**Tech Stack:** Python 3.12, FastAPI, httpx, pytest. All commands run inside Docker. Per project rules the engineer does NOT run tests/make targets — the user does; commands are listed for reference.

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
    def get_recipe(self, recipe_id):
        """Fetch a recipe object by id (shadow ids allowed)."""
        return self.get(f"/objects/recipes/{recipe_id}")

    def get_resolved_positions(self, shadow_id) -> list[dict]:
        """Resolved ingredient positions for a (shadow) recipe.

        Each position carries product_id, product_id_effective,
        is_nested_recipe_pos, child_recipe_id, recipe_amount. Returns [] when
        Grocy returns nothing.
        """
        return (
            self.get(
                "/objects/recipes_pos_resolved",
                {"query[]": [f"recipe_id={shadow_id}"]},
            )
            or []
        )
```

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
        return self.get(f"/recipes/{shadow_id}/fulfillment")

    def consume_recipe(self, shadow_id):
        """Consume a shadow recipe in Grocy (deducts stock, writes stock_log)."""
        return self.post(f"/recipes/{shadow_id}/consume")

    def mark_meal_plan_done(self, meal_plan_id):
        """Flip a meal_plan entry's done flag in Grocy."""
        return self.put(f"/objects/meal_plan/{meal_plan_id}", data={"done": 1})
```

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

- [ ] **Step 1: Inventory the raw calls to replace**

Run: `docker compose exec backend grep -n 'grocy_api\.get(f"/objects/recipes/\|/fulfillment"\|recipes_pos_resolved\|/consume")\|meal_plan/{.*}", data={"done"' app/services/consumption.py`
Expected: the raw sites for recipe fetch, fulfillment, resolved positions, consume, and meal_plan done-flag (note: some appear in multiple loops — meal-plan recipe loop AND check/preview loops).

- [ ] **Step 2: Replace each raw call with the typed method**

Apply these exact substitutions everywhere they appear in `backend/app/services/consumption.py`:

| Raw call | Typed method |
|----------|--------------|
| `grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")` | `grocy_api.get_recipe(meal["recipe_id"])` |
| `grocy_api.get(f"/recipes/{shadow_id}/fulfillment")` | `grocy_api.get_recipe_fulfillment(shadow_id)` |
| `grocy_api.get("/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={shadow_id}"]})` | `grocy_api.get_resolved_positions(shadow_id)` |
| `grocy_api.post(f"/recipes/{shadow_id}/consume")` | `grocy_api.consume_recipe(shadow_id)` |
| `grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})` | `grocy_api.mark_meal_plan_done(meal["id"])` |

Do NOT touch `grocy_api.get(f"/stock/products/{...}")` calls (out of scope per the scope guard).

For the `recipes_pos_resolved` replacement: the existing `_resolve_product_origins` wraps that raw call inside a `try/except GrocyError: return {}`. Since `get_resolved_positions` already returns `[]` on an empty response (but NOT on GrocyError), keep the surrounding `try/except` in `_resolve_product_origins` and just swap the inner `grocy_api.get(...)` for `grocy_api.get_resolved_positions(shadow_id)`. (If plan #1 already moved this logic out, apply the swap there instead.)

- [ ] **Step 3: Confirm no raw sites remain (except stock/products)**

Run: `docker compose exec backend grep -n '/objects/recipes/\|/fulfillment"\|recipes_pos_resolved\|/consume")\|"done": 1' app/services/consumption.py`
Expected: no matches except possibly inside the new typed methods if they were inlined (they live in grocy_api.py, so expect zero in consumption.py).

- [ ] **Step 4: Run the consumption suite**

Run: `docker compose exec backend pytest tests/api/test_consumption_endpoints.py tests/services_new/test_grocy_api_methods.py -v`
Expected: PASS. Behavior unchanged — typed methods produce identical requests.

- [ ] **Step 5: Lint**

Run: `make lint-python`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/consumption.py
git commit -m "refactor: use typed GrocyAPI methods in consumption save-loop"
```

---

## Self-Review

- **Spec coverage:** Candidate #3 = replace raw `/objects/...` path strings with typed methods so Grocy quirks concentrate in `grocy_api.py`. ✓ Tasks 1-2 add the five methods (TDD), Task 3 repoints every in-scope raw call. ✓
- **Placeholder scan:** No TBD/TODO; all method bodies and substitutions shown. ✓
- **Type consistency:** Method names `get_recipe`, `get_resolved_positions`, `get_recipe_fulfillment`, `consume_recipe`, `mark_meal_plan_done` identical across tasks and the substitution table. ✓
- **Scope:** Explicitly excludes `/stock/products/...` to avoid over-reach (YAGNI). ✓
- **Test seam note:** Tests bypass `__init__` via `__new__` and mock `get/post/put`, asserting on the exact path/params — verifying the interface translation without a live Grocy. This is the leverage the typed methods buy: tests assert on intent-shaped calls.
