from sqlmodel import select

from app.core.encryption import decrypt_api_key
from app.db.session import SessionLocal
from app.models.household import Household, HouseholdUser
from app.models.user import User
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.recipe import RecipeCalculationError, sync_all_recipes_from_grocy
from app.tasks import celery


@celery.task(name="app.tasks.sync_recipes.sync_all_recipes")
def sync_all_recipes():
    """
    Sync recipes from Grocy for every household that has credentials configured.
    Deduplicates by household_id — syncs once per household using first available key.
    Runs daily at 04:00 via celery beat.
    """
    db = SessionLocal()
    results = []

    try:
        household_users = db.exec(
            select(HouseholdUser).where(
                HouseholdUser.grocy_api_key.isnot(None),  # type: ignore[union-attr]
            )
        ).all()

        seen_households: set[int] = set()

        for hu in household_users:
            if hu.household_id in seen_households:
                continue

            household = db.exec(select(Household).where(Household.id == hu.household_id)).first()
            if not household or not household.grocy_url:
                continue

            seen_households.add(hu.household_id)

            try:
                user = db.exec(select(User).where(User.id == hu.user_id)).first()
                if not user:
                    continue
                plaintext_key = decrypt_api_key(hu.grocy_api_key, user.hashed_password)
                if not plaintext_key:
                    continue
                grocy_api = GrocyAPI(key=plaintext_key, url=household.grocy_url)
                result = sync_all_recipes_from_grocy(
                    db=db, grocy_api=grocy_api, household_id=hu.household_id
                )
                db.commit()
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "success",
                        "processed": result.processed,
                        "synced": result.synced,
                        "errors": result.errors,
                    }
                )
            except (GrocyError, RecipeCalculationError) as exc:
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "error",
                        "error": str(exc),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "error",
                        "error": str(exc),
                    }
                )
    finally:
        db.close()

    return {"households_processed": len(results), "results": results}
