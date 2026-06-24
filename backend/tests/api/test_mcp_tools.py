"""MCP tool cores — called directly (the MCP app is not mounted in the test app).

Covers: search returns local id only + last_consumption; get_day strips
missing_items (grocy_id) and counts unsynced lines in omitted_lines, not breakdown.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app.mcp.server import (
    MCPValidationError,
    _add_product_to_meal_plan_core,
    _add_recipe_to_meal_plan_core,
    _get_day_core,
    _get_nutrition_targets_core,
    _resolve_date,
    _search_product_core,
)
from app.models.meal_plan import MealPlan
from app.models.nutrition_limit import DailyNutritionLimit
from app.models.product import ConsumedProduct, Product, ProductData
from app.models.recipe import Recipe
from app.models.user import User
from app.models.user_health_profile import UserHealthProfile
from app.services.grocy_api import GrocyConfigError
from app.services.nutrition_limits import resolve_nutrition_targets

HH = 1
USER_ID = 1001
DAY = date(2026, 6, 15)


@pytest.fixture()
def user(db: Session) -> User:
    u = User(
        id=USER_ID,
        email="mcp@example.com",
        username="mcp-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _product(db: Session, grocy_id: int, name: str, *, calories: float) -> Product:
    product = Product(
        grocy_id=grocy_id,
        name=name,
        product_group_id=1,
        household_id=HH,
        qu_id_stock=3,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db.add(ProductData(product_id=product.id, calories=calories, created_at=datetime.now(UTC)))
    db.commit()
    return product


def test_resolve_date_aliases() -> None:
    today = datetime.now(UTC).date()
    assert _resolve_date("today") == today
    assert _resolve_date("2026-06-15") == date(2026, 6, 15)


def test_search_product_local_id_and_last_consumption(db: Session, user: User) -> None:
    product = _product(db, 546, "Деруни", calories=2.0)
    pd = db.exec(select(ProductData).where(ProductData.product_id == product.id)).first()
    db.add(
        ConsumedProduct(
            product_data_id=pd.id,
            date=DAY,
            quantity=100,
            user_id=USER_ID,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = _search_product_core(db, user, HH, "деруни", 5)
    assert len(out) == 1
    row = out[0]
    assert row["id"] == product.id
    assert "grocy_id" not in row
    assert row["last_consumption"] is not None
    assert row["last_consumption"]["calories"] == 200.0


def test_get_day_strips_missing_items_and_counts_omitted(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A synced product resolves into breakdown; an unsynced product (no local
    row) is counted in omitted_lines and never appears in breakdown — and the
    response never carries missing_items (grocy_id)."""
    _product(db, 546, "Деруни", calories=2.0)

    # Cache hit for the synced product; the unsynced one has no local row anyway.
    fake_r = MagicMock()
    fake_r.get.return_value = json.dumps({"units": [], "stock_to_grams_ml": 1.0})
    monkeypatch.setattr("app.services.meal_plan.get_redis", lambda: fake_r)

    db.add(
        MealPlan(
            household_id=HH,
            user_id=USER_ID,
            type="product",
            day=DAY,
            section_id=1,
            product_grocy_id=546,
            product_amount=Decimal("100"),
            product_amount_stock=Decimal("100"),
            product_qu_id=82,
            status="pending",
            created_at=datetime.now(UTC),
        )
    )
    db.add(
        MealPlan(
            household_id=HH,
            user_id=USER_ID,
            type="product",
            day=DAY,
            section_id=1,
            product_grocy_id=999,
            product_amount=Decimal("100"),
            product_amount_stock=Decimal("100"),
            product_qu_id=82,
            status="pending",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = _get_day_core(db, user, HH, "2026-06-15")
    assert out["date"] == "2026-06-15"
    assert "missing_items" not in out
    assert out["omitted_lines"] == 1
    assert len(out["breakdown"]) == 1
    line = out["breakdown"][0]
    assert line["id"] is not None
    # Breakdown speaks the same long-form vocabulary as totals (not kcal/protein).
    assert line["calories"] == pytest.approx(200.0)
    assert "kcal" not in line
    assert out["totals"]["calories"] == pytest.approx(200.0)
    # Salt is tracked across the whole day view (totals + breakdown).
    assert "salt" in out["totals"]
    assert "salt" in line


def test_resolve_targets_per_day_limit_wins(db: Session, user: User) -> None:
    db.add(UserHealthProfile(user_id=USER_ID, daily_calories=2000, created_at=datetime.now(UTC)))
    db.add(
        DailyNutritionLimit(
            user_id=USER_ID,
            date=DAY,
            calories=1800,
            proteins=140,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    source, targets = resolve_nutrition_targets(db, user, DAY)
    assert source == "daily_limit"
    assert targets is not None
    assert targets["calories"] == 1800
    assert targets["proteins"] == 140


def test_resolve_targets_falls_back_to_profile(db: Session, user: User) -> None:
    db.add(
        UserHealthProfile(
            user_id=USER_ID,
            daily_calories=2200,
            daily_proteins=150,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    source, targets = resolve_nutrition_targets(db, user, DAY)
    assert source == "profile_default"
    assert targets is not None
    assert targets["calories"] == 2200
    assert targets["proteins"] == 150
    # Unset profile defaults map through as None.
    assert targets["salt"] is None


def test_resolve_targets_none_when_nothing_set(db: Session, user: User) -> None:
    source, targets = resolve_nutrition_targets(db, user, DAY)
    assert source == "none"
    assert targets is None


def test_resolve_targets_empty_profile_is_none(db: Session, user: User) -> None:
    """A profile row with no daily_* set is not a valid default source."""
    db.add(UserHealthProfile(user_id=USER_ID, weight=70, created_at=datetime.now(UTC)))
    db.commit()

    source, targets = resolve_nutrition_targets(db, user, DAY)
    assert source == "none"
    assert targets is None


def test_get_nutrition_targets_core_envelope(db: Session, user: User) -> None:
    db.add(UserHealthProfile(user_id=USER_ID, daily_calories=2100, created_at=datetime.now(UTC)))
    db.commit()

    out = _get_nutrition_targets_core(db, user, HH, "2026-06-15")
    assert out["date"] == "2026-06-15"
    assert out["source"] == "profile_default"
    assert out["targets"]["calories"] == 2100


def test_get_day_targets_use_fallback(db: Session, user: User) -> None:
    db.add(UserHealthProfile(user_id=USER_ID, daily_calories=2300, created_at=datetime.now(UTC)))
    db.commit()

    out = _get_day_core(db, user, HH, "2026-06-15")
    assert out["targets_source"] == "profile_default"
    assert out["targets"]["calories"] == 2300


# ===== Meal-plan write tools =====

STOCK_QU = 3
PIECE_QU = 82


def _recipe(db: Session, grocy_id: int, name: str) -> Recipe:
    recipe = Recipe(grocy_id=grocy_id, name=name, household_id=HH, created_at=datetime.now(UTC))
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def _mock_units(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    """Patch the units cache helper (Redis) used by the product write core."""
    monkeypatch.setattr(
        "app.mcp.server.get_or_load_units_for_product", lambda hh, gid, grocy_api=None: payload
    )


def _mock_units_sequence(monkeypatch: pytest.MonkeyPatch, *payloads: dict) -> list[dict]:
    """Patch the units helper to return successive payloads (cold-read then post-warm)."""
    calls: list[dict] = []

    def _fake(hh: int, gid: int, grocy_api: object = None) -> dict:
        calls.append({"grocy_api": grocy_api})
        return payloads[min(len(calls) - 1, len(payloads) - 1)]

    monkeypatch.setattr("app.mcp.server.get_or_load_units_for_product", _fake)
    return calls


def _spy_build_grocy_api(monkeypatch: pytest.MonkeyPatch, *, raises: Exception | None = None) -> list:
    """Stub build_grocy_api to a sentinel (or raise); return a list recording each call."""
    calls: list = []

    def _fake(db: object, household_id: int, user_id: int) -> object:
        calls.append((household_id, user_id))
        if raises is not None:
            raise raises
        return object()

    monkeypatch.setattr("app.mcp.server.build_grocy_api", _fake)
    return calls


def _stub_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the Celery enqueue so create_lines runs but no task/Redis is touched."""
    monkeypatch.setattr("app.mcp.server.submit_batch", lambda *a, **k: "task-123")


_GRAMS = {
    "qu_id": STOCK_QU,
    "name": "g",
    "name_plural": None,
    "is_stock_default": True,
    "factor_to_stock": 1.0,
}
_BANKA = {
    "qu_id": PIECE_QU,
    "name": "банка",
    "name_plural": "банки",
    "is_stock_default": False,
    "factor_to_stock": 500.0,
}


def test_add_product_happy_path_converts_to_stock(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = _product(db, 546, "Квасоля", calories=2.0)
    _mock_units(monkeypatch, {"units": [_GRAMS, _BANKA], "stock_to_grams_ml": 1.0})
    _stub_submit(monkeypatch)

    out = _add_product_to_meal_plan_core(
        db, user, HH, product.id, amount=2, date="2026-06-15", unit="банка"
    )
    assert out["status"] == "queued"
    assert out["resolved_unit"] == "банка"
    assert out["section_id"] == 0

    row = db.exec(select(MealPlan).where(MealPlan.id == out["line_id"])).first()
    assert row is not None
    assert row.type == "product"
    assert row.product_grocy_id == 546
    assert row.product_qu_id == PIECE_QU
    assert row.product_amount == Decimal("2")
    assert row.product_amount_stock == Decimal("1000.0")  # 2 банки * 500
    assert row.status == "pending"


def test_add_product_defaults_to_stock_unit_when_unit_omitted(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = _product(db, 547, "Борошно", calories=3.0)
    _mock_units(monkeypatch, {"units": [_GRAMS, _BANKA], "stock_to_grams_ml": 1.0})
    _stub_submit(monkeypatch)

    out = _add_product_to_meal_plan_core(db, user, HH, product.id, amount=250, date="today")
    assert out["status"] == "queued"
    assert out["resolved_unit"] == "g"
    row = db.exec(select(MealPlan).where(MealPlan.id == out["line_id"])).first()
    assert row.product_qu_id == STOCK_QU
    assert row.product_amount_stock == Decimal("250.0")


def test_add_product_cold_miss_warms_then_proceeds(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = _product(db, 548, "Цукор", calories=4.0)
    # Cold read returns empty; after warm the units are populated.
    _mock_units_sequence(
        monkeypatch,
        {"units": [], "stock_to_grams_ml": None},
        {"units": [_GRAMS], "stock_to_grams_ml": 1.0},
    )
    build_calls = _spy_build_grocy_api(monkeypatch)
    _stub_submit(monkeypatch)

    out = _add_product_to_meal_plan_core(db, user, HH, product.id, amount=10, date="today")
    assert out["status"] == "queued"
    assert build_calls == [(HH, user.id)]  # warm attempted exactly once
    assert db.exec(select(MealPlan)).first() is not None


def test_add_product_warm_failure_returns_needs_units(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = _product(db, 548, "Цукор", calories=4.0)
    _mock_units(monkeypatch, {"units": [], "stock_to_grams_ml": None})
    _spy_build_grocy_api(monkeypatch, raises=GrocyConfigError("no_api_key", "missing"))

    out = _add_product_to_meal_plan_core(db, user, HH, product.id, amount=1, date="today")
    assert out["status"] == "needs_units"
    assert out["available_units"] == []
    assert db.exec(select(MealPlan)).first() is None  # nothing written


def test_add_product_cache_hit_does_not_warm(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = _product(db, 548, "Цукор", calories=4.0)
    _mock_units(monkeypatch, {"units": [_GRAMS], "stock_to_grams_ml": 1.0})
    build_calls = _spy_build_grocy_api(monkeypatch)
    _stub_submit(monkeypatch)

    out = _add_product_to_meal_plan_core(db, user, HH, product.id, amount=5, date="today")
    assert out["status"] == "queued"
    assert build_calls == []  # hot path never decrypts / builds a Grocy client


def test_add_product_unknown_unit_returns_needs_unit(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = _product(db, 549, "Олія", calories=9.0)
    _mock_units(monkeypatch, {"units": [_GRAMS, _BANKA], "stock_to_grams_ml": 1.0})

    out = _add_product_to_meal_plan_core(
        db, user, HH, product.id, amount=1, date="today", unit="пляшка"
    )
    assert out["status"] == "needs_unit"
    assert {u["name"] for u in out["available_units"]} == {"g", "банка"}
    assert db.exec(select(MealPlan)).first() is None


def test_add_product_unknown_id_raises(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_units(monkeypatch, {"units": [_GRAMS], "stock_to_grams_ml": 1.0})
    with pytest.raises(MCPValidationError):
        _add_product_to_meal_plan_core(db, user, HH, 99999, amount=1, date="today")


def test_add_recipe_happy_path(db: Session, user: User, monkeypatch: pytest.MonkeyPatch) -> None:
    recipe = _recipe(db, 7, "Борщ")
    _stub_submit(monkeypatch)

    out = _add_recipe_to_meal_plan_core(db, user, HH, recipe.id, servings=2, date="tomorrow")
    assert out["status"] == "queued"
    assert out["servings"] == 2
    row = db.exec(select(MealPlan).where(MealPlan.id == out["line_id"])).first()
    assert row.type == "recipe"
    assert row.recipe_grocy_id == 7
    assert row.recipe_servings == Decimal("2")
    assert row.product_grocy_id is None


def test_add_recipe_unknown_id_raises(db: Session, user: User) -> None:
    with pytest.raises(MCPValidationError):
        _add_recipe_to_meal_plan_core(db, user, HH, 99999, servings=1, date="today")


def test_add_recipe_rejects_nonpositive_servings(db: Session, user: User) -> None:
    recipe = _recipe(db, 8, "Каша")
    with pytest.raises(MCPValidationError):
        _add_recipe_to_meal_plan_core(db, user, HH, recipe.id, servings=0, date="today")


def test_add_recipe_section_by_name(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipe = _recipe(db, 9, "Омлет")
    _stub_submit(monkeypatch)
    monkeypatch.setattr(
        "app.mcp.server.get_or_load_sections",
        lambda hh, grocy_api=None: [{"section_id": 5, "name": "Сніданок"}],
    )

    out = _add_recipe_to_meal_plan_core(
        db, user, HH, recipe.id, servings=1, date="today", section="сніданок"
    )
    assert out["section_id"] == 5


def test_add_recipe_unknown_section_raises(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipe = _recipe(db, 10, "Суп")
    monkeypatch.setattr(
        "app.mcp.server.get_or_load_sections",
        lambda hh, grocy_api=None: [{"section_id": 5, "name": "Сніданок"}],
    )
    with pytest.raises(MCPValidationError):
        _add_recipe_to_meal_plan_core(
            db, user, HH, recipe.id, servings=1, date="today", section="вечеря"
        )
