"""Tests for the grocy per-entry stock sync + read-time recompute service."""

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
    query_all_stock,
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


def _stock_row(
    product_id: int,
    *,
    name: str,
    due_type: int = 1,
    qu_id: int = 1,
    location_id: int | None = 3,
    not_frozen: int = 0,
) -> dict:
    """A row of GET /stock with its embedded product object."""
    return {
        "product_id": product_id,
        "product": {
            "name": name,
            "qu_id_stock": qu_id,
            "due_type": due_type,
            "location_id": location_id,
            "should_not_be_frozen": not_frozen,
        },
    }


def _entry(
    stock_id: str,
    *,
    amount: str = "2",
    best_before: str | None = None,
    purchased: str | None = None,
    opened: int = 0,
    location_id: int | None = None,
) -> dict:
    """A row of GET /stock/products/{id}/entries."""
    return {
        "stock_id": stock_id,
        "amount": amount,
        "best_before_date": best_before,
        "purchased_date": purchased,
        "open": opened,
        "location_id": location_id,
    }


def _mock_grocy(
    stock: list[dict],
    entries_by_product: dict[int, list[dict]],
    units: list[dict] | None = None,
) -> MagicMock:
    api = MagicMock(spec=GrocyAPI)
    api.get_quantity_units.return_value = units or [{"id": 1, "name": "Piece"}]

    def _get(path: str, params=None):
        if path == "/stock":
            return stock
        if path.startswith("/stock/products/") and path.endswith("/entries"):
            pid = int(path.split("/")[3])
            return entries_by_product.get(pid, [])
        raise AssertionError(f"unexpected GET {path}")

    api.get.side_effect = _get
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
# sync_stock_expiry — per-entry diff
# --------------------------------------------------------------------------- #


class TestSyncStockExpiry:
    def test_writes_one_row_per_entry(self, db, household):
        stock = [
            _stock_row(1, name="Milk", due_type=1),
            _stock_row(2, name="Yogurt", due_type=2),
        ]
        entries = {
            1: [
                _entry("s1", amount="1", best_before="2026-06-25"),
                _entry("s2", amount="2", best_before="2026-07-10"),
            ],
            2: [_entry("s3", amount="3", best_before="2026-06-18")],
        }
        result = sync_stock_expiry(db, _mock_grocy(stock, entries), household.id)
        db.commit()

        assert result == {"synced": 3}
        rows = {r.grocy_stock_id: r for r in db.exec(select(GrocyStockExpiry)).all()}
        assert set(rows) == {"s1", "s2", "s3"}
        assert rows["s1"].grocy_product_id == 1
        assert rows["s1"].due_type == 1
        assert rows["s1"].best_before_date == date(2026, 6, 25)
        assert rows["s1"].quantity_unit_name == "Piece"
        assert rows["s2"].amount == Decimal("2")
        assert rows["s3"].due_type == 2

    def test_multiple_entries_per_product_retained(self, db, household):
        stock = [_stock_row(1, name="Milk")]
        entries = {
            1: [
                _entry("s1", best_before="2026-06-25"),
                _entry("s2", best_before="2026-07-01"),
                _entry("s3", best_before="2026-07-15"),
            ]
        }
        sync_stock_expiry(db, _mock_grocy(stock, entries), household.id)
        db.commit()

        rows = db.exec(select(GrocyStockExpiry)).all()
        assert len(rows) == 3
        assert all(r.grocy_product_id == 1 for r in rows)

    def test_resync_upserts_in_place_and_deletes_missing(self, db, household):
        stock = [_stock_row(1, name="Milk")]
        first_entries = {1: [_entry("s1", amount="1"), _entry("s2", amount="2")]}
        api = _mock_grocy(stock, first_entries)
        sync_stock_expiry(db, api, household.id)
        db.commit()

        ids_before = {r.grocy_stock_id: r.id for r in db.exec(select(GrocyStockExpiry)).all()}

        # s1 updated, s2 gone, s3 new.
        second_entries = {1: [_entry("s1", amount="5"), _entry("s3", amount="9")]}
        sync_stock_expiry(db, _mock_grocy(stock, second_entries), household.id)
        db.commit()

        rows = {r.grocy_stock_id: r for r in db.exec(select(GrocyStockExpiry)).all()}
        assert set(rows) == {"s1", "s3"}
        # s1 was updated in place (same PK), not deleted/recreated.
        assert rows["s1"].id == ids_before["s1"]
        assert rows["s1"].amount == Decimal("5")
        assert rows["s3"].amount == Decimal("9")

    def test_empty_stock_skips_without_wiping_cache(self, db, household):
        stock = [_stock_row(1, name="Milk")]
        entries = {1: [_entry("s1", best_before="2026-06-25")]}
        sync_stock_expiry(db, _mock_grocy(stock, entries), household.id)
        db.commit()

        result = sync_stock_expiry(db, _mock_grocy([], {}), household.id)
        db.commit()

        assert result == {"synced": 0, "skipped": True}
        assert len(db.exec(select(GrocyStockExpiry)).all()) == 1

    def test_entry_missing_stock_id_is_skipped(self, db, household):
        stock = [_stock_row(1, name="Milk")]
        entries = {1: [{"amount": "1", "best_before_date": "2026-06-25"}, _entry("s2", amount="2")]}
        result = sync_stock_expiry(db, _mock_grocy(stock, entries), household.id)
        db.commit()

        assert result == {"synced": 1}
        assert [r.grocy_stock_id for r in db.exec(select(GrocyStockExpiry)).all()] == ["s2"]

    def test_product_missing_meta_is_skipped(self, db, household):
        stock = [{"product_id": 1}, _stock_row(2, name="Bread")]  # row 1 has no product object
        entries = {1: [_entry("s1")], 2: [_entry("s2", best_before="2026-06-24")]}
        result = sync_stock_expiry(db, _mock_grocy(stock, entries), household.id)
        db.commit()

        assert result == {"synced": 1}
        assert [r.grocy_product_id for r in db.exec(select(GrocyStockExpiry)).all()] == [2]

    def test_entry_fields_mapped(self, db, household):
        stock = [_stock_row(1, name="Milk")]
        entries = {1: [_entry("s1", best_before="2026-06-25", purchased="2026-06-01", opened=1)]}
        sync_stock_expiry(db, _mock_grocy(stock, entries), household.id)
        db.commit()

        row = db.exec(select(GrocyStockExpiry)).one()
        assert row.purchased_date == date(2026, 6, 1)
        assert row.opened is True


# --------------------------------------------------------------------------- #
# read-time helpers
# --------------------------------------------------------------------------- #


def _seed_entry(db, household, *, stock_id, product_id, name, best_before, amount="1", due_type=1):
    db.add(
        GrocyStockExpiry(
            household_id=household.id,
            grocy_stock_id=stock_id,
            grocy_product_id=product_id,
            product_name=name,
            amount=Decimal(amount),
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
        _seed_entry(db, household, stock_id="s1", product_id=1, name="Milk", best_before=date(2026, 6, 20))

        items = query_expiring_stock(db, household.id, today=date(2026, 6, 22))

        assert len(items) == 1
        assert items[0].expiry_status == "overdue"
        assert items[0].days_until_expiry == -2

    def test_sorted_by_urgency_nulls_last(self, db, household):
        _seed_entry(db, household, stock_id="a", product_id=1, name="A", best_before=date(2026, 6, 25))
        _seed_entry(db, household, stock_id="b", product_id=2, name="B", best_before=date(2026, 6, 18), due_type=2)
        _seed_entry(db, household, stock_id="c", product_id=3, name="C", best_before=None)

        items = query_expiring_stock(db, household.id, today=date(2026, 6, 21))

        assert [i.row.product_name for i in items] == ["B", "A", "C"]
        assert items[-1].days_until_expiry is None

    def test_include_flags_filter_recomputed_status(self, db, household):
        _seed_entry(db, household, stock_id="s", product_id=1, name="Soon", best_before=date(2026, 6, 25))
        _seed_entry(db, household, stock_id="o", product_id=2, name="Overdue", best_before=date(2026, 6, 18), due_type=1)
        _seed_entry(db, household, stock_id="e", product_id=3, name="Expired", best_before=date(2026, 6, 18), due_type=2)
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
        _seed_entry(db, household, stock_id="m", product_id=1, name="Mine", best_before=date(2026, 6, 25))
        _seed_entry(db, other, stock_id="t", product_id=1, name="Theirs", best_before=date(2026, 6, 25))

        items = query_expiring_stock(db, household.id, today=date(2026, 6, 21))
        assert [i.row.product_name for i in items] == ["Mine"]


class TestQueryAllStock:
    def test_aggregates_entries_per_product(self, db, household):
        # Two entries of the same product collapse to one line with summed amount
        # and the nearest best-before.
        _seed_entry(db, household, stock_id="s1", product_id=1, name="Milk", best_before=date(2026, 7, 10), amount="2")
        _seed_entry(db, household, stock_id="s2", product_id=1, name="Milk", best_before=date(2026, 6, 25), amount="3")

        items = query_all_stock(db, household.id, today=date(2026, 6, 21))

        assert len(items) == 1
        assert items[0].amount == Decimal("5")
        assert items[0].best_before_date == date(2026, 6, 25)
        assert items[0].days_until_expiry == 4

    def test_includes_non_expiring_products(self, db, household):
        # A product with no best-before (never expires) still appears.
        _seed_entry(db, household, stock_id="s1", product_id=1, name="Salt", best_before=None, amount="1")
        _seed_entry(db, household, stock_id="s2", product_id=2, name="Milk", best_before=date(2026, 6, 25), amount="1")

        items = query_all_stock(db, household.id, today=date(2026, 6, 21))
        names = {i.product_name for i in items}
        assert names == {"Salt", "Milk"}

    def test_sorted_by_urgency_then_name_nulls_last(self, db, household):
        _seed_entry(db, household, stock_id="a", product_id=1, name="Apple", best_before=date(2026, 6, 25))
        _seed_entry(db, household, stock_id="b", product_id=2, name="Bread", best_before=date(2026, 6, 22))
        _seed_entry(db, household, stock_id="c", product_id=3, name="Salt", best_before=None)

        items = query_all_stock(db, household.id, today=date(2026, 6, 21))
        assert [i.product_name for i in items] == ["Bread", "Apple", "Salt"]
        assert items[-1].days_until_expiry is None

    def test_scoped_to_household(self, db, household):
        other = Household(name="Other", grocy_url="http://x", created_at=datetime.now(UTC))
        db.add(other)
        db.commit()
        db.refresh(other)
        _seed_entry(db, household, stock_id="m", product_id=1, name="Mine", best_before=date(2026, 6, 25))
        _seed_entry(db, other, stock_id="t", product_id=1, name="Theirs", best_before=date(2026, 6, 25))

        items = query_all_stock(db, household.id, today=date(2026, 6, 21))
        assert [i.product_name for i in items] == ["Mine"]
