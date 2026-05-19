"""Shared scaffolding for background availability-check Celery tasks.

Used by `day_check_task` and `range_check_task` — both follow the same
PROGRESS → SUCCESS|FAILURE lifecycle, write JSON state to a Redis key, and
delegate the actual work to a service callable.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from app.core.redis import get_redis
from app.db.session import SessionLocal
from app.services.consumption import ConsumptionError
from app.services.grocy_api import GrocyAPI, GrocyConfigError, build_grocy_api

TTL_24H = 86400


def store_state(
    r: Any,
    key: str,
    state: str,
    task_id: str,
    *,
    step: str | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    payload = {
        "state": state,
        "task_id": task_id,
        "step": step,
        "created_at": datetime.now(UTC).isoformat(),
        "result": result,
        "error": error,
        **extra,
    }
    r.set(key, json.dumps(payload), ex=TTL_24H)


def run_availability_check_job(
    task: Any,
    redis_key: str,
    runner: Callable[[Session, GrocyAPI], dict[str, Any]],
    *,
    user_id: int,
    household_id: int,
    progress_step: str,
    extra_state: dict[str, Any] | None = None,
) -> None:
    """Common scaffolding: Redis state transitions + DB lifecycle + Grocy build.

    `runner(db, grocy_api)` returns the result dict that lands in the SUCCESS
    state. Any ConsumptionError / ValueError / Exception is caught and turned
    into FAILURE state with the message.
    """
    r = get_redis()
    task_id = task.request.id
    db = SessionLocal()
    extra = extra_state or {}

    try:
        store_state(r, redis_key, "PROGRESS", task_id, step="Connecting to Grocy...", **extra)

        try:
            grocy_api = build_grocy_api(db, household_id, user_id)
        except GrocyConfigError as cfg_err:
            store_state(r, redis_key, "FAILURE", task_id, error=cfg_err.detail, **extra)
            return

        store_state(r, redis_key, "PROGRESS", task_id, step=progress_step, **extra)
        result = runner(db, grocy_api)
        store_state(r, redis_key, "SUCCESS", task_id, result=result, **extra)

    except (ConsumptionError, ValueError) as exc:
        store_state(r, redis_key, "FAILURE", task_id, error=str(exc), **extra)
    except Exception as exc:
        store_state(r, redis_key, "FAILURE", task_id, error=str(exc), **extra)
    finally:
        db.close()
