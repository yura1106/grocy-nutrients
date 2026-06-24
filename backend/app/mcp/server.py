"""MCP server for Claude Code — tools over the local catalog.

Bearer-API-key auth authenticates the user and resolves the key's bound household.
Tools read the local DB only, with one exception: `add_product_to_meal_plan` may make
a read-only Grocy call to self-heal the meal-plan units cache on a cold miss (ADR-0004
amendment 2026-06-24). The per-user Grocy key IS readable on this path (Themis is keyed
by the `hashed_password` DB column, ADR-0002); no tool performs Grocy *writes* — meal-plan
lines reach Grocy only via the Celery worker (`submit_batch`). Stateless mode keeps the
per-request HTTP context current — see python-sdk #1233 for the session-reuse bug.

Each `@mcp.tool()` is a thin wrapper around a plain `_core` function taking
`(db, user, household_id, ...)` so tests can call the core directly (the MCP app is
not mounted in the test app).
"""

import logging
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from decimal import Decimal

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser, authenticate_api_key
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.household import HouseholdUser
from app.models.product import Product
from app.models.recipe import Recipe
from app.schemas.meal_plan import MealPlanLineCreate
from app.services.daily_nutrition import get_daily_nutrition_range
from app.services.grocy_api import GrocyConfigError, GrocyError, build_grocy_api
from app.services.meal_plan import (
    compute_daily_totals,
    create_lines,
    get_or_load_sections,
    get_or_load_units_for_product,
    submit_batch,
)
from app.services.nutrition_limits import resolve_nutrition_targets
from app.services.product import (
    get_last_consumption,
    get_product_detail_for_mcp,
    search_products_fuzzy,
)
from app.services.product import list_recent_consumption as _svc_list_recent_consumption
from app.services.recipe import get_recipe_detail_for_mcp, search_recipes_fuzzy
from app.services.stock_expiry import query_all_stock as _svc_query_all_stock
from app.services.stock_expiry import query_expiring_stock as _svc_query_expiring_stock

logger = logging.getLogger(__name__)

_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=bool(settings.MCP_ALLOWED_HOSTS),
    allowed_hosts=settings.MCP_ALLOWED_HOSTS,
)
mcp = FastMCP(
    "grocy-nutrients",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=_transport_security,
)

_DAY_NUTRIENT_MAP = {
    "kcal": "calories",
    "protein": "proteins",
    "carbs": "carbohydrates",
    "sugars": "carbohydrates_of_sugars",
    "fat": "fats",
    "sat_fat": "fats_saturated",
    "salt": "salt",
    "fibers": "fibers",
}


class MCPAuthError(Exception):
    """Raised when the request lacks a valid, household-bound API key."""


class MCPValidationError(Exception):
    """Raised when a tool argument is malformed (e.g. an unparseable date)."""


def _api_key_from_context(ctx: Context) -> str:
    request = ctx.request_context.request
    auth: str | None = request.headers.get("authorization") if request is not None else None
    if not auth:
        raise MCPAuthError("Missing Authorization header (Bearer API key required).")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise MCPAuthError("Authorization header must be 'Bearer <api_key>'.")
    return token


def _authenticate(token: str, db: Session) -> tuple[AuthenticatedUser, int]:
    try:
        user, household_id = authenticate_api_key(token, db)
    except HTTPException as exc:
        raise MCPAuthError(exc.detail) from exc
    if household_id is None:
        raise MCPAuthError(
            "This API key is not bound to a household. Re-create it from the Households UI."
        )
    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == user.id,
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if membership is None:
        raise MCPAuthError("You are no longer an active member of this household.")
    return user, household_id


def _resolve_date(value: str) -> date_type:
    """Parse an ISO date or the aliases today/tomorrow/yesterday (UTC)."""
    today = datetime.now(UTC).date()
    alias = value.strip().lower()
    if alias == "today":
        return today
    if alias == "tomorrow":
        return today + timedelta(days=1)
    if alias == "yesterday":
        return today - timedelta(days=1)
    try:
        return date_type.fromisoformat(value.strip())
    except ValueError as exc:
        raise MCPValidationError(
            f"Invalid date '{value}'. Use ISO YYYY-MM-DD or today/tomorrow/yesterday."
        ) from exc


def _search_product_core(
    db: Session, user: AuthenticatedUser, household_id: int, name: str, limit: int
) -> list[dict]:
    results = search_products_fuzzy(db, query=name, household_id=household_id, limit=limit)
    return [
        {
            "id": r.id,
            "name": r.name,
            "is_fresh": r.is_fresh,
            "calories": r.calories,
            "proteins": r.proteins,
            "fats": r.fats,
            "carbohydrates": r.carbohydrates,
            "carbohydrates_of_sugars": r.carbohydrates_of_sugars,
            "last_consumption": get_last_consumption(db, r.id, user.id),  # type: ignore[arg-type]
        }
        for r in results
    ]


def _search_recipe_core(
    db: Session, user: AuthenticatedUser, household_id: int, name: str, limit: int
) -> list[dict]:
    return search_recipes_fuzzy(db, query=name, household_id=household_id, limit=limit)


def _get_day_core(db: Session, user: AuthenticatedUser, household_id: int, date: str) -> dict:
    day = _resolve_date(date)
    result = compute_daily_totals(db, household_id=household_id, user_id=user.id, day=day)
    totals = {long: round(result[short], 2) for short, long in _DAY_NUTRIENT_MAP.items()}

    targets_source, targets = resolve_nutrition_targets(db, user, day)

    breakdown = []
    for line in result["breakdown"]:
        remapped = {k: v for k, v in line.items() if k not in _DAY_NUTRIENT_MAP}
        for short, long in _DAY_NUTRIENT_MAP.items():
            remapped[long] = line[short]
        breakdown.append(remapped)

    return {
        "date": day.isoformat(),
        "totals": totals,
        "targets": targets,
        "targets_source": targets_source,
        "breakdown": breakdown,
        "omitted_lines": result["omitted_lines"],
    }


def _get_nutrition_targets_core(
    db: Session, user: AuthenticatedUser, household_id: int, date: str
) -> dict:
    day = _resolve_date(date)
    source, targets = resolve_nutrition_targets(db, user, day)
    return {"date": day.isoformat(), "source": source, "targets": targets}


def _get_product_detail_core(
    db: Session, user: AuthenticatedUser, household_id: int, id: int
) -> dict:
    return get_product_detail_for_mcp(db, id, household_id, user.id)  # type: ignore[arg-type]


def _get_recipe_detail_core(
    db: Session, user: AuthenticatedUser, household_id: int, id: int
) -> dict:
    return get_recipe_detail_for_mcp(db, id, household_id, user.id)  # type: ignore[arg-type]


def _list_recent_consumption_core(
    db: Session, user: AuthenticatedUser, household_id: int, days: int
) -> dict:
    return _svc_list_recent_consumption(db, user.id, household_id, days)  # type: ignore[arg-type]


def _get_expiring_stock_core(
    db: Session,
    user: AuthenticatedUser,
    household_id: int,
    include_expired: bool = True,
    include_overdue: bool = True,
) -> list[dict]:
    items = _svc_query_expiring_stock(
        db, household_id, include_expired=include_expired, include_overdue=include_overdue
    )
    return [
        {
            "product_name": i.row.product_name,
            "amount": float(i.row.amount),
            "quantity_unit_name": i.row.quantity_unit_name,
            "best_before_date": i.row.best_before_date.isoformat()
            if i.row.best_before_date
            else None,
            "days_until_expiry": i.days_until_expiry,
            "expiry_status": i.expiry_status,
            "should_not_be_frozen": i.row.should_not_be_frozen,
            "synced_at": i.synced_at.isoformat(),
        }
        for i in items
    ]


def _get_all_stock_core(
    db: Session,
    user: AuthenticatedUser,
    household_id: int,
) -> list[dict]:
    items = _svc_query_all_stock(db, household_id)
    return [
        {
            "product_name": i.product_name,
            "amount": float(i.amount),
            "quantity_unit_name": i.quantity_unit_name,
            "best_before_date": i.best_before_date.isoformat() if i.best_before_date else None,
            "days_until_expiry": i.days_until_expiry,
            "expiry_status": i.expiry_status,
            "should_not_be_frozen": i.should_not_be_frozen,
            "synced_at": i.synced_at.isoformat(),
        }
        for i in items
    ]


def _get_nutrition_history_core(
    db: Session, user: AuthenticatedUser, household_id: int, start: str, end: str
) -> dict:
    start_d = _resolve_date(start)
    end_d = _resolve_date(end)
    rows = get_daily_nutrition_range(db, user.id, start_d, end_d)  # type: ignore[arg-type]
    return {
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
        "days": [r.model_dump() for r in rows],
    }


def _match_unit(units: list[dict], unit: str | None) -> dict | None:
    if unit is None or not unit.strip():
        return next((u for u in units if u.get("is_stock_default")), None)
    wanted = unit.strip().casefold()
    for u in units:
        names = {str(u.get("name") or "").casefold(), str(u.get("name_plural") or "").casefold()}
        if wanted in names - {""}:
            return u
    return None


def _resolve_section_id(household_id: int, section: str | None) -> int:
    if section is None or not section.strip():
        return 0
    wanted = section.strip().casefold()
    sections = get_or_load_sections(household_id, grocy_api=None)
    for s in sections:
        if str(s.get("name", "")).casefold() == wanted:
            return int(s["section_id"])
    names = [s.get("name", "") for s in sections]
    raise MCPValidationError(
        f"Unknown meal section '{section}'. Available: {names or 'none cached'}."
    )


def _add_product_to_meal_plan_core(
    db: Session,
    user: AuthenticatedUser,
    household_id: int,
    product_id: int,
    amount: float,
    date: str,
    unit: str | None = None,
    section: str | None = None,
) -> dict:
    if amount <= 0:
        raise MCPValidationError("amount must be > 0.")
    day = _resolve_date(date)
    section_id = _resolve_section_id(household_id, section)

    product = db.exec(
        select(Product).where(Product.id == product_id, Product.household_id == household_id)
    ).first()
    if product is None:
        raise MCPValidationError(f"No product with local id {product_id} in this household.")
    grocy_product_id = int(product.grocy_id)

    units_payload = get_or_load_units_for_product(household_id, grocy_product_id, grocy_api=None)
    units = units_payload.get("units") or []
    if not units:
        try:
            grocy_api = build_grocy_api(db, household_id, user.id)
            units_payload = get_or_load_units_for_product(
                household_id, grocy_product_id, grocy_api=grocy_api
            )
            units = units_payload.get("units") or []
        except (GrocyConfigError, GrocyError):
            units = []
    if not units:
        return {
            "status": "needs_units",
            "available_units": [],
            "message": (
                f"Could not load units for '{product.name}' from Grocy. Check that this "
                "household's Grocy key and URL are configured, then try again."
            ),
        }

    chosen = _match_unit(units, unit)
    if chosen is None:
        return {
            "status": "needs_unit",
            "available_units": [{"qu_id": u["qu_id"], "name": u["name"]} for u in units],
            "message": (
                f"Specify a unit for '{product.name}'."
                if unit is None
                else f"Unit '{unit}' not found for '{product.name}'."
            ),
        }

    factor = float(chosen.get("factor_to_stock") or 1.0)
    line = MealPlanLineCreate(
        type="product",
        day=day,
        section_id=section_id,
        product_grocy_id=grocy_product_id,
        product_amount=Decimal(str(amount)),
        product_amount_stock=Decimal(str(amount * factor)),
        product_qu_id=int(chosen["qu_id"]),
    )
    rows = create_lines(
        db, household_id=household_id, user_id=user.id, lines=[line], grocy_api=None
    )
    line_ids = [int(r.id) for r in rows if r.id is not None]
    task_id = submit_batch(db, household_id=household_id, user_id=user.id, line_ids=line_ids)
    return {
        "status": "queued",
        "line_id": line_ids[0],
        "task_id": task_id,
        "day": day.isoformat(),
        "section_id": section_id,
        "resolved_unit": chosen["name"],
        "amount": amount,
    }


def _add_recipe_to_meal_plan_core(
    db: Session,
    user: AuthenticatedUser,
    household_id: int,
    recipe_id: int,
    servings: float,
    date: str,
    section: str | None = None,
) -> dict:
    if servings <= 0:
        raise MCPValidationError("servings must be > 0.")
    day = _resolve_date(date)
    section_id = _resolve_section_id(household_id, section)

    recipe = db.exec(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.household_id == household_id)
    ).first()
    if recipe is None:
        raise MCPValidationError(f"No recipe with local id {recipe_id} in this household.")

    line = MealPlanLineCreate(
        type="recipe",
        day=day,
        section_id=section_id,
        recipe_grocy_id=int(recipe.grocy_id),
        recipe_servings=Decimal(str(servings)),
    )
    rows = create_lines(
        db, household_id=household_id, user_id=user.id, lines=[line], grocy_api=None
    )
    line_ids = [int(r.id) for r in rows if r.id is not None]
    task_id = submit_batch(db, household_id=household_id, user_id=user.id, line_ids=line_ids)
    return {
        "status": "queued",
        "line_id": line_ids[0],
        "task_id": task_id,
        "day": day.isoformat(),
        "section_id": section_id,
        "servings": servings,
    }


@mcp.tool()
def search_product(name: str, ctx: Context, limit: int = 5) -> list[dict]:
    """Fuzzy-search products by name; returns local id, name, per-100g nutrients
    and `last_consumption` (your most recent consumption with its macros)."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _search_product_core(db, user, household_id, name, limit)


@mcp.tool()
def search_recipe(name: str, ctx: Context, limit: int = 5) -> list[dict]:
    """Fuzzy-search recipes by name. Returns local id, name and the latest
    per-serving nutrients for each match. Typo-tolerant."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _search_recipe_core(db, user, household_id, name, limit)


@mcp.tool()
def get_day(date: str, ctx: Context) -> dict:
    """Calculated nutrition for one day of your meal plan. `date`: ISO or
    today/tomorrow/yesterday. Returns `totals`, `targets` + `targets_source`
    (daily_limit|profile_default|none), per-line `breakdown`, and `omitted_lines`
    (count of lines unresolvable locally)."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_day_core(db, user, household_id, date)


@mcp.tool()
def get_nutrition_targets(date: str, ctx: Context) -> dict:
    """Your daily nutrient targets for a date (use when planning meals). `date`:
    ISO or today/tomorrow/yesterday. Returns `source`
    (daily_limit|profile_default|none) and `targets` (8 nutrient goals, each may be
    null; `targets` is null when source is none)."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_nutrition_targets_core(db, user, household_id, date)


@mcp.tool()
def get_product_detail(id: int, ctx: Context) -> dict:
    """Full detail for one product (by local id): nutrient-data history and your
    consumption history."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_product_detail_core(db, user, household_id, id)


@mcp.tool()
def get_recipe_detail(id: int, ctx: Context) -> dict:
    """Full detail for one recipe (by local id): per-serving consumption history
    and the product breakdown of its most recent consumption."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_recipe_detail_core(db, user, household_id, id)


@mcp.tool()
def list_recent_consumption(days: int, ctx: Context) -> dict:
    """Your product and recipe consumption over the last `days` days (local ids)."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _list_recent_consumption_core(db, user, household_id, days)


@mcp.tool()
def get_expiring_stock(
    ctx: Context,
    include_expired: bool = True,
    include_overdue: bool = True,
) -> list[dict]:
    """Stock expiring soon, overdue, or expired (7-day window), sorted by urgency.
    days_until_expiry/expiry_status are recomputed live; `synced_at` is freshness.
    Set include_expired/include_overdue False to narrow."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_expiring_stock_core(db, user, household_id, include_expired, include_overdue)


@mcp.tool()
def get_all_stock(ctx: Context) -> list[dict]:
    """Whole pantry, one line per product (amounts summed across entries, nearest
    best_before kept), sorted by urgency. days_until_expiry/expiry_status recomputed
    live; `synced_at` is freshness."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_all_stock_core(db, user, household_id)


@mcp.tool()
def get_nutrition_history(start: str, end: str, ctx: Context) -> dict:
    """Your recorded daily-nutrition totals over a date range (inclusive).

    `start` and `end` accept ISO dates or today/tomorrow/yesterday.
    """
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_nutrition_history_core(db, user, household_id, start, end)


@mcp.tool()
def add_product_to_meal_plan(
    product_id: int,
    amount: float,
    date: str,
    ctx: Context,
    unit: str | None = None,
    section: str | None = None,
) -> dict:
    """Add a product to your meal plan for a day (local DB + Grocy). Plans a meal —
    does NOT consume/change stock. `product_id` from search_product; `date` ISO or
    today/tomorrow/yesterday; `unit` a unit name (default: stock unit); `section`
    optional. Returns `{status: queued, ...}`, or `needs_unit`/`needs_units`
    (with `available_units`) — ask the user and retry."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _add_product_to_meal_plan_core(
            db, user, household_id, product_id, amount, date, unit, section
        )


@mcp.tool()
def add_recipe_to_meal_plan(
    recipe_id: int,
    servings: float,
    date: str,
    ctx: Context,
    section: str | None = None,
) -> dict:
    """Add a recipe to your meal plan for a day (local DB + Grocy). Plans a meal —
    does NOT consume/change stock. `recipe_id` from search_recipe; `date` ISO or
    today/tomorrow/yesterday; `section` optional. Returns `{status: queued, ...}`."""
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _add_recipe_to_meal_plan_core(
            db, user, household_id, recipe_id, servings, date, section
        )
