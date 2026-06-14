"""upsert_product invalidates the meal-plan units cache on the existing-product
branch only, so a Grocy unit-conversion change surfaces on the next read instead
of being masked by the 24h cache.

Uses a monkeypatch spy rather than asserting the Redis key is gone: fakeredis is
not a dependency and the test harness swallows Redis connection errors, so a
real-key assertion would pass for the wrong reason when Redis is unavailable.
"""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.product import Product
from app.schemas.product import GrocyProductResponse
from app.services.product import upsert_product

HH_ID = 7101


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="Units Cache HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


def _grocy_product(grocy_id: int, *, name: str = "Сметана") -> GrocyProductResponse:
    return GrocyProductResponse(
        id=grocy_id,
        name=name,
        product_group_id=1,
        active=1,
        qu_id_stock=99,  # "банка"-style non-standard stock unit
    )


def test_upsert_existing_product_invalidates_units_cache(
    db: Session, hh: Household, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Updating an existing product evicts its cached units payload."""
    grocy_id = 555
    existing = Product(
        grocy_id=grocy_id,
        name="Сметана",
        active=True,
        product_group_id=1,
        qu_id_stock=99,
        household_id=HH_ID,
        created_at=datetime.now(UTC),
    )
    db.add(existing)
    db.commit()

    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.services.product.invalidate_units_cache",
        lambda household_id, grocy_product_id: calls.append((household_id, grocy_product_id)),
    )

    upsert_product(db, _grocy_product(grocy_id, name="Сметана 20%"), household_id=HH_ID)

    assert calls == [(HH_ID, grocy_id)]


def test_upsert_new_product_does_not_invalidate_units_cache(
    db: Session, hh: Household, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A brand-new product has no cache entry, so no eviction is attempted."""
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.services.product.invalidate_units_cache",
        lambda household_id, grocy_product_id: calls.append((household_id, grocy_product_id)),
    )

    upsert_product(db, _grocy_product(999), household_id=HH_ID)

    assert calls == []
