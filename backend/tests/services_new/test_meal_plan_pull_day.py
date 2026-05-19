"""Tests for pull_grocy_day_to_local - recovery import of Grocy meal_plan rows."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app.models.household import Household, HouseholdUser, Role
from app.models.meal_plan import MealPlan
from app.models.user import User
from app.services.grocy_api import GrocyAPI
from app.services.meal_plan import pull_grocy_day_to_local

HID = 9191
DAY = date(2026, 5, 19)


@pytest.fixture()
def household_and_two_users(db: Session) -> tuple[Household, User, User]:
    role = Role(name="admin")
    db.add(role)
    db.commit()
    db.refresh(role)

    alice = User(
        email="alice@example.com",
        username="alice",
        hashed_password="x" * 60,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    bob = User(
        email="bob@example.com",
        username="bob",
        hashed_password="y" * 60,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(alice)
    db.add(bob)
    db.commit()
    db.refresh(alice)
    db.refresh(bob)

    household = Household(id=HID, name="HH", created_at=datetime.now(UTC))
    db.add(household)
    db.commit()
    db.refresh(household)

    for u in (alice, bob):
        db.add(
            HouseholdUser(
                household_id=household.id,
                user_id=u.id,
                role_id=role.id,
                is_active=True,
            )
        )
    db.commit()
    return household, alice, bob


def _product_row(*, id_: int, owner: int | None = None, done: bool = False) -> dict:
    row: dict = {
        "id": id_,
        "day": DAY.isoformat(),
        "type": "product",
        "section_id": 1,
        "product_id": 100 + id_,
        "product_amount": "2.5",
        "product_qu_id": 3,
        "done": "1" if done else "0",
    }
    if owner is not None:
        row["userfields"] = {"user_id": str(owner)}
    else:
        row["userfields"] = {"user_id": None}
    return row


def _recipe_row(*, id_: int, owner: int | None = None) -> dict:
    return {
        "id": id_,
        "day": DAY.isoformat(),
        "type": "recipe",
        "section_id": 2,
        "recipe_id": 500 + id_,
        "recipe_servings": "1.5",
        "done": "0",
        "userfields": {"user_id": str(owner) if owner is not None else None},
    }


def _note_row(*, id_: int) -> dict:
    return {
        "id": id_,
        "day": DAY.isoformat(),
        "type": "note",
        "section_id": 1,
        "note": "buy milk",
        "done": "0",
        "userfields": {"user_id": None},
    }


def _mock_grocy(rows: list[dict]) -> MagicMock:
    api = MagicMock(spec=GrocyAPI)
    api.get_meal_plan.return_value = rows
    api.get_product.return_value = {"id": 1, "name": "Test Product"}
    return api


def test_pulls_orphan_rows_inserts_locally_and_writes_userfield(
    db: Session, household_and_two_users
) -> None:
    household, alice, _bob = household_and_two_users
    api = _mock_grocy(
        [
            _product_row(id_=1, owner=None),
            _recipe_row(id_=2, owner=None),
        ]
    )

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 2
    assert result["pulled_already_done"] == 0
    assert result["skipped_already_local"] == 0
    assert result["skipped_other_owner"] == 0
    assert result["skipped_notes"] == 0
    assert result["userfield_write_failures"] == 0

    rows = db.exec(
        select(MealPlan).where(MealPlan.household_id == household.id)
    ).all()
    assert len(rows) == 2
    by_gid = {r.grocy_meal_plan_id: r for r in rows}

    product_row = by_gid[1]
    assert product_row.user_id == alice.id
    assert product_row.status == "synced"
    assert product_row.type == "product"
    assert product_row.product_grocy_id == 101
    assert product_row.product_amount == Decimal("2.5")
    assert product_row.product_amount_stock == Decimal("2.5")
    assert product_row.product_qu_id == 3
    assert product_row.done is False
    assert product_row.day == DAY

    recipe_row = by_gid[2]
    assert recipe_row.user_id == alice.id
    assert recipe_row.type == "recipe"
    assert recipe_row.recipe_grocy_id == 502
    assert recipe_row.recipe_servings == Decimal("1.5")

    assert api.put.call_count == 2
    put_paths = sorted(call.args[0] for call in api.put.call_args_list)
    assert put_paths == [
        "/userfields/meal_plan/1",
        "/userfields/meal_plan/2",
    ]


def test_skips_rows_owned_by_other_user(
    db: Session, household_and_two_users
) -> None:
    household, alice, bob = household_and_two_users
    api = _mock_grocy([_product_row(id_=10, owner=bob.id)])

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 0
    assert result["skipped_other_owner"] == 1
    rows = db.exec(select(MealPlan).where(MealPlan.household_id == household.id)).all()
    assert rows == []
    api.put.assert_not_called()


def test_skips_rows_already_local_for_household(
    db: Session, household_and_two_users
) -> None:
    household, alice, _bob = household_and_two_users

    local = MealPlan(
        household_id=household.id,
        user_id=alice.id,
        grocy_meal_plan_id=42,
        type="product",
        day=DAY,
        section_id=1,
        product_grocy_id=101,
        product_amount=Decimal("1"),
        product_amount_stock=Decimal("1"),
        product_qu_id=3,
        status="synced",
    )
    db.add(local)
    db.commit()

    api = _mock_grocy([_product_row(id_=42, owner=None)])

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 0
    assert result["skipped_already_local"] == 1
    rows = db.exec(select(MealPlan).where(MealPlan.household_id == household.id)).all()
    assert len(rows) == 1
    api.put.assert_not_called()


def test_pulls_note_rows(
    db: Session, household_and_two_users
) -> None:
    household, alice, _bob = household_and_two_users
    api = _mock_grocy([_note_row(id_=7)])

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 1
    assert result["skipped_notes"] == 0
    rows = db.exec(
        select(MealPlan).where(MealPlan.household_id == household.id)
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.type == "note"
    assert row.note == "buy milk"
    assert row.status == "synced"
    assert row.grocy_meal_plan_id == 7
    assert row.user_id == alice.id


def test_skips_unknown_type_rows(
    db: Session, household_and_two_users
) -> None:
    """skipped_notes counter now tracks only unknown types (not product/recipe/note)."""
    household, alice, _bob = household_and_two_users
    unknown = {
        "id": 99,
        "day": DAY.isoformat(),
        "type": "alien",
        "section_id": 1,
        "done": "0",
        "userfields": {"user_id": None},
    }
    api = _mock_grocy([unknown])

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 0
    assert result["skipped_notes"] == 1
    rows = db.exec(
        select(MealPlan).where(MealPlan.household_id == household.id)
    ).all()
    assert rows == []


def test_pulls_done_rows_as_done_without_consumption_record(
    db: Session, household_and_two_users
) -> None:
    household, alice, _bob = household_and_two_users
    api = _mock_grocy([_product_row(id_=5, owner=None, done=True)])

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 0
    assert result["pulled_already_done"] == 1

    rows = db.exec(select(MealPlan).where(MealPlan.household_id == household.id)).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.done is True
    assert row.done_at is not None


def test_does_not_overwrite_existing_userfield_with_put(
    db: Session, household_and_two_users
) -> None:
    household, alice, _bob = household_and_two_users
    api = _mock_grocy([_product_row(id_=8, owner=alice.id)])

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 1
    rows = db.exec(select(MealPlan).where(MealPlan.household_id == household.id)).all()
    assert len(rows) == 1
    assert rows[0].user_id == alice.id
    api.put.assert_not_called()


def test_userfield_put_failure_is_swallowed_and_counted(
    db: Session, household_and_two_users
) -> None:
    household, alice, _bob = household_and_two_users
    api = _mock_grocy([_product_row(id_=11, owner=None)])
    api.put.side_effect = RuntimeError("boom")

    result = pull_grocy_day_to_local(
        db,
        household_id=household.id,
        user_id=alice.id,
        day=DAY,
        grocy_api=api,
    )

    assert result["pulled"] == 1
    assert result["userfield_write_failures"] == 1
    rows = db.exec(select(MealPlan).where(MealPlan.household_id == household.id)).all()
    assert len(rows) == 1
    assert rows[0].user_id == alice.id
