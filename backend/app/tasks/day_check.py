from app.services.consumption import check_products_availability
from app.tasks import celery
from app.tasks._availability_check import run_availability_check_job

DAY_CHECK_OUTCOME_TTL = 43200  # 12h — only used by the DELETE endpoint


def redis_key(user_id: int, household_id: int, date: str) -> str:
    return f"day_check:{user_id}:{household_id}:{date}"


def outcome_key(user_id: int, household_id: int, date: str) -> str:
    return f"day_check:outcome:{user_id}:{household_id}:{date}"


@celery.task(
    name="app.tasks.day_check.day_check_task",
    bind=True,
)
def day_check_task(self, user_id: int, household_id: int, date: str):
    """Background task: check product availability for a single day."""
    run_availability_check_job(
        self,
        redis_key(user_id, household_id, date),
        runner=lambda db, api: check_products_availability(
            db,
            api,
            date,
            household_id=household_id,
            user_id=user_id,
        ),
        user_id=user_id,
        household_id=household_id,
        progress_step=f"Checking availability for {date}...",
        extra_state={"date": date},
    )
