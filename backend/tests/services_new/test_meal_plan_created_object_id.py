"""Tests that the batch task and retry_line both honour Grocy's
`created_object_id` response field instead of relying on snapshot/tuple
reconciliation. The reconciliation block remains as a fallback for older
Grocy versions that return an empty/missing field.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.models.household import Household
from app.models.meal_plan import MealPlan
from app.models.user import User
from app.services.meal_plan import retry_line

HH_ID = 8001
USER_ID = 8101
DAY = date(2026, 5, 13)


@pytest.fixture()
def hh(db: Session) -> Household:
    household = Household(id=HH_ID, name="CreatedId HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@pytest.fixture()
def user(db: Session) -> User:
    u = User(
        id=USER_ID,
        email="createdid@example.com",
        username="createdid-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _failed_product_row() -> MealPlan:
    return MealPlan(
        household_id=HH_ID,
        user_id=USER_ID,
        type="product",
        day=DAY,
        section_id=1,
        product_grocy_id=546,
        product_amount=Decimal("22"),
        product_amount_stock=Decimal("0.063"),
        product_qu_id=82,
        status="failed",
        retry_count=3,
        error_message="prior transient blip",
        created_at=datetime.now(UTC),
    )


def test_retry_uses_created_object_id_directly(db: Session, hh: Household, user: User) -> None:
    """When Grocy's POST returns `{"created_object_id": <id>}`, retry_line must
    set grocy_meal_plan_id directly without falling back to snapshot/tuple
    matching. This also clears stale error_message and retry_count.
    """
    row = _failed_product_row()
    db.add(row)
    db.commit()
    db.refresh(row)

    grocy = MagicMock()
    grocy.create_meal_plan_entry.return_value = {"created_object_id": 4242}
    grocy.get_meal_plan.return_value = []

    with patch(
        "app.services.meal_plan.fetch_new_grocy_rows_window"
    ) as fetch_new_mock:
        updated = retry_line(
            db,
            household_id=HH_ID,
            line_id=row.id,
            user_id=USER_ID,
            grocy_api=grocy,
        )

    db.commit()
    db.refresh(updated)

    assert updated.grocy_meal_plan_id == 4242
    assert updated.status == "synced"
    assert updated.error_message is None
    assert updated.retry_count == 0
    fetch_new_mock.assert_not_called()


def test_retry_falls_back_to_reconcile_when_response_missing_id(
    db: Session, hh: Household, user: User
) -> None:
    """If Grocy returns a response without `created_object_id`, retry_line must
    fall back to snapshot/tuple reconciliation.
    """
    row = _failed_product_row()
    db.add(row)
    db.commit()
    db.refresh(row)

    grocy = MagicMock()
    grocy.create_meal_plan_entry.return_value = {}
    grocy.get_meal_plan.return_value = []

    with patch(
        "app.services.meal_plan.fetch_new_grocy_rows_window",
        return_value=[
            {
                "id": 5151,
                "day": DAY.isoformat(),
                "section_id": 1,
                "type": "product",
                "product_id": 546,
                "product_amount": "0.063",
                "product_qu_id": 82,
            }
        ],
    ):
        updated = retry_line(
            db,
            household_id=HH_ID,
            line_id=row.id,
            user_id=USER_ID,
            grocy_api=grocy,
        )

    db.commit()
    db.refresh(updated)

    assert updated.grocy_meal_plan_id == 5151
    assert updated.status == "synced"


def test_retry_rejects_syncing_status(db: Session, hh: Household, user: User) -> None:
    """A `syncing` row must not be retriable from the API — a concurrent batch
    task may still be in flight, and a second POST would duplicate the Grocy
    row.
    """
    from fastapi import HTTPException

    row = _failed_product_row()
    row.status = "syncing"
    db.add(row)
    db.commit()
    db.refresh(row)

    with pytest.raises(HTTPException) as exc_info:
        retry_line(
            db,
            household_id=HH_ID,
            line_id=row.id,
            user_id=USER_ID,
            grocy_api=MagicMock(),
        )

    assert exc_info.value.status_code == 409


def test_retry_rejects_other_users_row(db: Session, hh: Household, user: User) -> None:
    """A user must not retry another member's row in the same household."""
    from fastapi import HTTPException

    other_user = User(
        id=USER_ID + 1,
        email="other-retry@example.com",
        username="other-retry-user",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(other_user)
    db.commit()

    row = _failed_product_row()
    row.user_id = USER_ID + 1
    db.add(row)
    db.commit()
    db.refresh(row)

    with pytest.raises(HTTPException) as exc_info:
        retry_line(
            db,
            household_id=HH_ID,
            line_id=row.id,
            user_id=USER_ID,
            grocy_api=MagicMock(),
        )

    assert exc_info.value.status_code == 404

    fresh = db.get(MealPlan, row.id)
    assert fresh is not None
    assert fresh.status == "failed"
