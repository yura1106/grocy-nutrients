from datetime import UTC, datetime

from sqlmodel import select

from app.db.session import SessionLocal
from app.models.household import HouseholdUser
from app.services.grocy_api import GrocyConfigError, GrocyError, build_grocy_api
from app.services.product import ProductSyncError, sync_grocy_products
from app.tasks import celery


@celery.task(name="app.tasks.sync_products.sync_all_products")
def sync_all_products() -> dict:
    """
    Sync products from Grocy for every household that has credentials configured.
    Iterates over distinct households (via HouseholdUser records that have a grocy_api_key)
    and uses the first available key per household to sync.
    Runs daily at 04:00 via celery beat.
    """
    db = SessionLocal()
    results = []

    try:
        # Get all household_users that have a grocy_api_key configured
        household_users = db.exec(
            select(HouseholdUser).where(
                HouseholdUser.grocy_api_key.isnot(None),  # type: ignore[union-attr]
            )
        ).all()

        # Deduplicate by household_id — sync once per household using first available key
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
                result = sync_grocy_products(
                    db, grocy_api, offset=0, limit=10000, household_id=hu.household_id
                )
                hu.last_products_sync_at = datetime.now(UTC)
                db.add(hu)
                db.commit()
                results.append(
                    {
                        "household_id": hu.household_id,
                        "status": "success",
                        "processed": result.processed,
                        "updated": result.updated,
                        "new_history_records": result.new_history_records,
                    }
                )
            except (GrocyError, ProductSyncError) as exc:
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
