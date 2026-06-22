from sqlmodel import col, select

from app.db.session import SessionLocal
from app.models.household import HouseholdUser
from app.services.grocy_api import GrocyConfigError, GrocyError, build_grocy_api
from app.services.stock_expiry import sync_stock_expiry
from app.tasks import celery


@celery.task(name="app.tasks.sync_stock_expiry.sync_all_stock_expiry")
def sync_all_stock_expiry() -> dict:
    """
    Sync ALL in-stock entries from Grocy for every household with credentials.
    Deduplicates by household_id — syncs once per household using first available key.
    Runs every 4h at :20 via celery beat.
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
                result = sync_stock_expiry(
                    db=db, grocy_api=grocy_api, household_id=hu.household_id
                )
                db.commit()
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "skipped" if result.get("skipped") else "success",
                        "synced": result["synced"],
                    }
                )
            except GrocyError as run_err:
                db.rollback()
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "error",
                        "error": str(run_err),
                    }
                )
            except Exception as run_err:
                db.rollback()
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
