import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal

from sqlmodel import Session, select

from app.models.stock_expiry import GrocyStockExpiry
from app.services.grocy_api import GrocyAPI

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date_type | None:
    if not value:
        return None
    try:
        return date_type.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def derive_expiry(
    best_before_date: date_type | None, due_type: int, today: date_type
) -> tuple[int | None, str]:
    """Recompute (days_until_expiry, expiry_status) from stored durable facts.

    due_type follows Grocy: 1 = best-before (past -> overdue), 2 = expiration (past -> expired).
    Computed at read time so neither value goes stale between daily syncs.
    """
    if best_before_date is None:
        return None, "due_soon"
    days = (best_before_date - today).days
    if days >= 0:
        return days, "due_soon"
    return days, "expired" if due_type == 2 else "overdue"


def sync_stock_expiry(db: Session, grocy_api: GrocyAPI, household_id: int) -> dict:
    raw_units = grocy_api.get_quantity_units()
    qu_units: dict[int, str] = {
        int(u["id"]): str(u.get("name", "")) for u in raw_units if u.get("id") is not None
    }

    volatile = grocy_api.get("/stock/volatile", {"due_soon_days": 7})

    # A product can appear in several buckets; the unique (household, product) constraint
    # allows one row. Status is no longer stored (it's derived at read time from
    # best_before_date + due_type), so any bucket's entry for a product is equivalent.
    by_product: dict[int, dict] = {}
    for bucket in ("due_products", "overdue_products", "expired_products"):
        for product_data in volatile.get(bucket, []):
            try:
                product_id = int(product_data["product_id"])
            except (KeyError, TypeError, ValueError):
                logger.warning("sync_stock_expiry: volatile entry missing product_id, skipping (household %s)", household_id)
                continue
            by_product[product_id] = product_data

    if not by_product:
        # Don't wipe a good snapshot on a transient empty/failed fetch; leave the
        # previous data in place and report the run as skipped.
        logger.warning("sync_stock_expiry: /stock/volatile returned empty for household %s, keeping previous cache", household_id)
        return {"synced": 0, "skipped": True}

    existing = db.exec(select(GrocyStockExpiry).where(GrocyStockExpiry.household_id == household_id)).all()
    for row in existing:
        db.delete(row)
    # Flush the deletes before inserting; otherwise the unit-of-work emits the new
    # INSERTs before the DELETEs and the (household, product) unique constraint trips
    # on every re-run for products that are still expiring.
    db.flush()

    now = datetime.now(UTC)
    synced = 0
    for product_id, product_data in by_product.items():
        try:
            product = product_data["product"]
            qu_id = int(product["qu_id_stock"])
            product_name = product["name"]
        except (KeyError, TypeError, ValueError):
            logger.warning("sync_stock_expiry: malformed entry for product %s, skipping (household %s)", product_id, household_id)
            continue
        best_before = _parse_date(product_data.get("best_before_date"))
        try:
            due_type = int(product.get("due_type", 1))
        except (TypeError, ValueError):
            due_type = 1
        db.add(GrocyStockExpiry(
            household_id=household_id,
            grocy_product_id=product_id,
            product_name=product_name,
            amount=Decimal(str(product_data.get("amount_aggregated", 0))),
            qu_id_stock=qu_id,
            quantity_unit_name=qu_units.get(qu_id, str(qu_id)),
            best_before_date=best_before,
            due_type=due_type,
            location_id=product.get("location_id"),
            should_not_be_frozen=bool(product.get("should_not_be_frozen", 0)),
            synced_at=now,
        ))
        synced += 1
    return {"synced": synced}


@dataclass
class ExpiringStockItem:
    """A cache row with expiry_status/days_until_expiry recomputed for `today`."""

    row: GrocyStockExpiry
    days_until_expiry: int | None
    expiry_status: str
    synced_at: datetime


def query_expiring_stock(
    db: Session,
    household_id: int,
    include_expired: bool = True,
    include_overdue: bool = True,
    today: date_type | None = None,
) -> list[ExpiringStockItem]:
    """Expiring-stock items with status/days recomputed against today (never stale)."""
    today = today or datetime.now(UTC).date()
    allowed = {"due_soon"}
    if include_overdue:
        allowed.add("overdue")
    if include_expired:
        allowed.add("expired")

    rows = db.exec(
        select(GrocyStockExpiry).where(GrocyStockExpiry.household_id == household_id)
    ).all()

    items: list[ExpiringStockItem] = []
    for row in rows:
        days, status = derive_expiry(row.best_before_date, row.due_type, today)
        if status not in allowed:
            continue
        items.append(
            ExpiringStockItem(
                row=row,
                days_until_expiry=days,
                expiry_status=status,
                synced_at=row.synced_at,
            )
        )

    # Most urgent first; rows without a best-before date (days is None) sort last.
    items.sort(key=lambda i: (i.days_until_expiry is None, i.days_until_expiry or 0))
    return items
