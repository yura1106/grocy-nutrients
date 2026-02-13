from app.tasks import celery
from app.db.session import SessionLocal
from app.models.user import User
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.product import sync_grocy_products, ProductSyncError
from sqlmodel import select


@celery.task(name="app.tasks.sync_products.sync_all_products")
def sync_all_products():
    """
    Sync products from Grocy for every user that has a grocy_api_key configured.
    Runs daily at 04:00 via celery beat.
    """
    db = SessionLocal()
    results = []

    try:
        users = db.exec(
            select(User).where(User.grocy_api_key.isnot(None))  # type: ignore[union-attr]
        ).all()

        for user in users:
            try:
                grocy_api = GrocyAPI(user.grocy_api_key)

                # Sync all products in one go (no chunking needed — no HTTP timeout)
                result = sync_grocy_products(db, grocy_api, offset=0, limit=10000)
                results.append({
                    "user_id": user.id,
                    "status": "success",
                    "processed": result.processed,
                    "updated": result.updated,
                    "new_history_records": result.new_history_records,
                })
            except (GrocyError, ProductSyncError) as exc:
                results.append({
                    "user_id": user.id,
                    "status": "error",
                    "error": str(exc),
                })
            except Exception as exc:
                results.append({
                    "user_id": user.id,
                    "status": "error",
                    "error": str(exc),
                })
    finally:
        db.close()

    return {"users_processed": len(results), "results": results}
