from sqlmodel import col, select

from app.db.session import SessionLocal
from app.models.household import HouseholdUser
from app.services.grocy_api import GrocyConfigError, GrocyError, build_grocy_api
from app.services.recipe import RecipeCalculationError, sync_all_recipes_from_grocy
from app.tasks import celery


@celery.task(name="app.tasks.sync_recipes.sync_all_recipes")
def sync_all_recipes() -> dict:
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
                col(HouseholdUser.grocy_api_key).isnot(None),
            )
        ).all()

        seen_households: set[int] = set()

        for hu in household_users:
            if hu.household_id in seen_households:
                continue
            seen_households.add(hu.household_id)

            try:
                grocy_api = build_grocy_api(db, hu.household_id, hu.user_id)
            except GrocyConfigError as cfg_err:
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "error",
                        "error": cfg_err.detail,
                    }
                )
                continue

            try:
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
            except (GrocyError, RecipeCalculationError) as run_err:
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "error",
                        "error": str(run_err),
                    }
                )
            except Exception as run_err:
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "error",
                        "error": str(run_err),
                    }
                )
    finally:
        db.close()

    return {"households_processed": len(results), "results": results}
