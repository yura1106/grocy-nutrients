"""Tests for the grocy stock-expiry sync + read-time recompute service."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app.models.household import Household
from app.models.stock_expiry import GrocyStockExpiry
from app.services.grocy_api import GrocyAPI
from app.services.stock_expiry import (
    derive_expiry,
    query_expiring_stock,
    sync_stock_expiry,
)


@pytest.fixture()
def household(db: Session) -> Household:
    h = Household(name="Home", grocy_url="http://grocy.local", created_at=datetime.now(UTC))
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def _volatile_entry(
    product_id: int,
    *,
    name: str,
    best_before: str | None,
    due_type: int = 1,
    amount: str = "2",
    qu_id: int = 1,
    location_id: int | None = 3,
    not_frozen: int = 0,
) -> dict:
    return {
        "product_id": product_id,
        "amount_aggregated": amount,
        "best_before_date": best_before,
        "product": {
            "name": name,
            "qu_id_stock": qu_id,
            "due_type": due_type,
            "location_id": location_id,
            "should_not_be_frozen": not_frozen,
        },
    }


def _mock_grocy(volatile: dict, units: list[dict] | None = None) -> MagicMock:
    api = MagicMock(spec=GrocyAPI)
    api.get_quantity_units.return_value = units or [{"id": 1, "name": "Piece"}]
    api.get.return_value = volatile
    return api


# --------------------------------------------------------------------------- #
# derive_expiry — pure logic
# --------------------------------------------------------------------------- #


class TestDeriveExpiry:
    today = date(2026, 6, 21)

    def test_future_date_is_due_soon(self):
        assert derive_expiry(date(2026, 6, 25), due_type=1, today=self.today) == (4, "due_soon")

    def test_today_is_due_soon_zero_days(self):
        assert derive_expiry(self.today, due_type=2, today=self.today) == (0, "due_soon")

    def test_past_best_before_type1_is_overdue(self):
        assert derive_expiry(date(2026, 6, 18), due_type=1, today=self.today) == (-3, "overdue")

    def test_past_best_before_type2_is_expired(self):
        assert derive_expiry(date(2026, 6, 18), due_type=2, today=self.today) == (-3, "expired")

    def test_none_date_is_due_soon_with_null_days(self):
        assert derive_expiry(None, due_type=1, today=self.today) == (None, "due_soon")


# --------------------------------------------------------------------------- #
# sync_stock_expiry
# --------------------------------------------------------------------------- #


class TestSyncStockExpiry:
    def test_writes_one_row_per_product_with_due_type(self, db, household):
        volatile = {
            "due_products": [_volatile_entry(1, name="Milk", best_before="2026-06-25", due_type=1)],
            "overdue_products": [],
            "expired_products": [
                _volatile_entry(2, name="Yogurt", best_before="2026-06-18", due_type=2)
            ],
        }
        result = sync_stock_expiry(db, _mock_grocy(volatile), household.id)
        db.commit()

        assert result == {"synced": 2}
        rows = {r.grocy_product_id: r for r in db.exec(select(GrocyStockExpiry)).all()}
        assert rows[1].due_type == 1
        assert rows[1].best_before_date == date(2026, 6, 25)
        assert rows[1].quantity_unit_name == "Piece"
        assert rows[1].amount == Decimal("2")
        assert rows[2].due_type == 2

    def test_dedup_across_buckets_keeps_single_row(self, db, household):
        # Same product surfaced in two buckets must not violate the unique constraint.
        entry = _volatile_entry(1, name="Milk", best_before="2026-06-20", due_type=1)
        volatile = {
            "due_products": [entry],
            "overdue_products": [entry],
            "expired_products": [],
        }
        result = sync_stock_expiry(db, _mock_grocy(volatile), household.id)
        db.commit()

        assert result == {"synced": 1}
        assert len(db.exec(select(GrocyStockExpiry)).all()) == 1

    def test_resync_replaces_rows_without_unique_violation(self, db, household):
        # Regression: delete-then-insert must flush deletes first, else the second
        # sync trips uq_grocy_stock_expiry_household_product for still-expiring products.
        volatile = {
            "due_products": [_volatile_entry(1, name="Milk", best_before="2026-06-25")],
            "overdue_products": [],
            "expired_products": [],
        }
        api = _mock_grocy(volatile)
        sync_stock_expiry(db, api, household.id)
        db.commit()

        # Second run with the same product still present.
        sync_stock_expiry(db, api, household.id)
        db.commit()

        rows = db.exec(select(GrocyStockExpiry)).all()
        assert len(rows) == 1
        assert rows[0].grocy_product_id == 1

    def test_empty_fetch_skips_without_wiping_cache(self, db, household):
        # Seed a good snapshot.
        first = {
            "due_products": [_volatile_entry(1, name="Milk", best_before="2026-06-25")],
            "overdue_products": [],
            "expired_products": [],
        }
        sync_stock_expiry(db, _mock_grocy(first), household.id)
        db.commit()

        # Transient empty fetch must NOT delete the previous data.
        empty = {"due_products": [], "overdue_products": [], "expired_products": []}
        result = sync_stock_expiry(db, _mock_grocy(empty), household.id)
        db.commit()

        assert result == {"synced": 0, "skipped": True}
        assert len(db.exec(select(GrocyStockExpiry)).all()) == 1

    def test_malformed_entry_is_skipped(self, db, household):
        volatile = {
            "due_products": [
                {"product_id": 1, "best_before_date": "2026-06-25"},  # no nested product
                _volatile_entry(2, name="Bread", best_before="2026-06-24"),
            ],
            "overdue_products": [],
            "expired_products": [],
        }
        result = sync_stock_expiry(db, _mock_grocy(volatile), household.id)
        db.commit()

        assert result == {"synced": 1}
        rows = db.exec(select(GrocyStockExpiry)).all()
        assert [r.grocy_product_id for r in rows] == [2]

    def test_missing_due_type_defaults_to_one(self, db, household):
        entry = _volatile_entry(1, name="Milk", best_before="2026-06-25")
        del entry["product"]["due_type"]
        volatile = {"due_products": [entry], "overdue_products": [], "expired_products": []}
        sync_stock_expiry(db, _mock_grocy(volatile), household.id)
        db.commit()

        assert db.exec(select(GrocyStockExpiry)).one().due_type == 1


# --------------------------------------------------------------------------- #
# query_expiring_stock — read-time recompute
# --------------------------------------------------------------------------- #


def _seed_row(db, household, *, product_id, name, best_before, due_type=1):
    db.add(
        GrocyStockExpiry(
            household_id=household.id,
            grocy_product_id=product_id,
            product_name=name,
            amount=Decimal("1"),
            qu_id_stock=1,
            quantity_unit_name="Piece",
            best_before_date=best_before,
            due_type=due_type,
            synced_at=datetime.now(UTC),
        )
    )
    db.commit()


class TestQueryExpiringStock:
    def test_recomputes_status_against_today_not_sync_time(self, db, household):
        # Row synced when it had a future best-before; querying after it passes must
        # report overdue, not the stale due_soon — this is the staleness fix.
        _seed_row(db, household, product_id=1, name="Milk", best_before=date(2026, 6, 20), due_type=1)

        items = query_expiring_stock(db, household.id, today=date(2026, 6, 22))

        assert len(items) == 1
        assert items[0].expiry_status == "overdue"
        assert items[0].days_until_expiry == -2

    def test_sorted_by_urgency_nulls_last(self, db, household):
        _seed_row(db, household, product_id=1, name="A", best_before=date(2026, 6, 25))
        _seed_row(db, household, product_id=2, name="B", best_before=date(2026, 6, 18), due_type=2)
        _seed_row(db, household, product_id=3, name="C", best_before=None)

        items = query_expiring_stock(db, household.id, today=date(2026, 6, 21))

        # Most urgent (most negative days) first; null best-before sorts last.
        assert [i.row.product_name for i in items] == ["B", "A", "C"]
        assert items[-1].days_until_expiry is None

    def test_include_flags_filter_recomputed_status(self, db, household):
        _seed_row(db, household, product_id=1, name="Soon", best_before=date(2026, 6, 25))
        _seed_row(db, household, product_id=2, name="Overdue", best_before=date(2026, 6, 18), due_type=1)
        _seed_row(db, household, product_id=3, name="Expired", best_before=date(2026, 6, 18), due_type=2)
        today = date(2026, 6, 21)

        only_soon = query_expiring_stock(
            db, household.id, include_overdue=False, include_expired=False, today=today
        )
        assert [i.row.product_name for i in only_soon] == ["Soon"]

        no_expired = query_expiring_stock(db, household.id, include_expired=False, today=today)
        assert {i.row.product_name for i in no_expired} == {"Soon", "Overdue"}

    def test_scoped_to_household(self, db, household):
        other = Household(name="Other", grocy_url="http://x", created_at=datetime.now(UTC))
        db.add(other)
        db.commit()
        db.refresh(other)
        _seed_row(db, household, product_id=1, name="Mine", best_before=date(2026, 6, 25))
        _seed_row(db, other, product_id=1, name="Theirs", best_before=date(2026, 6, 25))

        items = query_expiring_stock(db, household.id, today=date(2026, 6, 21))
        assert [i.row.product_name for i in items] == ["Mine"]
