"""URL-level regression net for the consumption.py Grocy call sites.

These tests pin the EXACT Grocy paths/params that the consumption loops emit,
so the Task-3 refactor (raw `grocy_api.get("/objects/...")` -> typed methods
like `get_recipe`) can be proven request-identical. They are written to pass
against the PRE-swap code and must keep passing after the swap.

Strategy: a RecordingGrocy bypasses __init__ and records every get/post/put
(path, params/data) while returning canned shapes keyed by path. The canned
data is chosen so each driver function reaches all in-scope recipe/product call
sites and then short-circuits (empty resolved positions + empty stock_log =>
the deep per-position DB/conversion loops are skipped).
"""

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.user import User
from app.services import consumption
from app.services.grocy_api import GrocyAPI

SHADOW_ID = -44663
RECIPE_ID = 75
MEAL_ID = 5531
PRODUCT_ID = 491
DATE = "2024-01-15"


class RecordingGrocy(GrocyAPI):
    """Records every HTTP call and returns canned, short-circuiting data."""

    def __new__(cls):
        return super().__new__(cls)

    def __init__(self):  # bypass real __init__ (needs url/key)
        self.calls: list[tuple] = []

    def get(self, path, params=None):
        self.calls.append(("GET", path, params))
        if path == "/objects/meal_plan":
            return self._meal_plan
        if path.startswith("/objects/recipes/"):
            return {"id": RECIPE_ID, "name": "Вечеря №1"}
        if path == "/objects/recipes":  # get_meal_plan_recipe
            return [{"id": SHADOW_ID}]
        if path.endswith("/fulfillment"):
            return {"missing_products_count": 0}
        if path == "/objects/recipes_pos_resolved":
            return []
        if path == "/objects/stock_log":
            return []
        if path.startswith("/stock/products/"):
            return {"stock_amount": 999, "stock_amount_aggregated": 999, "product": {}}
        return []

    def post(self, path, data=None, params=None):
        self.calls.append(("POST", path, data))
        return []

    def put(self, path, data=None, params=None):
        self.calls.append(("PUT", path, data))
        return {}

    # convenience
    def paths(self, method=None):
        return [(m, p) for (m, p, _) in self.calls if method is None or m == method]


def _recipe_meal(user_id: int):
    # userfields.user_id keeps the row through filter_meal_plan_to_user without DB
    return {
        "id": MEAL_ID,
        "type": "recipe",
        "recipe_id": RECIPE_ID,
        "day": DATE,
        "userfields": {"user_id": str(user_id)},
    }


def _product_meal(user_id: int):
    return {
        "id": MEAL_ID + 1,
        "type": "product",
        "product_id": PRODUCT_ID,
        "product_amount": 1,
        "day": DATE,
        "userfields": {"user_id": str(user_id)},
    }


@pytest.fixture()
def hh_and_user(test_user: User, test_household: Household) -> tuple[int, int]:
    """Reuse conftest's user+household; returns (household_id, user_id)."""
    return test_household.id, test_user.id


def _grocy(meal_plan):
    g = RecordingGrocy()
    g._meal_plan = meal_plan
    return g


class TestCheckProductsAvailabilityCalls:
    def test_recipe_branch_emits_expected_paths(
        self, db: Session, hh_and_user: tuple[int, int]
    ):
        household, user_id = hh_and_user
        g = _grocy([_recipe_meal(user_id)])
        consumption.check_products_availability(
            db, g, date_str=DATE, household_id=household, user_id=user_id
        )
        paths = g.paths()
        assert ("GET", f"/objects/recipes/{RECIPE_ID}") in paths
        assert ("GET", f"/recipes/{SHADOW_ID}/fulfillment") in paths
        assert ("GET", "/objects/recipes_pos_resolved") in paths
        # the resolved query carries the shadow id
        resolved_calls = [c for c in g.calls if c[1] == "/objects/recipes_pos_resolved"]
        assert resolved_calls[0][2] == {"query[]": [f"recipe_id={SHADOW_ID}"]}


class TestCheckRangeAvailabilityCalls:
    def test_recipe_branch_emits_expected_paths(
        self, db: Session, hh_and_user: tuple[int, int]
    ):
        household, user_id = hh_and_user
        g = _grocy([_recipe_meal(user_id)])
        consumption.check_range_availability(
            db, g, household, DATE, DATE, user_id=user_id
        )
        paths = g.paths()
        assert ("GET", f"/objects/recipes/{RECIPE_ID}") in paths
        assert ("GET", "/objects/recipes_pos_resolved") in paths
        resolved_calls = [c for c in g.calls if c[1] == "/objects/recipes_pos_resolved"]
        assert resolved_calls[0][2] == {"query[]": [f"recipe_id={SHADOW_ID}"]}


class TestExecuteConsumptionCalls:
    def test_recipe_branch_emits_consume_and_done(
        self, db: Session, hh_and_user: tuple[int, int]
    ):
        household, user_id = hh_and_user
        g = _grocy([_recipe_meal(user_id)])
        consumption.execute_consumption(
            db, g, DATE, household_id=household, user_id=user_id
        )
        paths = g.paths()
        assert ("GET", f"/objects/recipes/{RECIPE_ID}") in paths
        assert ("GET", f"/recipes/{SHADOW_ID}/fulfillment") in paths
        assert ("POST", f"/recipes/{SHADOW_ID}/consume") in paths
        # meal_plan done flag (recipe branch, line ~920)
        done_calls = [c for c in g.calls if c[0] == "PUT"]
        assert ("PUT", f"/objects/meal_plan/{MEAL_ID}", {"done": 1}) in done_calls

    def test_product_branch_marks_meal_done(
        self, db: Session, hh_and_user: tuple[int, int]
    ):
        household, user_id = hh_and_user
        g = _grocy([_product_meal(user_id)])
        consumption.execute_consumption(
            db, g, DATE, household_id=household, user_id=user_id
        )
        done_calls = [c for c in g.calls if c[0] == "PUT"]
        assert ("PUT", f"/objects/meal_plan/{MEAL_ID + 1}", {"done": 1}) in done_calls
