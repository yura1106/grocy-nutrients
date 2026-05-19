from app.services.consumption import check_range_availability
from app.tasks import celery
from app.tasks._availability_check import TTL_24H, run_availability_check_job

RANGE_CHECK_TTL = TTL_24H  # re-exported for endpoint compatibility


def redis_key(user_id: int, household_id: int) -> str:
    return f"range_check:{user_id}:{household_id}"


@celery.task(
    name="app.tasks.range_check.range_check_task",
    bind=True,
)
def range_check_task(self, user_id: int, household_id: int, start_date: str, end_date: str):
    """Background task: check product availability for a date range."""
    run_availability_check_job(
        self,
        redis_key(user_id, household_id),
        runner=lambda db, api: check_range_availability(
            db,
            api,
            household_id=household_id,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
        ),
        user_id=user_id,
        household_id=household_id,
        progress_step=f"Checking availability for {start_date} — {end_date}...",
        extra_state={"start_date": start_date, "end_date": end_date},
    )
