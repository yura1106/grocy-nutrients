"""Tests for build_grocy_api factory + GrocyAPI mapping properties."""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from app.core.encryption import encrypt_api_key
from app.core.grocy_mapping_keys import GrocyMappingKey, MissingHouseholdSetting
from app.core.security import get_password_hash
from app.models.household import Household, HouseholdGrocyMapping, HouseholdUser, Role
from app.models.user import User
from app.services.grocy_api import (
    GrocyAPI,
    GrocyConfigError,
    build_grocy_api,
)


@pytest.fixture()
def admin_role(db: Session) -> Role:
    role = Role(name="admin")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture()
def user_with_password(db: Session) -> User:
    """Standalone user with a known plaintext-derived hashed_password.

    `encrypt_api_key` uses the user's hashed_password as the SCellSeal key,
    so we need a stable hash here.
    """
    user = User(
        email="grocyuser@example.com",
        username="grocyuser",
        hashed_password=get_password_hash("grocy-pass-123"),
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def household(db: Session) -> Household:
    h = Household(name="Home", grocy_url="http://grocy.local", created_at=datetime.now(UTC))
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def _make_membership(
    db: Session,
    household: Household,
    user: User,
    role: Role,
    *,
    api_key_plaintext: str | None = "real-key",
    is_active: bool = True,
) -> HouseholdUser:
    encrypted = (
        encrypt_api_key(api_key_plaintext, user.hashed_password) if api_key_plaintext else None
    )
    hu = HouseholdUser(
        household_id=household.id,
        user_id=user.id,
        role_id=role.id,
        grocy_api_key=encrypted,
        is_active=is_active,
    )
    db.add(hu)
    db.commit()
    db.refresh(hu)
    return hu


def _seed_mapping(
    db: Session,
    household: Household,
    *,
    gram: str | None = "82",
    ml: str | None = "85",
    portion: str | None = "9",
) -> None:
    for key, value in (
        (GrocyMappingKey.GRAM_UNIT_ID, gram),
        (GrocyMappingKey.ML_UNIT_ID, ml),
        (GrocyMappingKey.PORTION_UNIT_ID, portion),
    ):
        db.add(HouseholdGrocyMapping(household_id=household.id, key=key.value, value=value))
    db.commit()


class TestBuildGrocyApiHappyPath:
    def test_returns_grocy_api_with_loaded_mapping(
        self, db, household, user_with_password, admin_role
    ):
        _make_membership(db, household, user_with_password, admin_role)
        _seed_mapping(db, household)

        api = build_grocy_api(db, household.id, user_with_password.id)

        assert isinstance(api, GrocyAPI)
        assert api.url == "http://grocy.local/api"
        assert api.headers["GROCY-API-KEY"] == "real-key"
        assert api.gram_unit_id == 82
        assert api.ml_unit_id == 85
        assert api.portion_unit_id == 9

    def test_loads_mapping_with_null_values(self, db, household, user_with_password, admin_role):
        # NULL/missing values are tolerated at load time — they only blow up when read.
        _make_membership(db, household, user_with_password, admin_role)
        _seed_mapping(db, household, gram=None, ml=None, portion=None)

        api = build_grocy_api(db, household.id, user_with_password.id)

        assert isinstance(api, GrocyAPI)
        with pytest.raises(MissingHouseholdSetting) as exc_info:
            _ = api.gram_unit_id
        assert exc_info.value.key == "gram_unit_id"


class TestBuildGrocyApiConfigErrors:
    def test_not_a_member_raises(self, db, household, user_with_password):
        # No HouseholdUser row at all.
        with pytest.raises(GrocyConfigError) as exc_info:
            build_grocy_api(db, household.id, user_with_password.id)
        assert exc_info.value.code == "not_a_member"

    def test_inactive_membership_treated_as_not_a_member(
        self, db, household, user_with_password, admin_role
    ):
        _make_membership(db, household, user_with_password, admin_role, is_active=False)
        with pytest.raises(GrocyConfigError) as exc_info:
            build_grocy_api(db, household.id, user_with_password.id)
        assert exc_info.value.code == "not_a_member"

    def test_no_api_key_raises_config_error(self, db, household, user_with_password, admin_role):
        _make_membership(db, household, user_with_password, admin_role, api_key_plaintext=None)
        with pytest.raises(GrocyConfigError) as exc_info:
            build_grocy_api(db, household.id, user_with_password.id)
        assert exc_info.value.code == "no_api_key"

    def test_no_grocy_url_raises_config_error(self, db, user_with_password, admin_role):
        h = Household(name="No URL Home", grocy_url=None, created_at=datetime.now(UTC))
        db.add(h)
        db.commit()
        db.refresh(h)
        _make_membership(db, h, user_with_password, admin_role)

        with pytest.raises(GrocyConfigError) as exc_info:
            build_grocy_api(db, h.id, user_with_password.id)
        assert exc_info.value.code == "no_grocy_url"


class TestGrocyConfigError:
    def test_carries_code_and_detail(self):
        err = GrocyConfigError("not_a_member", "nope")
        assert err.code == "not_a_member"
        assert err.detail == "nope"
        assert str(err) == "nope"


class TestGrocyApiTypedValueCaching:
    def test_repeated_property_access_uses_cache(
        self, db, household, user_with_password, admin_role
    ):
        _make_membership(db, household, user_with_password, admin_role)
        _seed_mapping(db, household)

        api = build_grocy_api(db, household.id, user_with_password.id)

        # First access populates cache, subsequent accesses hit it.
        assert api.gram_unit_id == 82
        assert api.gram_unit_id == 82
        assert "gram_unit_id" in api._cast_cache

    def test_missing_key_raises_with_key_info(self, db, household, user_with_password, admin_role):
        _make_membership(db, household, user_with_password, admin_role)
        # Only seed two of three keys.
        db.add(
            HouseholdGrocyMapping(
                household_id=household.id, key=GrocyMappingKey.GRAM_UNIT_ID.value, value="82"
            )
        )
        db.add(
            HouseholdGrocyMapping(
                household_id=household.id, key=GrocyMappingKey.ML_UNIT_ID.value, value="85"
            )
        )
        db.commit()

        api = build_grocy_api(db, household.id, user_with_password.id)
        with pytest.raises(MissingHouseholdSetting) as exc_info:
            _ = api.portion_unit_id
        assert exc_info.value.key == "portion_unit_id"

    def test_empty_string_treated_as_missing(self, db, household, user_with_password, admin_role):
        _make_membership(db, household, user_with_password, admin_role)
        db.add(
            HouseholdGrocyMapping(
                household_id=household.id, key=GrocyMappingKey.GRAM_UNIT_ID.value, value=""
            )
        )
        db.commit()

        api = build_grocy_api(db, household.id, user_with_password.id)
        with pytest.raises(MissingHouseholdSetting):
            _ = api.gram_unit_id

    def test_gram_ml_units_pair(self, db, household, user_with_password, admin_role):
        _make_membership(db, household, user_with_password, admin_role)
        _seed_mapping(db, household)

        api = build_grocy_api(db, household.id, user_with_password.id)
        assert api.gram_ml_units == (82, 85)
