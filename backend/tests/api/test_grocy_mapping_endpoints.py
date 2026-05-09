"""Tests for the per-household Grocy-mapping HTTP surface.

Endpoints under test:
- GET  /api/grocy-mapping/registry              (any authenticated user)
- GET  /api/households/{id}/grocy-mapping       (active member)
- PUT  /api/households/{id}/grocy-mapping       (admin only, replace-all)
- GET  /api/households/grocy/quantity-units     (admin only, proxy to Grocy)
"""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser
from app.models.household import Household, HouseholdGrocyMapping, HouseholdUser, Role


@pytest.fixture()
def admin_role(db: Session) -> Role:
    role = Role(name="admin")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture()
def user_role(db: Session) -> Role:
    role = Role(name="user")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture()
def household(db: Session) -> Household:
    h = Household(name="Home", grocy_url="http://grocy.local", created_at=datetime.now(UTC))
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@pytest.fixture()
def admin_membership(
    db: Session, test_user: AuthenticatedUser, household: Household, admin_role: Role
) -> HouseholdUser:
    hu = HouseholdUser(
        household_id=household.id, user_id=test_user.id, role_id=admin_role.id
    )
    db.add(hu)
    db.commit()
    db.refresh(hu)
    return hu


@pytest.fixture()
def user_membership(
    db: Session, test_user: AuthenticatedUser, household: Household, user_role: Role
) -> HouseholdUser:
    hu = HouseholdUser(
        household_id=household.id, user_id=test_user.id, role_id=user_role.id
    )
    db.add(hu)
    db.commit()
    db.refresh(hu)
    return hu


def _seed_mapping(db: Session, household_id: int, values: dict[str, str | None]) -> None:
    for key, value in values.items():
        db.add(HouseholdGrocyMapping(household_id=household_id, key=key, value=value))
    db.commit()


class TestRegistryEndpoint:
    def test_returns_three_keys(self, client):
        response = client.get("/api/grocy-mapping/registry")
        assert response.status_code == 200
        data = response.json()
        keys = {entry["key"] for entry in data}
        assert keys == {"gram_unit_id", "ml_unit_id", "portion_unit_id"}

    def test_each_entry_has_type(self, client):
        response = client.get("/api/grocy-mapping/registry")
        for entry in response.json():
            assert entry["type"] == "int"


class TestGetMapping:
    def test_member_can_read_mapping(self, client, db, admin_membership, household):
        _seed_mapping(
            db,
            household.id,
            {"gram_unit_id": "82", "ml_unit_id": "85", "portion_unit_id": "9"},
        )
        response = client.get(f"/api/households/{household.id}/grocy-mapping")
        assert response.status_code == 200
        items = {row["key"]: row["value"] for row in response.json()}
        assert items == {"gram_unit_id": "82", "ml_unit_id": "85", "portion_unit_id": "9"}

    def test_user_role_member_can_read(self, client, db, user_membership, household):
        _seed_mapping(db, household.id, {"gram_unit_id": "82"})
        response = client.get(f"/api/households/{household.id}/grocy-mapping")
        assert response.status_code == 200
        assert any(row["key"] == "gram_unit_id" for row in response.json())

    def test_inactive_member_blocked(
        self, client, db, test_user, household, user_role
    ):
        hu = HouseholdUser(
            household_id=household.id,
            user_id=test_user.id,
            role_id=user_role.id,
            is_active=False,
        )
        db.add(hu)
        db.commit()
        response = client.get(f"/api/households/{household.id}/grocy-mapping")
        assert response.status_code == 403

    def test_non_member_returns_403(self, client, household):
        response = client.get(f"/api/households/{household.id}/grocy-mapping")
        assert response.status_code == 403


class TestUpdateMapping:
    def test_admin_replaces_all_values(self, client, db, admin_membership, household):
        _seed_mapping(
            db,
            household.id,
            {"gram_unit_id": "1", "ml_unit_id": "2", "portion_unit_id": "3"},
        )
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "82"},
                {"key": "ml_unit_id", "value": "85"},
                {"key": "portion_unit_id", "value": "9"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 200
        items = {row["key"]: row["value"] for row in response.json()}
        assert items == {"gram_unit_id": "82", "ml_unit_id": "85", "portion_unit_id": "9"}

    def test_admin_can_set_value_to_null(self, client, db, admin_membership, household):
        _seed_mapping(db, household.id, {"gram_unit_id": "82"})
        body = {
            "items": [
                {"key": "gram_unit_id", "value": None},
                {"key": "ml_unit_id", "value": "85"},
                {"key": "portion_unit_id", "value": "9"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 200
        items = {row["key"]: row["value"] for row in response.json()}
        assert items["gram_unit_id"] is None

    def test_empty_string_normalized_to_null(
        self, client, db, admin_membership, household
    ):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": ""},
                {"key": "ml_unit_id", "value": "85"},
                {"key": "portion_unit_id", "value": "9"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 200
        items = {row["key"]: row["value"] for row in response.json()}
        assert items["gram_unit_id"] is None

    def test_non_admin_returns_403(self, client, db, user_membership, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "1"},
                {"key": "ml_unit_id", "value": "2"},
                {"key": "portion_unit_id", "value": "3"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 403

    def test_unknown_key_rejected(self, client, db, admin_membership, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "1"},
                {"key": "ml_unit_id", "value": "2"},
                {"key": "portion_unit_id", "value": "3"},
                {"key": "totally_made_up", "value": "1"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 422

    def test_duplicate_key_rejected(self, client, db, admin_membership, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "1"},
                {"key": "gram_unit_id", "value": "2"},
                {"key": "ml_unit_id", "value": "2"},
                {"key": "portion_unit_id", "value": "3"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 422

    def test_missing_key_rejected(self, client, db, admin_membership, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "1"},
                {"key": "ml_unit_id", "value": "2"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 422

    def test_invalid_value_rejected(self, client, db, admin_membership, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "not-an-int"},
                {"key": "ml_unit_id", "value": "85"},
                {"key": "portion_unit_id", "value": "9"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 422

    def test_negative_value_rejected(self, client, db, admin_membership, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "-5"},
                {"key": "ml_unit_id", "value": "85"},
                {"key": "portion_unit_id", "value": "9"},
            ]
        }
        response = client.put(f"/api/households/{household.id}/grocy-mapping", json=body)
        assert response.status_code == 422

    def test_update_persists_to_db(self, client, db, admin_membership, test_user, household):
        body = {
            "items": [
                {"key": "gram_unit_id", "value": "82"},
                {"key": "ml_unit_id", "value": "85"},
                {"key": "portion_unit_id", "value": "9"},
            ]
        }
        client.put(f"/api/households/{household.id}/grocy-mapping", json=body)

        rows = list(
            db.exec(
                select(HouseholdGrocyMapping).where(
                    HouseholdGrocyMapping.household_id == household.id
                )
            ).all()
        )
        by_key = {r.key: r for r in rows}
        assert by_key["gram_unit_id"].value == "82"
        assert by_key["gram_unit_id"].updated_by_user_id == test_user.id


class TestQuantityUnitsEndpoint:
    def test_admin_proxies_grocy_response(
        self, grocy_client, db, test_user, household, admin_role
    ):
        hu = HouseholdUser(
            household_id=household.id, user_id=test_user.id, role_id=admin_role.id
        )
        db.add(hu)
        db.commit()

        from app.core.auth import get_grocy_api
        from app.main import app

        mock_api = app.dependency_overrides[get_grocy_api]()
        mock_api.get_quantity_units.return_value = [
            {"id": 82, "name": "g"},
            {"id": 85, "name": "ml"},
        ]

        response = grocy_client.get(
            f"/api/households/grocy/quantity-units?household_id={household.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data == [{"id": 82, "name": "g"}, {"id": 85, "name": "ml"}]

    def test_non_admin_returns_403(self, grocy_client, db, test_user, household, user_role):
        hu = HouseholdUser(
            household_id=household.id, user_id=test_user.id, role_id=user_role.id
        )
        db.add(hu)
        db.commit()

        response = grocy_client.get(
            f"/api/households/grocy/quantity-units?household_id={household.id}"
        )
        assert response.status_code == 403

    def test_grocy_error_returns_502(
        self, grocy_client, db, test_user, household, admin_role
    ):
        hu = HouseholdUser(
            household_id=household.id, user_id=test_user.id, role_id=admin_role.id
        )
        db.add(hu)
        db.commit()

        from app.core.auth import get_grocy_api
        from app.main import app
        from app.services.grocy_api import GrocyError

        mock_api = app.dependency_overrides[get_grocy_api]()
        mock_api.get_quantity_units.side_effect = GrocyError("boom")

        response = grocy_client.get(
            f"/api/households/grocy/quantity-units?household_id={household.id}"
        )
        assert response.status_code == 502
