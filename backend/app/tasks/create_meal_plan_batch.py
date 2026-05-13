"""Sequential per-line POST /objects/meal_plan with auto-retry, then reconcile-fetch
to assign Grocy IDs to local rows.
"""

from __future__ import annotations

import logging
import time

from celery.exceptions import SoftTimeLimitExceeded
from sqlmodel import col, select

from app.db.session import SessionLocal
from app.models.meal_plan import MealPlan
from app.services.grocy_api import (
    GrocyAuthError,
    GrocyConfigError,
    GrocyError,
    GrocyRequestError,
    build_grocy_api,
)
from app.services.meal_plan import (
    assign_grocy_ids_in_order,
    build_grocy_payload,
    fetch_new_grocy_rows_window,
    snapshot_grocy_ids_for_window,
    truncate_error,
    write_job_state,
    write_meal_plan_owner_userfield,
)
from app.tasks import celery

logger = logging.getLogger(__name__)

RETRY_DELAYS_S = (1, 3, 9)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, GrocyAuthError):
        return False
    if isinstance(exc, GrocyRequestError):
        return True
    msg = str(exc)
    return "Grocy returned error 5" in msg


@celery.task(
    name="app.tasks.create_meal_plan_batch.create_meal_plan_batch_task",
    bind=True,
    soft_time_limit=300,
    time_limit=360,
)
def create_meal_plan_batch_task(
    self, *, user_id: int, household_id: int, line_ids: list[int]
) -> dict:
    task_id = self.request.id
    db = SessionLocal()
    total = len(line_ids)
    errors: list[str] = []
    synced = 0
    failed = 0

    try:
        try:
            grocy_api = build_grocy_api(db, household_id, user_id)
        except GrocyConfigError as exc:
            write_job_state(task_id, state="FAILURE", current=0, total=total, error=exc.detail)
            return {"status": "error", "error": exc.detail}

        write_job_state(task_id, state="PROGRESS", current=0, total=total)

        rows = list(
            db.exec(
                select(MealPlan)
                .where(
                    col(MealPlan.id).in_(line_ids),
                    MealPlan.household_id == household_id,
                )
                .order_by(col(MealPlan.id))
            )
        )
        if not rows:
            write_job_state(
                task_id,
                state="FAILURE",
                current=0,
                total=total,
                error="No matching meal plan rows.",
            )
            return {"status": "error", "error": "No matching meal plan rows."}

        for row in rows:
            row.status = "syncing"
            db.add(row)
        db.commit()

        days = sorted({r.day for r in rows})
        start_day, end_day = days[0], days[-1]

        snapshot_ids, snapshot_max_ts = snapshot_grocy_ids_for_window(
            grocy_api, start_day, end_day
        )

        for index, row in enumerate(rows, start=1):
            try:
                _post_with_retry(grocy_api, row)
            except SoftTimeLimitExceeded:
                raise
            except (GrocyError, GrocyRequestError) as exc:
                row.status = "failed"
                row.retry_count = len(RETRY_DELAYS_S)
                row.error_message = truncate_error(str(exc))
                db.add(row)
                db.commit()
                failed += 1
                errors.append(f"line {row.id}: {row.error_message}")
            else:
                db.add(row)
                db.commit()

            write_job_state(
                task_id,
                state="PROGRESS",
                current=index,
                total=total,
                errors=errors,
            )

        candidates = fetch_new_grocy_rows_window(
            grocy_api, start_day, end_day, snapshot_ids, snapshot_max_ts
        )
        syncing_rows = list(
            db.exec(
                select(MealPlan)
                .where(
                    col(MealPlan.id).in_(line_ids),
                    MealPlan.status == "syncing",
                )
                .order_by(col(MealPlan.id))
            )
        )
        matched, unmatched = assign_grocy_ids_in_order(syncing_rows, candidates)
        for r in matched:
            db.add(r)
        db.commit()
        synced = len(matched)

        # Mirror ownership to Grocy `userfields.user_id` so a future reconcile from
        # any client can attribute the row to its real creator. Best-effort: a
        # userfield write failure must not flip an otherwise-synced row to failed.
        for r in matched:
            if r.grocy_meal_plan_id is None:
                continue
            try:
                write_meal_plan_owner_userfield(grocy_api, r.grocy_meal_plan_id, user_id)
            except Exception as e:
                logger.warning(
                    "create_meal_plan_batch: failed to write userfields.user_id on "
                    "meal_plan %s: %s",
                    r.grocy_meal_plan_id,
                    e,
                )

        summary = {
            "synced": synced,
            "failed": failed,
            "unmatched": len(unmatched),
            "errors": errors,
        }
        write_job_state(
            task_id,
            state="SUCCESS",
            current=total,
            total=total,
            errors=errors,
            summary=summary,
        )
        return {"status": "success", "result": summary}

    except SoftTimeLimitExceeded:
        write_job_state(
            task_id,
            state="FAILURE",
            current=0,
            total=total,
            errors=errors,
            error=(
                "Task time limit reached. Some rows may have been synced; the recovery "
                "sweep will mark stragglers failed within ~10 minutes."
            ),
        )
        return {"status": "error", "error": "soft_time_limit"}
    except Exception as exc:
        write_job_state(
            task_id,
            state="FAILURE",
            current=0,
            total=total,
            errors=errors,
            error=truncate_error(str(exc)),
        )
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


def _post_with_retry(grocy_api, row: MealPlan) -> None:
    payload = build_grocy_payload(row)
    last_exc: BaseException | None = None
    for attempt, delay in enumerate(RETRY_DELAYS_S, start=1):
        try:
            grocy_api.create_meal_plan_entry(payload)
            return
        except (GrocyError, GrocyRequestError) as exc:
            last_exc = exc
            if not _is_transient(exc) or attempt == len(RETRY_DELAYS_S):
                raise
            row.retry_count = attempt
            row.error_message = truncate_error(str(exc))
            time.sleep(delay)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry loop exited without success or exception")
