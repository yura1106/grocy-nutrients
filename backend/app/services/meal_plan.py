"""
Meal plan service.

Handles local creation of meal-plan rows, enqueueing the Grocy sync batch task,
reconciliation against Grocy as the canonical store, single-line retry, and
flipping the local `done` flag from the consumption flow.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from celery.result import AsyncResult
from fastapi import HTTPException, status
from sqlalchemy import update
from sqlmodel import Session, col, select

from app.core.redis import get_redis
from app.models.meal_plan import MealPlan
from app.models.product import Product
from app.models.recipe import Recipe
from app.schemas.meal_plan import MealPlanLineCreate, MealPlanLineRead
from app.services.grocy_api import GrocyAPI, GrocyError, GrocyRequestError

MEAL_PLAN_JOB_TTL = 86400
MAX_ERROR_MESSAGE_LEN = 500

logger = logging.getLogger(__name__)


def _job_key(task_id: str) -> str:
    return f"meal_plan:job:{task_id}"


def write_job_state(
    task_id: str,
    *,
    state: str,
    current: int = 0,
    total: int = 0,
    errors: list[str] | None = None,
    summary: dict | None = None,
    error: str | None = None,
) -> None:
    r = get_redis()
    r.set(
        _job_key(task_id),
        json.dumps(
            {
                "task_id": task_id,
                "state": state,
                "current": current,
                "total": total,
                "errors": errors or [],
                "summary": summary,
                "error": error,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ),
        ex=MEAL_PLAN_JOB_TTL,
    )


def read_job_state(task_id: str) -> dict[str, Any] | None:
    r = get_redis()
    raw = r.get(_job_key(task_id))
    if raw is None:
        async_result = AsyncResult(task_id)
        if async_result.state == "PENDING":
            return None
        return {
            "task_id": task_id,
            "state": async_result.state,
            "current": 0,
            "total": 0,
            "errors": [],
            "summary": None,
            "error": str(async_result.result) if async_result.failed() else None,
        }
    data: dict[str, Any] = json.loads(raw)  # type: ignore[arg-type]
    return data


def truncate_error(message: str) -> str:
    if len(message) <= MAX_ERROR_MESSAGE_LEN:
        return message
    return message[: MAX_ERROR_MESSAGE_LEN - 3] + "..."


def ensure_product_synced(
    db: Session, *, grocy_api: GrocyAPI, household_id: int, grocy_product_id: int
) -> None:
    """Best-effort: if the product is missing locally, fetch it from Grocy.

    Errors are swallowed — meal-plan flows must keep working even if Grocy
    is unreachable. Callers should still tolerate a None product row afterwards.
    """
    found = db.exec(
        select(Product.id).where(
            Product.grocy_id == grocy_product_id,
            Product.household_id == household_id,
        )
    ).first()
    if found:
        return
    try:
        from app.services.product import sync_single_grocy_product

        sync_single_grocy_product(db, grocy_api, grocy_product_id, household_id=household_id)
    except Exception as e:
        logger.warning(
            "ensure_product_synced: failed to sync grocy_id=%s for household=%s: %s",
            grocy_product_id,
            household_id,
            e,
        )


def ensure_recipe_synced(
    db: Session, *, grocy_api: GrocyAPI, household_id: int, grocy_recipe_id: int
) -> None:
    """Best-effort lazy sync for a single recipe — mirror of ensure_product_synced."""
    found = db.exec(
        select(Recipe.id).where(
            Recipe.grocy_id == grocy_recipe_id,
            Recipe.household_id == household_id,
        )
    ).first()
    if found:
        return
    try:
        from app.services.recipe import sync_recipe_from_grocy

        sync_recipe_from_grocy(db, grocy_api, grocy_recipe_id, household_id=household_id)
    except Exception as e:
        logger.warning(
            "ensure_recipe_synced: failed to sync grocy_id=%s for household=%s: %s",
            grocy_recipe_id,
            household_id,
            e,
        )


def create_lines(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    lines: list[MealPlanLineCreate],
    grocy_api: GrocyAPI | None = None,
) -> list[MealPlan]:
    rows: list[MealPlan] = []
    for line in lines:
        row = MealPlan(
            household_id=household_id,
            user_id=user_id,
            type=line.type,
            day=line.day,
            section_id=line.section_id,
            product_id=line.product_id,
            product_amount=line.product_amount,
            product_amount_stock=line.product_amount_stock,
            product_qu_id=line.product_qu_id,
            product_qu_name=line.product_qu_name,
            recipe_id=line.recipe_id,
            recipe_servings=line.recipe_servings,
            status="pending",
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)

    # Best-effort lazy-sync any referenced product/recipe so the list view can
    # render a human name immediately. Failures are logged inside the helpers.
    if grocy_api is not None:
        product_ids = {
            int(line.product_id) for line in lines if line.type == "product" and line.product_id
        }
        recipe_ids = {
            int(line.recipe_id) for line in lines if line.type == "recipe" and line.recipe_id
        }
        for pid in product_ids:
            ensure_product_synced(
                db, grocy_api=grocy_api, household_id=household_id, grocy_product_id=pid
            )
        for rid in recipe_ids:
            ensure_recipe_synced(
                db, grocy_api=grocy_api, household_id=household_id, grocy_recipe_id=rid
            )

    return rows


def enrich_lines(
    db: Session,
    *,
    household_id: int,
    rows: list[MealPlan],
    grocy_api: GrocyAPI | None = None,
) -> list[MealPlanLineRead]:
    """Attach product/recipe names to each row, lazy-syncing missing ones.

    Lazy sync is best-effort: any Grocy error leaves the name as None, and the
    view falls back to "Product #ID"/"Recipe #ID" labels.
    """
    product_ids = {int(r.product_id) for r in rows if r.type == "product" and r.product_id}
    recipe_ids = {int(r.recipe_id) for r in rows if r.type == "recipe" and r.recipe_id}

    name_by_product: dict[int, str] = {}
    name_by_recipe: dict[int, str] = {}

    if product_ids:
        existing = db.exec(
            select(Product.grocy_id, Product.name).where(
                col(Product.grocy_id).in_(product_ids),
                Product.household_id == household_id,
            )
        ).all()
        name_by_product = {int(pid): str(name) for pid, name in existing}
        missing = product_ids - set(name_by_product.keys())
        if missing and grocy_api is not None:
            for pid in missing:
                ensure_product_synced(
                    db, grocy_api=grocy_api, household_id=household_id, grocy_product_id=pid
                )
            refetched = db.exec(
                select(Product.grocy_id, Product.name).where(
                    col(Product.grocy_id).in_(missing),
                    Product.household_id == household_id,
                )
            ).all()
            for pid, name in refetched:
                name_by_product[int(pid)] = str(name)

    if recipe_ids:
        existing_r = db.exec(
            select(Recipe.grocy_id, Recipe.name).where(
                col(Recipe.grocy_id).in_(recipe_ids),
                Recipe.household_id == household_id,
            )
        ).all()
        name_by_recipe = {int(rid): str(name) for rid, name in existing_r}
        missing_r = recipe_ids - set(name_by_recipe.keys())
        if missing_r and grocy_api is not None:
            for rid in missing_r:
                ensure_recipe_synced(
                    db, grocy_api=grocy_api, household_id=household_id, grocy_recipe_id=rid
                )
            refetched_r = db.exec(
                select(Recipe.grocy_id, Recipe.name).where(
                    col(Recipe.grocy_id).in_(missing_r),
                    Recipe.household_id == household_id,
                )
            ).all()
            for rid, name in refetched_r:
                name_by_recipe[int(rid)] = str(name)

    out: list[MealPlanLineRead] = []
    for row in rows:
        read = MealPlanLineRead.model_validate(row)
        if row.type == "product" and row.product_id is not None:
            read.product_name = name_by_product.get(int(row.product_id))
        elif row.type == "recipe" and row.recipe_id is not None:
            read.recipe_name = name_by_recipe.get(int(row.recipe_id))
        out.append(read)
    return out


def submit_batch(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    line_ids: list[int],
) -> str:
    if not line_ids:
        raise ValueError("line_ids must not be empty")

    owned = db.exec(
        select(MealPlan.id).where(
            col(MealPlan.id).in_(line_ids),
            MealPlan.household_id == household_id,
            MealPlan.status == "pending",
        )
    ).all()
    if len(owned) != len(line_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some line ids are missing, in another household, or not pending.",
        )

    from app.tasks.create_meal_plan_batch import create_meal_plan_batch_task

    task = create_meal_plan_batch_task.delay(
        user_id=user_id,
        household_id=household_id,
        line_ids=list(line_ids),
    )
    task_id: str = str(task.id)
    write_job_state(task_id, state="PENDING", current=0, total=len(line_ids))
    return task_id


def fetch_lines_in_range(
    db: Session,
    *,
    household_id: int,
    start_date: date,
    end_date: date,
) -> list[MealPlan]:
    return list(
        db.exec(
            select(MealPlan)
            .where(
                MealPlan.household_id == household_id,
                MealPlan.day >= start_date,
                MealPlan.day <= end_date,
            )
            .order_by(col(MealPlan.day), col(MealPlan.section_id), col(MealPlan.id))
        )
    )


def get_line_for_household(db: Session, *, household_id: int, line_id: int) -> MealPlan:
    row = db.exec(
        select(MealPlan).where(
            MealPlan.id == line_id,
            MealPlan.household_id == household_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line not found")
    return row


def delete_local_failed(db: Session, *, household_id: int, line_id: int) -> None:
    row = get_line_for_household(db, household_id=household_id, line_id=line_id)
    if row.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed rows can be deleted locally.",
        )
    db.delete(row)
    db.commit()


def retry_line(
    db: Session,
    *,
    household_id: int,
    line_id: int,
    user_id: int,
    grocy_api: GrocyAPI,
) -> MealPlan:
    row = get_line_for_household(db, household_id=household_id, line_id=line_id)
    if row.status not in ("failed", "pending", "syncing"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Line in status '{row.status}' cannot be retried.",
        )

    row.retry_count = 0
    row.error_message = None
    row.status = "syncing"
    db.add(row)
    db.commit()
    db.refresh(row)

    snapshot_ids, snapshot_max_ts = snapshot_grocy_ids_for_window(grocy_api, row.day, row.day)
    payload = build_grocy_payload(row)
    try:
        grocy_api.create_meal_plan_entry(payload)
    except (GrocyError, GrocyRequestError) as exc:
        row.status = "failed"
        row.retry_count = 1
        row.error_message = truncate_error(str(exc))
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    candidates = fetch_new_grocy_rows_window(
        grocy_api, row.day, row.day, snapshot_ids, snapshot_max_ts
    )
    assign_grocy_ids_in_order([row], candidates)
    db.add(row)
    db.commit()
    db.refresh(row)

    if row.grocy_meal_plan_id is not None:
        try:
            write_meal_plan_owner_userfield(grocy_api, row.grocy_meal_plan_id, user_id)
        except Exception as e:
            logger.warning(
                "retry_line: failed to write userfields.user_id on meal_plan %s: %s",
                row.grocy_meal_plan_id,
                e,
            )

    return row


def parse_userfield_user_id(grocy_row: dict) -> int | None:
    """Extract userfields.user_id from a Grocy meal_plan row, if int-parseable.

    Used by consumption to filter meal_plan to the caller's rows only.
    """
    uf = grocy_row.get("userfields")
    if not isinstance(uf, dict):
        return None
    raw = uf.get("user_id")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def lookup_user_id_for_grocy_meal_plan(
    db: Session, *, household_id: int, grocy_meal_plan_id: int
) -> int | None:
    """Fallback owner lookup: read meal_plans.user_id by Grocy id.

    Used when a Grocy row's userfields.user_id is NULL — typically because
    the userfield write failed or the row was created in Grocy UI directly.
    """
    stmt = select(MealPlan.user_id).where(
        MealPlan.household_id == household_id,
        MealPlan.grocy_meal_plan_id == grocy_meal_plan_id,
    )
    return db.exec(stmt).first()


def filter_meal_plan_to_user(
    db: Session,
    meal_plan: list[dict],
    *,
    household_id: int,
    user_id: int,
) -> list[dict]:
    """Keep only rows owned by `user_id`.

    Ownership comes from Grocy `userfields.user_id`; if absent there, we fall
    back to the local meal_plans.user_id (resolved by grocy_meal_plan_id).
    Rows whose owner cannot be determined to be `user_id` are dropped.
    """
    out: list[dict] = []
    for meal in meal_plan:
        owner = parse_userfield_user_id(meal)
        if owner is None:
            meal_id = meal.get("id")
            if meal_id is not None:
                owner = lookup_user_id_for_grocy_meal_plan(
                    db, household_id=household_id, grocy_meal_plan_id=int(meal_id)
                )
        if owner == user_id:
            out.append(meal)
    return out


def write_meal_plan_owner_userfield(
    grocy_api: GrocyAPI, grocy_meal_plan_id: int, user_id: int
) -> None:
    """PUT /userfields/meal_plan/{id} with {"user_id": "<n>"}.

    The userfield is named `user_id` in Grocy and stores our local user id.
    """
    grocy_api.put(
        f"/userfields/meal_plan/{int(grocy_meal_plan_id)}",
        data={"user_id": str(int(user_id))},
    )


def mark_done(db: Session, *, grocy_meal_plan_id: int) -> None:
    db.exec(  # type: ignore[call-overload]
        update(MealPlan)
        .where(col(MealPlan.grocy_meal_plan_id) == grocy_meal_plan_id)
        .values(done=True, done_at=datetime.now(UTC))
    )


def build_grocy_payload(row: MealPlan) -> dict:
    base: dict = {
        "day": row.day.isoformat(),
        "type": row.type,
        "section_id": row.section_id,
    }
    if row.type == "product":
        # Grocy expects `product_amount` in the product's stock unit. `product_qu_id`
        # is the unit the user introduced — Grocy stores it as the display unit but
        # converts/persists stock internally. See https://grocy.info/api docs:
        # the UI itself converts user input to stock units before POSTing.
        base.update(
            {
                "product_id": row.product_id,
                "product_amount": _decimal_to_str(row.product_amount_stock),
                "product_qu_id": row.product_qu_id,
            }
        )
    else:
        base.update(
            {
                "recipe_id": row.recipe_id,
                "recipe_servings": _decimal_to_str(row.recipe_servings),
            }
        )
    return base


def snapshot_grocy_ids_for_window(
    api: GrocyAPI, start_day: date, end_day: date
) -> tuple[set[int], str | None]:
    """Take a pre-batch snapshot of Grocy meal_plan rows in [start_day, end_day].

    Returns the set of existing Grocy ids AND the max `row_created_timestamp`
    seen across the snapshot (lexicographically comparable, format
    `YYYY-MM-DD HH:MM:SS`). Both are used after the batch to identify
    new-from-this-batch candidates: a row is "new" iff its id is not in the
    snapshot AND its row_created_timestamp is strictly greater than the
    snapshot max. The latter filter narrows the candidate set when multiple
    users write concurrently against the same tuple.
    """
    rows = api.get_meal_plan(start_date=start_day.isoformat(), end_date=end_day.isoformat()) or []
    ids = {int(r["id"]) for r in rows if "id" in r}
    max_ts = (
        max(
            (str(r.get("row_created_timestamp") or "") for r in rows),
            default="",
        )
        or None
    )
    return ids, max_ts


def fetch_new_grocy_rows_window(
    api: GrocyAPI,
    start_day: date,
    end_day: date,
    snapshot_ids: set[int],
    snapshot_max_ts: str | None = None,
) -> list[dict]:
    """Candidates created by *this* batch: not in the snapshot and (if a
    snapshot max timestamp is known) strictly newer than it."""
    rows = api.get_meal_plan(start_date=start_day.isoformat(), end_date=end_day.isoformat()) or []
    out: list[dict] = []
    for r in rows:
        if int(r["id"]) in snapshot_ids:
            continue
        if snapshot_max_ts:
            ts = str(r.get("row_created_timestamp") or "")
            if ts and ts <= snapshot_max_ts:
                continue
        out.append(r)
    return out


def _row_tuple(row: MealPlan) -> tuple:
    return (
        row.day.isoformat(),
        int(row.section_id),
        row.type,
        int(row.product_id or 0) if row.type == "product" else int(row.recipe_id or 0),
        _decimal_to_str(
            row.product_amount_stock if row.type == "product" else row.recipe_servings
        ),
    )


def _candidate_tuple(g: dict) -> tuple:
    g_type = str(g.get("type") or "product")
    return (
        str(g.get("day") or "")[:10],
        int(g.get("section_id") or 0),
        g_type,
        int(g.get("product_id") or 0) if g_type == "product" else int(g.get("recipe_id") or 0),
        _decimal_to_str(
            _decimal_or_none(g.get("product_amount"))
            if g_type == "product"
            else _decimal_or_none(g.get("recipe_servings"))
        ),
    )


def _apply_match_to_row(row: MealPlan, grocy_row: dict) -> None:
    row.grocy_meal_plan_id = int(grocy_row["id"])
    if row.type == "product":
        shadow = _int_or_none(grocy_row.get("recipe_id"))
        if shadow is not None and shadow < 0:
            row.grocy_shadow_recipe_id = shadow
    row.status = "synced"
    row.error_message = None


def assign_grocy_ids_in_order(
    rows: list[MealPlan], candidates: list[dict]
) -> tuple[list[MealPlan], list[MealPlan]]:
    by_tuple: dict[tuple, list[dict]] = {}
    for c in sorted(candidates, key=lambda x: int(x.get("id") or 0)):
        by_tuple.setdefault(_candidate_tuple(c), []).append(c)

    matched: list[MealPlan] = []
    unmatched: list[MealPlan] = []
    for row in rows:
        bucket = by_tuple.get(_row_tuple(row))
        if not bucket:
            unmatched.append(row)
            continue
        candidate = bucket.pop(0)
        _apply_match_to_row(row, candidate)
        matched.append(row)
    return matched, unmatched


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _decimal_to_str(value: Decimal | None) -> str:
    if value is None:
        return "0"
    return format(value.normalize(), "f")


def _parse_grocy_day(value: Any) -> date:
    if isinstance(value, date):
        return value
    s = str(value or "")[:10]
    return datetime.strptime(s, "%Y-%m-%d").date()


SECTIONS_TTL = 86400
UNITS_TTL = 86400


def _sections_key(household_id: int) -> str:
    return f"meal_plan:sections:household:{household_id}"


def _units_key(household_id: int, product_id: int) -> str:
    # v2: payload shape changed to include stock_to_grams_ml.
    return f"meal_plan:units:v2:household:{household_id}:product:{product_id}"


def get_or_load_sections(household_id: int, grocy_api: GrocyAPI) -> list[dict]:
    r = get_redis()
    cached = r.get(_sections_key(household_id))
    if cached:
        cached_sections: list[dict] = json.loads(cached)  # type: ignore[arg-type]
        return cached_sections
    raw = grocy_api.get_meal_plan_sections() or []
    sections = [
        {
            "section_id": int(s["id"]),
            "name": str(s.get("name") or ""),
            "sort_number": _int_or_none(s.get("sort_number")),
        }
        for s in raw
    ]
    r.set(_sections_key(household_id), json.dumps(sections), ex=SECTIONS_TTL)
    return sections


def get_or_load_units_for_product(
    household_id: int,
    product_id: int,
    grocy_api: GrocyAPI,
) -> dict:
    """Return {"units": [...], "stock_to_grams_ml": float|None}.

    `stock_to_grams_ml` is grams (or ml) per 1 stock unit. Used by the frontend
    to scale per-gram-stored nutrient values when the user enters an amount in
    a non-stock unit (e.g. grams of a piece-stocked product).
    """
    r = get_redis()
    cached = r.get(_units_key(household_id, product_id))
    if cached:
        cached_payload: dict = json.loads(cached)  # type: ignore[arg-type]
        return cached_payload

    product = grocy_api.get_product(product_id)
    stock_qu_id = _int_or_none(product.get("qu_id_stock"))

    conversions = grocy_api.get_quantity_unit_conversions_for_product(product_id) or []
    units_by_id: dict[int, dict] = {}
    for c in conversions:
        from_id = _int_or_none(c.get("from_qu_id"))
        to_id = _int_or_none(c.get("to_qu_id"))
        factor = c.get("factor")
        if from_id is None or to_id is None or factor is None:
            continue
        if to_id != stock_qu_id:
            continue
        try:
            factor_f = float(factor)
        except (TypeError, ValueError):
            continue
        units_by_id[from_id] = {
            "qu_id": from_id,
            "name": str(c.get("from_qu_name") or c.get("name") or ""),
            "name_plural": c.get("from_qu_name_plural"),
            "is_stock_default": from_id == stock_qu_id,
            "factor_to_stock": factor_f,
        }

    if stock_qu_id is not None and stock_qu_id not in units_by_id:
        units_by_id[stock_qu_id] = {
            "qu_id": stock_qu_id,
            "name": str(product.get("qu_id_stock_name") or ""),
            "name_plural": None,
            "is_stock_default": True,
            "factor_to_stock": 1.0,
        }

    stock_to_grams_ml: float | None
    if stock_qu_id is not None and grocy_api.is_gram_or_ml(stock_qu_id):
        stock_to_grams_ml = 1.0
    elif stock_qu_id is not None:
        try:
            stock_to_grams_ml = float(
                grocy_api.get_conversion_factor_safe(
                    product_id, stock_qu_id, grocy_api.gram_ml_units
                )
            )
        except Exception:
            stock_to_grams_ml = None
    else:
        stock_to_grams_ml = None

    payload = {
        "units": list(units_by_id.values()),
        "stock_to_grams_ml": stock_to_grams_ml,
    }
    r.set(_units_key(household_id, product_id), json.dumps(payload), ex=UNITS_TTL)
    return payload


def reconcile_window_for_batch(line_days: list[date]) -> tuple[date, date]:
    if not line_days:
        today = datetime.now(UTC).date()
        return today, today
    return min(line_days), max(line_days) + timedelta(days=0)
