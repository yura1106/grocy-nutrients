import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

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


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(0)


def derive_expiry(
    best_before_date: date_type | None, due_type: int, today: date_type
) -> tuple[int | None, str]:
    """Recompute (days_until_expiry, expiry_status) from stored durable facts.

    due_type follows Grocy: 1 = best-before (past -> overdue), 2 = expiration (past -> expired).
    Computed at read time so neither value goes stale between syncs.
    """
    if best_before_date is None:
        return None, "due_soon"
    days = (best_before_date - today).days
    if days >= 0:
        return days, "due_soon"
    return days, "expired" if due_type == 2 else "overdue"


@dataclass
class _ProductMeta:
    name: str
    qu_id_stock: int
    due_type: int
    should_not_be_frozen: bool
    location_id: int | None


def _product_meta(stock_entry: dict) -> _ProductMeta | None:
    """Pull durable product facts from a /stock row's embedded product object."""
    product = stock_entry.get("product") or {}
    try:
        qu_id = int(product["qu_id_stock"])
        name = str(product["name"])
    except (KeyError, TypeError, ValueError):
        return None
    try:
        due_type = int(product.get("due_type", 1))
    except (TypeError, ValueError):
        due_type = 1
    return _ProductMeta(
        name=name,
        qu_id_stock=qu_id,
        due_type=due_type,
        should_not_be_frozen=bool(product.get("should_not_be_frozen", 0)),
        location_id=product.get("location_id"),
    )


def sync_stock_expiry(db: Session, grocy_api: GrocyAPI, household_id: int) -> dict:
    """Sync ALL in-stock entries for a household into the local cache.

    Fetches the in-stock product list (GET /stock), then each product's individual
    stock entries (GET /stock/products/{id}/entries). Stores one row per entry keyed
    by Grocy's stable stock_id, and reconciles via diff: upsert each fetched entry,
    then delete only local rows whose stock_id is gone from Grocy. Never truncates.
    """
    raw_units = grocy_api.get_quantity_units()
    qu_units: dict[int, str] = {
        int(u["id"]): str(u.get("name", "")) for u in raw_units if u.get("id") is not None
    }

    stock = grocy_api.get("/stock")
    if not stock:
        # Empty/failed fetch is ambiguous; don't wipe a good snapshot on a transient
        # blip — keep previous rows and report the run as skipped.
        logger.warning(
            "sync_stock_expiry: /stock returned empty for household %s, keeping previous cache",
            household_id,
        )
        return {"synced": 0, "skipped": True}

    meta_by_product: dict[int, _ProductMeta] = {}
    for stock_row in stock:
        try:
            product_id = int(stock_row["product_id"])
        except (KeyError, TypeError, ValueError):
            continue
        meta = _product_meta(stock_row)
        if meta is not None:
            meta_by_product[product_id] = meta

    now = datetime.now(UTC)
    existing = db.exec(
        select(GrocyStockExpiry).where(GrocyStockExpiry.household_id == household_id)
    ).all()
    by_stock_id: dict[str, GrocyStockExpiry] = {row.grocy_stock_id: row for row in existing}

    seen: set[str] = set()
    synced = 0
    for product_id, meta in meta_by_product.items():
        entries = grocy_api.get(f"/stock/products/{product_id}/entries") or []
        for entry in entries:
            stock_id = entry.get("stock_id")
            if not stock_id:
                logger.warning(
                    "sync_stock_expiry: entry missing stock_id for product %s (household %s)",
                    product_id,
                    household_id,
                )
                continue
            stock_id = str(stock_id)
            seen.add(stock_id)

            row = by_stock_id.get(stock_id)
            if row is None:
                row = GrocyStockExpiry(household_id=household_id, grocy_stock_id=stock_id)
                db.add(row)

            row.grocy_product_id = product_id
            row.product_name = meta.name
            row.amount = _to_decimal(entry.get("amount", 0))
            row.qu_id_stock = meta.qu_id_stock
            row.quantity_unit_name = qu_units.get(meta.qu_id_stock, str(meta.qu_id_stock))
            row.best_before_date = _parse_date(entry.get("best_before_date"))
            row.purchased_date = _parse_date(entry.get("purchased_date"))
            row.opened = bool(entry.get("open", 0))
            row.due_type = meta.due_type
            row.location_id = (
                entry.get("location_id")
                if entry.get("location_id") is not None
                else meta.location_id
            )
            row.should_not_be_frozen = meta.should_not_be_frozen
            row.synced_at = now
            synced += 1

    for stock_id, row in by_stock_id.items():
        if stock_id not in seen:
            db.delete(row)

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
    """Expiring-stock entries with status/days recomputed against today (never stale)."""
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


@dataclass
class AggregatedStockItem:
    """All entries of one product collapsed: total amount + nearest best-before."""

    product_name: str
    amount: Decimal
    quantity_unit_name: str
    best_before_date: date_type | None
    days_until_expiry: int | None
    expiry_status: str
    should_not_be_frozen: bool
    synced_at: datetime


def query_all_stock(
    db: Session,
    household_id: int,
    today: date_type | None = None,
) -> list[AggregatedStockItem]:
    """All in-stock products, one line per product (amounts summed across entries,
    nearest best-before kept). Status/days recomputed against today."""
    today = today or datetime.now(UTC).date()

    rows = db.exec(
        select(GrocyStockExpiry).where(GrocyStockExpiry.household_id == household_id)
    ).all()

    by_product: dict[int, dict] = {}
    for row in rows:
        agg = by_product.get(row.grocy_product_id)
        if agg is None:
            by_product[row.grocy_product_id] = {
                "product_name": row.product_name,
                "amount": row.amount,
                "quantity_unit_name": row.quantity_unit_name,
                "best_before_date": row.best_before_date,
                "due_type": row.due_type,
                "should_not_be_frozen": row.should_not_be_frozen,
                "synced_at": row.synced_at,
            }
            continue
        agg["amount"] += row.amount
        # Keep the nearest (earliest) best-before across this product's entries.
        if row.best_before_date is not None and (
            agg["best_before_date"] is None or row.best_before_date < agg["best_before_date"]
        ):
            agg["best_before_date"] = row.best_before_date
            agg["due_type"] = row.due_type
        agg["synced_at"] = max(agg["synced_at"], row.synced_at)

    items: list[AggregatedStockItem] = []
    for agg in by_product.values():
        days, status = derive_expiry(agg["best_before_date"], agg["due_type"], today)
        items.append(
            AggregatedStockItem(
                product_name=agg["product_name"],
                amount=agg["amount"],
                quantity_unit_name=agg["quantity_unit_name"],
                best_before_date=agg["best_before_date"],
                days_until_expiry=days,
                expiry_status=status,
                should_not_be_frozen=agg["should_not_be_frozen"],
                synced_at=agg["synced_at"],
            )
        )

    # Most urgent first, then by name; no best-before (days None) sorts last.
    items.sort(
        key=lambda i: (
            i.days_until_expiry is None,
            i.days_until_expiry or 0,
            i.product_name.lower(),
        )
    )
    return items
