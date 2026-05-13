import json
from datetime import UTC, datetime

from app.core.redis import get_redis
from app.db.session import SessionLocal
from app.services.consumption import ConsumptionError, check_range_availability
from app.services.grocy_api import GrocyConfigError, build_grocy_api
from app.tasks import celery

RANGE_CHECK_TTL = 86400  # 24 hours


def _redis_key(user_id: int, household_id: int) -> str:
    return f"range_check:{user_id}:{household_id}"


def _store_state(r, key, state, task_id, start_date, end_date, **kwargs):
    r.set(
        key,
        json.dumps(
            {
                "state": state,
                "task_id": task_id,
                "step": kwargs.get("step"),
                "start_date": start_date,
                "end_date": end_date,
                "created_at": datetime.now(UTC).isoformat(),
                "result": kwargs.get("result"),
                "error": kwargs.get("error"),
            }
        ),
        ex=RANGE_CHECK_TTL,
    )


@celery.task(
    name="app.tasks.range_check.range_check_task",
    bind=True,
)
def range_check_task(self, user_id: int, household_id: int, start_date: str, end_date: str):
    """Background task: check product availability for a date range."""
    r = get_redis()
    key = _redis_key(user_id, household_id)
    task_id = self.request.id
    db = SessionLocal()

    try:
        _store_state(
            r,
            key,
            "PROGRESS",
            task_id,
            start_date,
            end_date,
            step="Connecting to Grocy...",
        )

        try:
            grocy_api = build_grocy_api(db, household_id, user_id)
        except GrocyConfigError as cfg_err:
            _store_state(
                r,
                key,
                "FAILURE",
                task_id,
                start_date,
                end_date,
                error=cfg_err.detail,
            )
            return

        _store_state(
            r,
            key,
            "PROGRESS",
            task_id,
            start_date,
            end_date,
            step=f"Checking availability for {start_date} — {end_date}...",
        )

        result = check_range_availability(
            db,
            grocy_api,
            household_id=household_id,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
        )

        _store_state(
            r,
            key,
            "SUCCESS",
            task_id,
            start_date,
            end_date,
            result=result,
        )

    except (ConsumptionError, ValueError) as exc:
        _store_state(
            r,
            key,
            "FAILURE",
            task_id,
            start_date,
            end_date,
            error=str(exc),
        )
    except Exception as exc:
        _store_state(
            r,
            key,
            "FAILURE",
            task_id,
            start_date,
            end_date,
            error=str(exc),
        )
    finally:
        db.close()
