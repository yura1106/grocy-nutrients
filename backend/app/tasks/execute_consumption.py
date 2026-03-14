from app.tasks import celery
from app.db.session import SessionLocal
from app.models.user import User
from app.services.grocy_api import GrocyAPI
from app.services.consumption import execute_consumption, ConsumptionError
from sqlmodel import select


@celery.task(
    name="app.tasks.execute_consumption.execute_consumption_task",
    bind=True,
)
def execute_consumption_task(self, user_id: int, date: str):
    """
    Background task: execute meal plan consumption for a given date.
    Reports progress via Celery's update_state.
    """
    db = SessionLocal()
    try:
        user = db.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return {"status": "error", "error": "User not found"}

        grocy_api = GrocyAPI(key=user.grocy_api_key, url=user.grocy_url)

        self.update_state(state="PROGRESS", meta={"step": "Connecting to Grocy..."})

        result = execute_consumption(db, grocy_api, date)

        return {"status": "success", "result": result}

    except (ConsumptionError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()
