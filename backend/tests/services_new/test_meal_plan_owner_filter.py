"""Tests for filter_meal_plan_to_user and parse_userfield_user_id."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlmodel import Session

from app.models.household import Household, HouseholdUser, Role
from app.models.meal_plan import MealPlan
from app.models.user import User
from app.services.meal_plan import (
    filter_meal_plan_to_user,
    parse_userfield_user_id,
)

HID = 8181


@pytest.fixture()
def household_and_two_users(db: Session) -> tuple[Household, User, User]:
    admin_role = Role(name="admin")
    db.add(admin_role)
    db.commit()
    db.refresh(admin_role)

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
                role_id=admin_role.id,
                is_active=True,
            )
        )
    db.commit()
    return household, alice, bob


def _grocy(*, id_: int, owner: int | None | str, missing_userfields: bool = False) -> dict:
    row = {
        "id": id_,
        "day": "2026-05-12",
        "type": "product",
        "section_id": 1,
        "product_id": 10,
        "product_amount": "1",
        "product_qu_id": 2,
    }
    if missing_userfields:
        return row
    row["userfields"] = {"user_id": owner if owner is None else str(owner)}
    return row


def test_parse_userfield_user_id_returns_int_when_set() -> None:
    assert parse_userfield_user_id(_grocy(id_=1, owner=42)) == 42


def test_parse_userfield_user_id_returns_none_when_null() -> None:
    assert parse_userfield_user_id(_grocy(id_=1, owner=None)) is None


def test_parse_userfield_user_id_returns_none_when_missing_userfields() -> None:
    assert parse_userfield_user_id(_grocy(id_=1, owner=None, missing_userfields=True)) is None


def test_parse_userfield_user_id_returns_none_for_garbage_value() -> None:
    row = {"userfields": {"user_id": "not-a-number"}}
    assert parse_userfield_user_id(row) is None


def test_filter_keeps_only_rows_with_matching_userfield(
    db: Session, household_and_two_users
) -> None:
    household, alice, bob = household_and_two_users
    meal_plan = [
        _grocy(id_=1, owner=alice.id),
        _grocy(id_=2, owner=bob.id),
        _grocy(id_=3, owner=alice.id),
    ]

    out = filter_meal_plan_to_user(db, meal_plan, household_id=household.id, user_id=alice.id)

    assert [m["id"] for m in out] == [1, 3]


def test_filter_falls_back_to_local_db_when_userfield_null(
    db: Session, household_and_two_users
) -> None:
    """If a Grocy row's userfield is NULL (e.g. userfield write failed when
    the row was POSTed), we look up the owner in the local meal_plans table
    by grocy_meal_plan_id."""
    household, alice, _bob = household_and_two_users

    local = MealPlan(
        household_id=household.id,
        user_id=alice.id,
        grocy_meal_plan_id=999,
        type="product",
        day=datetime(2026, 5, 12).date(),
        section_id=1,
        product_id=10,
        product_amount=Decimal("1"),
        product_qu_id=2,
        status="synced",
    )
    db.add(local)
    db.commit()

    meal_plan = [_grocy(id_=999, owner=None)]

    out = filter_meal_plan_to_user(db, meal_plan, household_id=household.id, user_id=alice.id)

    assert [m["id"] for m in out] == [999]


def test_filter_drops_rows_when_both_userfield_and_local_owner_are_null(
    db: Session, household_and_two_users
) -> None:
    """A row that has no userfield and no local mapping cannot be attributed
    to anyone; we conservatively drop it from the caller's view."""
    household, alice, _bob = household_and_two_users
    meal_plan = [_grocy(id_=12345, owner=None)]

    out = filter_meal_plan_to_user(db, meal_plan, household_id=household.id, user_id=alice.id)

    assert out == []


def test_filter_drops_other_users_rows_even_when_local_db_matches_caller(
    db: Session, household_and_two_users
) -> None:
    """Grocy userfield wins over local DB when both are set. (Local DB could
    be stale; Grocy is canonical for ownership across clients.)"""
    household, alice, bob = household_and_two_users

    # Local DB says alice owns it…
    local = MealPlan(
        household_id=household.id,
        user_id=alice.id,
        grocy_meal_plan_id=42,
        type="product",
        day=datetime(2026, 5, 12).date(),
        section_id=1,
        product_id=10,
        product_amount=Decimal("1"),
        product_qu_id=2,
        status="synced",
    )
    db.add(local)
    db.commit()

    # …but Grocy says bob does. Bob wins.
    meal_plan = [_grocy(id_=42, owner=bob.id)]

    out_for_alice = filter_meal_plan_to_user(
        db, meal_plan, household_id=household.id, user_id=alice.id
    )
    out_for_bob = filter_meal_plan_to_user(
        db, meal_plan, household_id=household.id, user_id=bob.id
    )

    assert out_for_alice == []
    assert [m["id"] for m in out_for_bob] == [42]
