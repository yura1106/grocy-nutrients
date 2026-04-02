from celery.exceptions import SoftTimeLimitExceeded
from sqlmodel import select

from app.core.encryption import decrypt_api_key
from app.db.session import SessionLocal
from app.models.household import Household, HouseholdUser
from app.models.user import User
from app.services.consumption import ConsumptionError, execute_consumption
from app.services.grocy_api import GrocyAPI
from app.tasks import celery


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
        hu = db.exec(
            select(HouseholdUser).where(
                HouseholdUser.user_id == user_id,
                HouseholdUser.household_id == household_id,
            )
        ).first()
        if not hu or not hu.grocy_api_key:
            return {
                "status": "error",
                "error": "Grocy API key not configured for this household.",
            }

        user = db.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return {"status": "error", "error": "User not found."}

        plaintext_key = decrypt_api_key(hu.grocy_api_key, user.hashed_password)
        if not plaintext_key:
            return {
                "status": "error",
                "error": "Failed to decrypt Grocy API key. Please re-save your key.",
            }

        household = db.exec(select(Household).where(Household.id == household_id)).first()
        if not household or not household.grocy_url:
            return {
                "status": "error",
                "error": "Grocy URL not configured for this household.",
            }

        grocy_api = GrocyAPI(key=plaintext_key, url=household.grocy_url)

        self.update_state(state="PROGRESS", meta={"step": "Connecting to Grocy..."})

        result = execute_consumption(
            db, grocy_api, date, household_id=household_id, user_id=user_id
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
