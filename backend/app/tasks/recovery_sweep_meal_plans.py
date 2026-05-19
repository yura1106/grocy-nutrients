"""Periodic sweep: rows stuck in 'syncing' for >10 minutes are marked failed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import update as sa_update
from sqlmodel import col

from app.db.session import SessionLocal
from app.models.meal_plan import MealPlan
from app.tasks import celery

STUCK_THRESHOLD = timedelta(minutes=10)


@celery.task(
    name="app.tasks.recovery_sweep_meal_plans.recovery_sweep_meal_plans_task",
    bind=True,
    soft_time_limit=120,
    time_limit=180,
)
def recovery_sweep_meal_plans_task(self) -> dict:
    cutoff = datetime.now(UTC) - STUCK_THRESHOLD
    db = SessionLocal()
    try:
        result = db.exec(  # type: ignore[call-overload]
            sa_update(MealPlan)
            .where(
                col(MealPlan.status) == "syncing",
                col(MealPlan.updated_at) < cutoff,
            )
            .values(
                status="failed",
                error_message="Task timed out or worker crashed before reconcile.",
            )
        )
        db.commit()
        rowcount = getattr(result, "rowcount", 0) or 0
        return {"swept": int(rowcount)}
    finally:
        db.close()
