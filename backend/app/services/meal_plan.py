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

from app.core.meal_plan_cache import UNITS_TTL, units_key
from app.core.note_nutrients import parse_note_nutrients
from app.core.redis import get_redis
from app.models.meal_plan import MealPlan
from app.models.product import Product, ProductData
from app.models.recipe import Recipe, RecipeData
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
            product_grocy_id=line.product_grocy_id,
            product_amount=line.product_amount,
            product_amount_stock=line.product_amount_stock,
            product_qu_id=line.product_qu_id,
            recipe_grocy_id=line.recipe_grocy_id,
            recipe_servings=line.recipe_servings,
            note=line.note.strip() if line.note else None,
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
        grocy_product_ids = {
            int(line.product_grocy_id)
            for line in lines
            if line.type == "product" and line.product_grocy_id
        }
        grocy_recipe_ids = {
            int(line.recipe_grocy_id)
            for line in lines
            if line.type == "recipe" and line.recipe_grocy_id
        }
        for grocy_product_id in grocy_product_ids:
            ensure_product_synced(
                db,
                grocy_api=grocy_api,
                household_id=household_id,
                grocy_product_id=grocy_product_id,
            )
        for grocy_recipe_id in grocy_recipe_ids:
            ensure_recipe_synced(
                db,
                grocy_api=grocy_api,
                household_id=household_id,
                grocy_recipe_id=grocy_recipe_id,
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
    grocy_product_ids = {
        int(r.product_grocy_id) for r in rows if r.type == "product" and r.product_grocy_id
    }
    grocy_recipe_ids = {
        int(r.recipe_grocy_id) for r in rows if r.type == "recipe" and r.recipe_grocy_id
    }

    name_by_product: dict[int, str] = {}
    local_id_by_product: dict[int, int] = {}
    name_by_recipe: dict[int, str] = {}
    local_id_by_recipe: dict[int, int] = {}

    if grocy_product_ids:
        existing = db.exec(
            select(Product.grocy_id, Product.name, Product.id).where(
                col(Product.grocy_id).in_(grocy_product_ids),
                Product.household_id == household_id,
            )
        ).all()
        for pid, name, local_id in existing:
            name_by_product[int(pid)] = str(name)
            if local_id is not None:
                local_id_by_product[int(pid)] = int(local_id)
        missing = grocy_product_ids - set(name_by_product.keys())
        if missing and grocy_api is not None:
            for grocy_product_id in missing:
                ensure_product_synced(
                    db,
                    grocy_api=grocy_api,
                    household_id=household_id,
                    grocy_product_id=grocy_product_id,
                )
            refetched = db.exec(
                select(Product.grocy_id, Product.name, Product.id).where(
                    col(Product.grocy_id).in_(missing),
                    Product.household_id == household_id,
                )
            ).all()
            for pid, name, local_id in refetched:
                name_by_product[int(pid)] = str(name)
                if local_id is not None:
                    local_id_by_product[int(pid)] = int(local_id)

    if grocy_recipe_ids:
        existing_r = db.exec(
            select(Recipe.grocy_id, Recipe.name, Recipe.id).where(
                col(Recipe.grocy_id).in_(grocy_recipe_ids),
                Recipe.household_id == household_id,
            )
        ).all()
        for rid, name, local_id in existing_r:
            name_by_recipe[int(rid)] = str(name)
            if local_id is not None:
                local_id_by_recipe[int(rid)] = int(local_id)
        missing_r = grocy_recipe_ids - set(name_by_recipe.keys())
        if missing_r and grocy_api is not None:
            for grocy_recipe_id in missing_r:
                ensure_recipe_synced(
                    db,
                    grocy_api=grocy_api,
                    household_id=household_id,
                    grocy_recipe_id=grocy_recipe_id,
                )
            refetched_r = db.exec(
                select(Recipe.grocy_id, Recipe.name, Recipe.id).where(
                    col(Recipe.grocy_id).in_(missing_r),
                    Recipe.household_id == household_id,
                )
            ).all()
            for rid, name, local_id in refetched_r:
                name_by_recipe[int(rid)] = str(name)
                if local_id is not None:
                    local_id_by_recipe[int(rid)] = int(local_id)

    qu_name_by_pair: dict[tuple[int, int], str] = {}
    if grocy_api is not None:
        product_qu_pairs = {
            (int(r.product_grocy_id), int(r.product_qu_id))
            for r in rows
            if r.type == "product"
            and r.product_grocy_id is not None
            and r.product_qu_id is not None
        }
        for grocy_product_id, qu_id in product_qu_pairs:
            try:
                payload = get_or_load_units_for_product(household_id, grocy_product_id, grocy_api)
            except Exception as e:
                logger.warning(
                    "enrich_lines: failed to load units for product %s: %s",
                    grocy_product_id,
                    e,
                )
                continue
            for unit in payload.get("units") or []:
                if int(unit.get("qu_id") or 0) == qu_id:
                    qu_name_by_pair[(grocy_product_id, qu_id)] = str(unit.get("name") or "")
                    break

    out: list[MealPlanLineRead] = []
    for row in rows:
        read = MealPlanLineRead.model_validate(row)
        if row.type == "product" and row.product_grocy_id is not None:
            read.product_name = name_by_product.get(int(row.product_grocy_id))
            read.product_local_id = local_id_by_product.get(int(row.product_grocy_id))
            if row.product_qu_id is not None:
                read.product_qu_name = qu_name_by_pair.get(
                    (int(row.product_grocy_id), int(row.product_qu_id))
                )
        elif row.type == "recipe" and row.recipe_grocy_id is not None:
            read.recipe_name = name_by_recipe.get(int(row.recipe_grocy_id))
            read.recipe_local_id = local_id_by_recipe.get(int(row.recipe_grocy_id))
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
            MealPlan.user_id == user_id,
            MealPlan.status == "pending",
        )
    ).all()
    if len(owned) != len(line_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some line ids are missing, owned by another user, or not pending.",
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
    user_id: int,
    start_date: date,
    end_date: date,
) -> list[MealPlan]:
    return list(
        db.exec(
            select(MealPlan)
            .where(
                MealPlan.household_id == household_id,
                MealPlan.user_id == user_id,
                MealPlan.day >= start_date,
                MealPlan.day <= end_date,
            )
            .order_by(col(MealPlan.day), col(MealPlan.section_id), col(MealPlan.id))
        )
    )


def get_line_for_owner(db: Session, *, household_id: int, user_id: int, line_id: int) -> MealPlan:
    """Fetch a meal plan line scoped to household + owner.

    Returns 404 for rows that exist but belong to another user — same response
    as for nonexistent ids, so we don't leak existence to non-owners.
    """
    row = db.exec(
        select(MealPlan).where(
            MealPlan.id == line_id,
            MealPlan.household_id == household_id,
            MealPlan.user_id == user_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line not found")
    return row


def delete_local_failed(db: Session, *, household_id: int, user_id: int, line_id: int) -> None:
    row = get_line_for_owner(db, household_id=household_id, user_id=user_id, line_id=line_id)
    if row.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed rows can be deleted locally.",
        )
    db.delete(row)
    db.commit()


_EDIT_STATUS_MESSAGES = {
    "pending": "Line is queued for sync; try again once it settles.",
    "syncing": "Line is currently syncing to Grocy; try again in a moment.",
    "failed": "Failed lines cannot be edited; delete and re-add.",
}

_DELETE_STATUS_MESSAGES = {
    "pending": "Line is queued for sync; try again once it settles.",
    "syncing": "Line is currently syncing to Grocy; try again in a moment.",
    "failed": "Failed lines must be deleted via the local delete action.",
}

_DONE_LOCKED_MESSAGE = (
    "Line is marked done and cannot be modified from this app; delete it directly in Grocy."
)


def update_line_amount(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    line_id: int,
    grocy_api: GrocyAPI,
    product_amount: Decimal | None = None,
    product_amount_stock: Decimal | None = None,
    recipe_servings: Decimal | None = None,
    note: str | None = None,
) -> MealPlan:
    """Edit a synced meal plan row's amount (product), servings (recipe), or note text.

    PUTs to Grocy first; only commits local changes if Grocy succeeds.
    """
    row = get_line_for_owner(db, household_id=household_id, user_id=user_id, line_id=line_id)

    if row.status != "synced":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_EDIT_STATUS_MESSAGES.get(
                row.status, f"Line in status '{row.status}' cannot be edited."
            ),
        )
    if row.done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_DONE_LOCKED_MESSAGE,
        )

    if row.type == "product":
        if product_amount is None or product_amount_stock is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product lines require both product_amount and product_amount_stock.",
            )
        if recipe_servings is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recipe_servings is not valid for a product line.",
            )
        if note is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="note is not valid for a product line.",
            )
    elif row.type == "recipe":
        if recipe_servings is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipe lines require recipe_servings.",
            )
        if product_amount is not None or product_amount_stock is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product_amount fields are not valid for a recipe line.",
            )
        if note is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="note is not valid for a recipe line.",
            )
    else:  # note
        if note is None or not note.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note lines require a non-empty note.",
            )
        if (
            product_amount is not None
            or product_amount_stock is not None
            or recipe_servings is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product/recipe fields are not valid for a note line.",
            )

    payload = build_grocy_payload_for_edit(
        row,
        product_amount_stock=product_amount_stock,
        recipe_servings=recipe_servings,
        note=note.strip() if note is not None else None,
    )
    try:
        grocy_api.put(f"/objects/meal_plan/{row.grocy_meal_plan_id}", data=payload)
    except GrocyError as exc:
        # Covers GrocyRequestError (subclass) too.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Grocy update failed: {exc}",
        ) from exc

    if row.type == "product":
        row.product_amount = product_amount
        row.product_amount_stock = product_amount_stock
    elif row.type == "recipe":
        row.recipe_servings = recipe_servings
    else:
        row.note = note.strip() if note is not None else row.note

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def toggle_note_done(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    line_id: int,
    done: bool,
    grocy_api: GrocyAPI,
) -> MealPlan:
    """Toggle `done` flag on a `type="note"` row.

    Notes are not consumable (no stock to deduct), so they need a separate
    toggle that doesn't go through the consumption flow. Product/recipe lines
    must use consumption — calling this for them returns 400.
    """
    row = get_line_for_owner(db, household_id=household_id, user_id=user_id, line_id=line_id)

    if row.type != "note":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only note lines can be toggled via this endpoint; "
            "use consumption flow for product/recipe lines.",
        )
    if row.status != "synced":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Line in status '{row.status}' cannot be toggled.",
        )

    try:
        grocy_api.put(
            f"/objects/meal_plan/{row.grocy_meal_plan_id}",
            data={"done": 1 if done else 0},
        )
    except GrocyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Grocy update failed: {exc}",
        ) from exc

    row.done = done
    row.done_at = datetime.now(UTC) if done else None
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_synced_line(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    line_id: int,
    grocy_api: GrocyAPI,
) -> None:
    """Delete a synced meal plan row from Grocy and locally.

    Grocy 404 is treated as "already gone" — local delete proceeds.
    Any other Grocy error → 502, local row preserved.
    """
    row = get_line_for_owner(db, household_id=household_id, user_id=user_id, line_id=line_id)

    if row.status != "synced":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_DELETE_STATUS_MESSAGES.get(
                row.status, f"Line in status '{row.status}' cannot be deleted."
            ),
        )
    # Product/recipe rows are locked once consumed (stock has been deducted).
    # Notes have no stock side-effects so done notes are freely deletable.
    if row.done and row.type != "note":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_DONE_LOCKED_MESSAGE,
        )

    try:
        grocy_api.delete(f"/objects/meal_plan/{row.grocy_meal_plan_id}")
    except GrocyError as exc:
        # GrocyRequestError (subclass) has http_status=None, so it falls through
        # to the 502 branch — correct: network errors should preserve the row.
        if exc.http_status == 404:
            logger.warning(
                "delete_synced_line: Grocy meal_plan %s already gone; deleting locally",
                row.grocy_meal_plan_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Grocy delete failed: {exc}",
            ) from exc

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
    row = get_line_for_owner(db, household_id=household_id, user_id=user_id, line_id=line_id)
    # `syncing` is intentionally excluded: a batch task may still be in flight
    # against this row, and a second POST would create a duplicate Grocy entry.
    # The recovery sweep flips truly-stuck syncing rows to `failed` after ~10
    # minutes, at which point retry becomes available again.
    if row.status not in ("failed", "pending"):
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

    # Take a snapshot only as a fallback path — modern Grocy returns
    # created_object_id directly from POST and we don't need to reconcile.
    snapshot_ids, snapshot_max_ts = snapshot_grocy_ids_for_window(grocy_api, row.day, row.day)
    payload = build_grocy_payload(row)
    try:
        response = grocy_api.create_meal_plan_entry(payload)
    except (GrocyError, GrocyRequestError) as exc:
        row.status = "failed"
        row.retry_count = 1
        row.error_message = truncate_error(str(exc))
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    created_id: int | None = None
    if isinstance(response, dict):
        raw = response.get("created_object_id")
        if raw is not None:
            try:
                created_id = int(raw)
            except (TypeError, ValueError):
                created_id = None

    if created_id is not None:
        row.grocy_meal_plan_id = created_id
        row.status = "synced"
        row.error_message = None
        row.retry_count = 0
    else:
        # Fallback: reconcile via snapshot diff + tuple match.
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


def mark_done(
    db: Session,
    *,
    household_id: int,
    grocy_meal_plan_id: int,
    grocy_shadow_recipe_id: int | None = None,
) -> None:
    payload: dict[str, Any] = {"done": True, "done_at": datetime.now(UTC)}
    if grocy_shadow_recipe_id is not None:
        payload["grocy_shadow_recipe_id"] = grocy_shadow_recipe_id
    stmt = (
        update(MealPlan)
        .where(
            col(MealPlan.household_id) == household_id,
            col(MealPlan.grocy_meal_plan_id) == grocy_meal_plan_id,
        )
        .values(**payload)
    )
    db.exec(stmt)  # type: ignore[call-overload]


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
        # NOTE: "product_id" / "recipe_id" here are Grocy-side payload keys — the
        # value comes from our renamed local column `*_grocy_id`.
        base.update(
            {
                "product_id": row.product_grocy_id,
                "product_amount": _decimal_to_str(row.product_amount_stock),
                "product_qu_id": row.product_qu_id,
            }
        )
    elif row.type == "recipe":
        base.update(
            {
                "recipe_id": row.recipe_grocy_id,
                "recipe_servings": _decimal_to_str(row.recipe_servings),
            }
        )
    else:  # note
        base["note"] = row.note or ""
    return base


def build_grocy_payload_for_edit(
    row: MealPlan,
    *,
    product_amount_stock: Decimal | None,
    recipe_servings: Decimal | None,
    note: str | None = None,
) -> dict:
    """Assemble the PUT body for editing a row's amount/servings/note.

    Same shape as `build_grocy_payload(row)` but substitutes the override values.
    We build the payload before mutating the row so Grocy failure leaves the
    local row untouched.
    """
    base: dict = {
        "day": row.day.isoformat(),
        "type": row.type,
        "section_id": row.section_id,
    }
    if row.type == "product":
        base.update(
            {
                "product_id": row.product_grocy_id,
                "product_amount": _decimal_to_str(product_amount_stock),
                "product_qu_id": row.product_qu_id,
            }
        )
    elif row.type == "recipe":
        base.update(
            {
                "recipe_id": row.recipe_grocy_id,
                "recipe_servings": _decimal_to_str(recipe_servings),
            }
        )
    else:  # note
        base["note"] = note if note is not None else (row.note or "")
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
    if row.type == "product":
        key1: int | str = int(row.product_grocy_id or 0)
        key2 = _decimal_to_str(row.product_amount_stock)
    elif row.type == "recipe":
        key1 = int(row.recipe_grocy_id or 0)
        key2 = _decimal_to_str(row.recipe_servings)
    else:  # note
        key1 = (row.note or "").strip()
        key2 = ""
    return (row.day.isoformat(), int(row.section_id), row.type, key1, key2)


def _candidate_tuple(g: dict) -> tuple:
    # NOTE: g.get("product_id") / g.get("recipe_id") are Grocy-side response
    # keys — do not rename to *_grocy_id. They come from the Grocy API.
    g_type = str(g.get("type") or "product")
    if g_type == "product":
        key1: int | str = int(g.get("product_id") or 0)
        key2 = _decimal_to_str(_decimal_or_none(g.get("product_amount")))
    elif g_type == "recipe":
        key1 = int(g.get("recipe_id") or 0)
        key2 = _decimal_to_str(_decimal_or_none(g.get("recipe_servings")))
    else:  # note
        key1 = str(g.get("note") or "").strip()
        key2 = ""
    return (
        str(g.get("day") or "")[:10],
        int(g.get("section_id") or 0),
        g_type,
        key1,
        key2,
    )


def _apply_match_to_row(row: MealPlan, grocy_row: dict) -> None:
    row.grocy_meal_plan_id = int(grocy_row["id"])
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


def pull_grocy_day_to_local(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    day: date,
    grocy_api: GrocyAPI,
) -> dict[str, Any]:
    """Pull a Grocy meal_plan day into local `meal_plans` without POSTing back.

    Recovers from the case where rows were created directly in Grocy (no local
    mirror) - without it, consumption flows drop the rows because
    `filter_meal_plan_to_user` cannot resolve an owner.
    """
    grocy_rows = (
        grocy_api.get_meal_plan(start_date=day.isoformat(), end_date=day.isoformat()) or []
    )

    existing_ids = set(
        db.exec(
            select(MealPlan.grocy_meal_plan_id).where(
                MealPlan.household_id == household_id,
                col(MealPlan.grocy_meal_plan_id).is_not(None),
            )
        ).all()
    )

    pulled = 0
    pulled_already_done = 0
    skipped_already_local = 0
    skipped_other_owner = 0
    skipped_notes = 0  # rows of unknown type (not product/recipe/note)

    inserted_rows: list[MealPlan] = []
    rows_needing_userfield: list[int] = []

    for g in grocy_rows:
        owner = parse_userfield_user_id(g)
        if owner is not None and owner != user_id:
            skipped_other_owner += 1
            continue

        grocy_id = _int_or_none(g.get("id"))
        if grocy_id is None:
            continue
        if grocy_id in existing_ids:
            skipped_already_local += 1
            continue

        g_type = str(g.get("type") or "product")
        if g_type not in ("product", "recipe", "note"):
            skipped_notes += 1
            continue

        is_done = _grocy_bool(g.get("done"))
        amount = _decimal_or_none(g.get("product_amount"))

        row = MealPlan(
            household_id=household_id,
            user_id=user_id,
            grocy_meal_plan_id=grocy_id,
            type=g_type,
            day=_parse_grocy_day(g.get("day")),
            section_id=int(g.get("section_id") or 0),
            product_grocy_id=_int_or_none(g.get("product_id")) if g_type == "product" else None,
            product_amount=amount if g_type == "product" else None,
            product_amount_stock=amount if g_type == "product" else None,
            product_qu_id=_int_or_none(g.get("product_qu_id")) if g_type == "product" else None,
            recipe_grocy_id=_int_or_none(g.get("recipe_id")) if g_type == "recipe" else None,
            recipe_servings=_decimal_or_none(g.get("recipe_servings"))
            if g_type == "recipe"
            else None,
            note=(str(g.get("note") or "").strip() or None) if g_type == "note" else None,
            status="synced",
            done=is_done,
            done_at=datetime.now(UTC) if is_done else None,
        )
        db.add(row)
        inserted_rows.append(row)
        if is_done:
            pulled_already_done += 1
        else:
            pulled += 1

        if owner is None:
            rows_needing_userfield.append(grocy_id)

    if inserted_rows:
        db.commit()
        for row in inserted_rows:
            db.refresh(row)

    # Product/recipe lazy sync is handled by enrich_lines at the endpoint layer.

    userfield_write_failures = 0
    for grocy_id in rows_needing_userfield:
        try:
            write_meal_plan_owner_userfield(grocy_api, grocy_id, user_id)
        except Exception as e:
            userfield_write_failures += 1
            logger.warning(
                "pull_grocy_day_to_local: userfield PUT failed for grocy_id=%s: %s",
                grocy_id,
                e,
            )

    return {
        "pulled": pulled,
        "pulled_already_done": pulled_already_done,
        "skipped_already_local": skipped_already_local,
        "skipped_other_owner": skipped_other_owner,
        "skipped_notes": skipped_notes,
        "userfield_write_failures": userfield_write_failures,
        "rows": inserted_rows,
    }


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _grocy_bool(value: Any) -> bool:
    # Grocy serializes booleans as the strings "0" / "1"; bool("0") is True,
    # so we must coerce through int first.
    if isinstance(value, str):
        return value not in ("", "0")
    return bool(value)


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


def _sections_key(household_id: int) -> str:
    return f"meal_plan:sections:household:{household_id}"


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
    grocy_product_id: int,
    grocy_api: GrocyAPI | None,
) -> dict:
    """Return {"units": [...], "stock_to_grams_ml": float|None}.

    `stock_to_grams_ml` is grams (or ml) per 1 stock unit. Used by the frontend
    to scale per-gram-stored nutrient values when the user enters an amount in
    a non-stock unit (e.g. grams of a piece-stocked product).

    On a Redis cache miss with `grocy_api is None` (the MCP path, which may not
    call Grocy), returns an empty payload with `stock_to_grams_ml=None` instead of
    hitting Grocy. A cache miss WITH a real `grocy_api` still loads from Grocy.
    """
    r = get_redis()
    cached = r.get(units_key(household_id, grocy_product_id))
    if cached:
        cached_payload: dict = json.loads(cached)  # type: ignore[arg-type]
        return cached_payload

    if grocy_api is None:
        return {"units": [], "stock_to_grams_ml": None}

    product = grocy_api.get_product(grocy_product_id)
    stock_qu_id = _int_or_none(product.get("qu_id_stock"))

    conversions = grocy_api.get_quantity_unit_conversions_for_product(grocy_product_id) or []
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
                    grocy_product_id, stock_qu_id, grocy_api.gram_ml_units
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
    r.set(units_key(household_id, grocy_product_id), json.dumps(payload), ex=UNITS_TTL)
    return payload


def reconcile_window_for_batch(line_days: list[date]) -> tuple[date, date]:
    if not line_days:
        today = datetime.now(UTC).date()
        return today, today
    return min(line_days), max(line_days) + timedelta(days=0)


_NUTRIENT_KEYS = (
    ("kcal", "calories"),
    ("protein", "proteins"),
    ("carbs", "carbohydrates"),
    ("sugars", "carbohydrates_of_sugars"),
    ("fat", "fats"),
    ("sat_fat", "fats_saturated"),
    ("salt", "salt"),
    ("fibers", "fibers"),
)


def _zero_totals() -> dict[str, float]:
    return {out_key: 0.0 for out_key, _ in _NUTRIENT_KEYS}


def _latest_product_data_for(db: Session, product_local_id: int) -> ProductData | None:
    stmt = (
        select(ProductData)
        .where(ProductData.product_id == product_local_id)
        .order_by(col(ProductData.created_at).desc())
        .limit(1)
    )
    return db.exec(stmt).first()


def _latest_recipe_data_for(db: Session, recipe_local_id: int) -> RecipeData | None:
    stmt = (
        select(RecipeData)
        .where(RecipeData.recipe_id == recipe_local_id)
        .order_by(col(RecipeData.consumed_at).desc())
        .limit(1)
    )
    return db.exec(stmt).first()


def compute_daily_totals(
    db: Session,
    *,
    household_id: int,
    user_id: int,
    day: date,
    grocy_api: GrocyAPI | None = None,
) -> dict[str, Any]:
    """Sum nutrition across the caller's meal-plan rows for a single day.

    Includes rows with status in ('pending','syncing','synced'); excludes 'failed'.
    Products/recipes without nutrient data (or products whose stock unit cannot
    be resolved to grams/ml) are listed in `missing_items` and contribute zero.
    Scoped to the calling user — each household member sees only their own plan.

    Also returns a per-line `breakdown` (local ids only) whose macros sum to
    `totals`, and `omitted_lines`: a count of product/recipe lines that could not
    resolve to a local id / nutrients / units. `grocy_api` may be None (MCP path);
    units then come from cache only — a miss marks the line omitted instead of
    calling Grocy. Web callers ignore the new keys.
    """
    rows = db.exec(
        select(MealPlan).where(
            MealPlan.household_id == household_id,
            MealPlan.user_id == user_id,
            MealPlan.day == day,
            col(MealPlan.status) != "failed",
        )
    ).all()

    totals = _zero_totals()
    missing: list[dict[str, Any]] = []
    seen_missing: set[tuple[str, int]] = set()
    breakdown: list[dict[str, Any]] = []
    omitted_lines = 0

    def mark_missing(kind: str, grocy_id: int, name: str) -> None:
        key = (kind, grocy_id)
        if key in seen_missing:
            return
        seen_missing.add(key)
        missing.append({"type": kind, "grocy_id": grocy_id, "name": name})

    products_by_grocy: dict[int, Product] = {}
    recipes_by_grocy: dict[int, Recipe] = {}

    for row in rows:
        if row.type == "product":
            if row.product_grocy_id is None or row.product_amount_stock is None:
                continue
            product = products_by_grocy.get(row.product_grocy_id)
            if product is None:
                product = db.exec(
                    select(Product).where(
                        Product.grocy_id == row.product_grocy_id,
                        Product.household_id == household_id,
                    )
                ).first()
                if product is not None:
                    products_by_grocy[row.product_grocy_id] = product

            display_name = product.name if product else f"Product #{row.product_grocy_id}"

            if product is None or product.id is None:
                mark_missing("product", row.product_grocy_id, display_name)
                omitted_lines += 1
                continue

            pdata = _latest_product_data_for(db, product.id)
            if pdata is None or pdata.calories is None:
                mark_missing("product", row.product_grocy_id, display_name)
                omitted_lines += 1
                continue

            units_payload = get_or_load_units_for_product(
                household_id, row.product_grocy_id, grocy_api
            )
            stock_to_grams = units_payload.get("stock_to_grams_ml")
            if stock_to_grams is None:
                mark_missing("product", row.product_grocy_id, display_name)
                omitted_lines += 1
                continue

            grams = float(row.product_amount_stock) * float(stock_to_grams)
            line = {
                "type": "product",
                "id": product.id,
                "name": product.name,
                "amount": grams,
                "done": bool(row.done),
            }
            for out_key, attr in _NUTRIENT_KEYS:
                per_gram = getattr(pdata, attr) or 0.0
                contributed = per_gram * grams
                totals[out_key] += contributed
                line[out_key] = round(contributed, 2)
            breakdown.append(line)

        elif row.type == "recipe":
            if row.recipe_grocy_id is None or row.recipe_servings is None:
                continue
            recipe = recipes_by_grocy.get(row.recipe_grocy_id)
            if recipe is None:
                recipe = db.exec(
                    select(Recipe).where(
                        Recipe.grocy_id == row.recipe_grocy_id,
                        Recipe.household_id == household_id,
                    )
                ).first()
                if recipe is not None:
                    recipes_by_grocy[row.recipe_grocy_id] = recipe

            display_name = recipe.name if recipe else f"Recipe #{row.recipe_grocy_id}"

            if recipe is None or recipe.id is None:
                mark_missing("recipe", row.recipe_grocy_id, display_name)
                omitted_lines += 1
                continue

            rdata = _latest_recipe_data_for(db, recipe.id)
            if rdata is None or rdata.calories is None:
                mark_missing("recipe", row.recipe_grocy_id, display_name)
                omitted_lines += 1
                continue

            servings = float(row.recipe_servings)
            line = {
                "type": "recipe",
                "id": recipe.id,
                "name": recipe.name,
                "servings": servings,
                "done": bool(row.done),
            }
            for out_key, attr in _NUTRIENT_KEYS:
                per_serving = getattr(rdata, attr) or 0.0
                contributed = per_serving * servings
                totals[out_key] += contributed
                line[out_key] = round(contributed, 2)
            breakdown.append(line)

        elif row.type == "note":
            if not row.note:
                continue
            parsed = parse_note_nutrients(row.note)
            if not parsed:
                continue
            line = {
                "type": "note",
                "id": None,
                "name": row.note,
                "done": bool(row.done),
            }
            for out_key, attr in _NUTRIENT_KEYS:
                value = parsed.get(attr)
                contributed = value if value is not None else 0.0
                totals[out_key] += contributed
                line[out_key] = round(contributed, 2)
            breakdown.append(line)

    return {
        **totals,
        "missing_items": missing,
        "breakdown": breakdown,
        "omitted_lines": omitted_lines,
    }
