import logging

from celery.exceptions import SoftTimeLimitExceeded

from app.db.session import SessionLocal
from app.services.consumption import ConsumptionError, execute_consumption
from app.services.grocy_api import GrocyConfigError, build_grocy_api
from app.services.stock_expiry import sync_stock_expiry
from app.tasks import celery

logger = logging.getLogger(__name__)


@celery.task(
    name="app.tasks.execute_consumption.execute_consumption_task",
    bind=True,
    soft_time_limit=300,
    time_limit=360,
)
def execute_consumption_task(self, user_id: int, household_id: int, date: str):
    """
    Background task: execute meal plan consumption for a given date.
    Uses Grocy credentials from the user's household membership.
    Reports progress via Celery's update_state.
    """
    db = SessionLocal()
    try:
        try:
            grocy_api = build_grocy_api(db, household_id, user_id)
        except GrocyConfigError as exc:
            return {"status": "error", "error": exc.detail}

        self.update_state(state="PROGRESS", meta={"step": "Connecting to Grocy..."})

        result = execute_consumption(
            db, grocy_api, date, household_id=household_id, user_id=user_id
        )

        # Consumption mutated Grocy stock; refresh the local cache so it reflects
        # post-consumption amounts immediately. A sync failure must never fail the
        # consumption that already succeeded.
        try:
            self.update_state(state="PROGRESS", meta={"step": "Refreshing stock..."})
            sync_stock_expiry(db=db, grocy_api=grocy_api, household_id=household_id)
            db.commit()
        except Exception as sync_err:
            db.rollback()
            logger.warning(
                "post-consume stock re-sync failed for household %s: %s",
                household_id,
                sync_err,
            )

        return {"status": "success", "result": result}

    except SoftTimeLimitExceeded:
        return {
            "status": "error",
            "error": "Task time limit reached. Partial results may have been saved — check consumption history for this date.",
        }
    except (ConsumptionError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()
