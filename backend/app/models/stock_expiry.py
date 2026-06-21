from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Numeric, UniqueConstraint
from sqlmodel import Column, Field, SQLModel


class GrocyStockExpiry(SQLModel, table=True):
    __tablename__ = "grocy_stock_expiry"
    __table_args__ = (
        UniqueConstraint(
            "household_id", "grocy_product_id",
            name="uq_grocy_stock_expiry_household_product",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="households.id")
    grocy_product_id: int
    product_name: str
    amount: Decimal = Field(sa_column=Column(Numeric(precision=12, scale=3), nullable=False))
    qu_id_stock: int
    quantity_unit_name: str
    best_before_date: date_type | None = None
    # Grocy product due_type: 1 = best-before (-> overdue when past), 2 = expiration (-> expired).
    # days_until_expiry and expiry_status are derived from best_before_date + due_type at read
    # time (see services.stock_expiry) so they never go stale between daily syncs.
    due_type: int = Field(default=1)
    location_id: int | None = None
    should_not_be_frozen: bool = Field(default=False)
    synced_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
