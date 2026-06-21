"""MCP server for Claude Code — read-only tools over the local catalog (never Grocy).

Bearer-API-key auth authenticates the user and resolves the key's bound household;
the per-user Grocy key is unreadable on this path (Themis is keyed by the password
hash), so every tool reads the local DB only. Stateless mode keeps the per-request
HTTP context current — see python-sdk #1233 for the session-reuse bug.

Each `@mcp.tool()` is a thin wrapper around a plain `_core` function taking
`(db, user, household_id, ...)` so tests can call the core directly (the MCP app is
not mounted in the test app).
"""

import logging
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser, authenticate_api_key
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.household import HouseholdUser
from app.services.daily_nutrition import get_daily_nutrition_range
from app.services.meal_plan import compute_daily_totals
from app.services.nutrition_limits import get_today_limit
from app.services.product import (
    get_last_consumption,
    get_product_detail_for_mcp,
    search_products_fuzzy,
)
from app.services.product import list_recent_consumption as _svc_list_recent_consumption
from app.services.recipe import get_recipe_detail_for_mcp, search_recipes_fuzzy

logger = logging.getLogger(__name__)

_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=bool(settings.MCP_ALLOWED_HOSTS),
    allowed_hosts=settings.MCP_ALLOWED_HOSTS,
)
# streamable_http_path="/" so the tool resolves at /mcp (default would nest to /mcp/mcp).
mcp = FastMCP(
    "grocy-nutrients",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=_transport_security,
)

# compute_daily_totals / breakdown speak short keys; the MCP day output speaks the
# long-form (DB attribute) names. Map short → long for totals, breakdown, and targets.
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
    """Authenticate the key and return (user, household_id).

    Converts HTTPException → MCPAuthError and rejects keys with no household
    (legacy keys minted before the per-key binding — re-mint from the UI). The
    None-rejection also narrows the type to `int` for the tool cores.
    """
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


# ===== Tool cores (plain, testable; no FastMCP Context) =====


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
    # grocy_api omitted → MCP path: units from cache only, no Grocy calls.
    result = compute_daily_totals(db, household_id=household_id, user_id=user.id, day=day)
    # compute_daily_totals speaks short keys (kcal/protein/…); remap to long names.
    totals = {long: round(result[short], 2) for short, long in _DAY_NUTRIENT_MAP.items()}

    limit = get_today_limit(db, user, day)
    targets = (
        {long: getattr(limit, long) for long in _DAY_NUTRIENT_MAP.values()}
        if limit is not None
        else None
    )

    # Remap each breakdown line's nutrient keys to the same long-form vocabulary
    # as totals (keeping id/name/amount/servings/done/type). Strip `missing_items`
    # (it carries grocy_id); expose only the local-id breakdown.
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
        "breakdown": breakdown,
        "omitted_lines": result["omitted_lines"],
    }


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


# ===== MCP tools (thin wrappers) =====


@mcp.tool()
def search_product(name: str, ctx: Context, limit: int = 5) -> list[dict]:
    """Fuzzy-search products in your grocy-nutrients catalog by name.

    Returns up to `limit` matches with local id, name, per-100g nutrients and a
    `last_consumption` sub-object (your most recent consumption of that product,
    with its contributed macros). Typo-tolerant.
    """
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
    """Calculated nutrition for one day of your meal plan.

    `date` accepts an ISO date (YYYY-MM-DD) or today/tomorrow/yesterday. Returns
    summed `totals`, your `targets` for that day (if set), a per-line `breakdown`
    (local ids, contributed macros, done flag), and `omitted_lines` — a count of
    lines that couldn't be resolved locally (unsynced products/recipes).
    """
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_day_core(db, user, household_id, date)


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
def get_nutrition_history(start: str, end: str, ctx: Context) -> dict:
    """Your recorded daily-nutrition totals over a date range (inclusive).

    `start` and `end` accept ISO dates or today/tomorrow/yesterday.
    """
    token = _api_key_from_context(ctx)
    with SessionLocal() as db:
        user, household_id = _authenticate(token, db)
        return _get_nutrition_history_core(db, user, household_id, start, end)
