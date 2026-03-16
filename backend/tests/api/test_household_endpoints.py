"""Tests for household endpoints: soft delete, data summary, delete household, backfill."""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models.household import Household, HouseholdUser, Role
from app.models.product import ConsumedProduct, Product, ProductData
from app.models.user import User


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
    h = Household(name="Test Home", created_at=datetime.now(UTC))
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@pytest.fixture()
def admin_membership(
    db: Session, test_user: User, household: Household, admin_role: Role
) -> HouseholdUser:
    hu = HouseholdUser(
        household_id=household.id,
        user_id=test_user.id,
        role_id=admin_role.id,
    )
    db.add(hu)
    db.commit()
    db.refresh(hu)
    return hu


class TestRemoveUser:
    """Tests for DELETE /{household_id}/users/{user_id} (soft delete)."""

    def test_remove_user_requires_confirm(self, client, admin_membership, test_user, household):
        response = client.delete(f"/api/households/{household.id}/users/{test_user.id}")
        assert response.status_code == 400
        assert "Confirmation required" in response.json()["detail"]

    def test_remove_user_with_confirm_returns_204(
        self, client, db, admin_membership, household, user_role
    ):
        # Create another user to remove
        other_user = User(
            email="other@example.com",
            username="other",
            hashed_password=get_password_hash("Test1234!"),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        hu = HouseholdUser(
            household_id=household.id,
            user_id=other_user.id,
            role_id=user_role.id,
        )
        db.add(hu)
        db.commit()

        response = client.delete(
            f"/api/households/{household.id}/users/{other_user.id}?confirm=true"
        )
        assert response.status_code == 204

        # Verify soft delete
        db.refresh(hu)
        assert hu.is_active is False
        assert hu.deactivated_at is not None

    def test_removed_user_not_in_household_list(
        self, client, db, admin_membership, household, user_role
    ):
        other_user = User(
            email="other2@example.com",
            username="other2",
            hashed_password=get_password_hash("Test1234!"),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        hu = HouseholdUser(
            household_id=household.id,
            user_id=other_user.id,
            role_id=user_role.id,
        )
        db.add(hu)
        db.commit()

        # Remove user
        client.delete(f"/api/households/{household.id}/users/{other_user.id}?confirm=true")

        # Check household detail
        response = client.get(f"/api/households/{household.id}")
        assert response.status_code == 200
        members = response.json()["members"]
        member_ids = [m["user_id"] for m in members]
        assert other_user.id not in member_ids

    def test_readd_reactivates_membership(
        self, client, db, admin_membership, household, user_role
    ):
        other_user = User(
            email="reactivate@example.com",
            username="reactivate",
            hashed_password=get_password_hash("Test1234!"),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        hu = HouseholdUser(
            household_id=household.id,
            user_id=other_user.id,
            role_id=user_role.id,
        )
        db.add(hu)
        db.commit()

        # Remove
        client.delete(f"/api/households/{household.id}/users/{other_user.id}?confirm=true")
        db.refresh(hu)
        assert hu.is_active is False

        # Re-add
        response = client.post(
            f"/api/households/{household.id}/users",
            json={
                "user_id": other_user.id,
                "role_name": "user",
            },
        )
        assert response.status_code == 200

        db.refresh(hu)
        assert hu.is_active is True
        assert hu.deactivated_at is None


class TestDataSummary:
    """Tests for GET /{household_id}/users/{user_id}/data-summary."""

    def test_data_summary_returns_counts(self, client, db, admin_membership, test_user, household):
        # Create some consumed products for this user+household
        product = Product(
            grocy_id=1,
            name="P1",
            product_group_id=1,
            active=True,
            household_id=household.id,
            created_at=datetime.now(UTC),
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        pd = ProductData(product_id=product.id, price=5.0, created_at=datetime.now(UTC))
        db.add(pd)
        db.commit()
        db.refresh(pd)

        from datetime import date

        cp = ConsumedProduct(
            product_data_id=pd.id,
            date=date.today(),
            quantity=2.0,
            household_id=household.id,
            user_id=test_user.id,
            created_at=datetime.now(UTC),
        )
        db.add(cp)
        db.commit()

        response = client.get(f"/api/households/{household.id}/users/{test_user.id}/data-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["consumed_products"] == 1
        assert data["total"] >= 1


class TestDeleteHousehold:
    """Tests for DELETE /{household_id}."""

    def test_delete_household_wrong_password_returns_403(
        self, client, admin_membership, household
    ):
        response = client.request(
            "DELETE",
            f"/api/households/{household.id}",
            json={
                "password": "wrongpassword",
                "confirmation_text": f"DELETE {household.name}",
            },
        )
        assert response.status_code == 403
        assert "Incorrect password" in response.json()["detail"]

    def test_delete_household_wrong_confirmation_returns_400(
        self, client, admin_membership, household
    ):
        response = client.request(
            "DELETE",
            f"/api/households/{household.id}",
            json={
                "password": "testpassword123",
                "confirmation_text": "wrong text",
            },
        )
        assert response.status_code == 400

    def test_delete_household_success(self, client, db, admin_membership, household):
        response = client.request(
            "DELETE",
            f"/api/households/{household.id}",
            json={
                "password": "testpassword123",
                "confirmation_text": f"DELETE {household.name}",
            },
        )
        assert response.status_code == 204

        # Verify household is deleted
        from sqlmodel import select

        result = db.exec(select(Household).where(Household.id == household.id)).first()
        assert result is None


class TestBackfill:
    """Tests for GET /{household_id}/backfill-status and POST /{household_id}/backfill."""

    def test_backfill_status_returns_counts(self, client, db, admin_membership, household):
        # Create a product with null household_id
        product = Product(
            grocy_id=99,
            name="Orphan",
            product_group_id=1,
            active=True,
            created_at=datetime.now(UTC),
        )
        db.add(product)
        db.commit()

        response = client.get(f"/api/households/{household.id}/backfill-status")
        assert response.status_code == 200
        data = response.json()
        assert data["products"] >= 1
        assert data["total"] >= 1

    def test_backfill_fills_null_values(self, client, db, admin_membership, test_user, household):
        # Create orphan product
        product = Product(
            grocy_id=100,
            name="Orphan2",
            product_group_id=1,
            active=True,
            created_at=datetime.now(UTC),
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        response = client.post(f"/api/households/{household.id}/backfill")
        assert response.status_code == 200
        data = response.json()
        assert data["updated_household_id"] >= 1

        # Verify product now has household_id
        db.refresh(product)
        assert product.household_id == household.id

    def test_backfill_is_idempotent(self, client, db, admin_membership, household):
        # Run backfill twice
        client.post(f"/api/households/{household.id}/backfill")
        response = client.post(f"/api/households/{household.id}/backfill")
        assert response.status_code == 200
        data = response.json()
        assert data["updated_household_id"] == 0
        assert data["updated_user_id"] == 0

    def test_backfill_status_zero_after_backfill(self, client, db, admin_membership, household):
        client.post(f"/api/households/{household.id}/backfill")
        response = client.get(f"/api/households/{household.id}/backfill-status")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_backfill_non_admin_returns_403(self, client, db, household, test_user, user_role):
        # Remove admin membership, add user membership
        from sqlmodel import select

        hu = db.exec(
            select(HouseholdUser).where(
                HouseholdUser.household_id == household.id,
                HouseholdUser.user_id == test_user.id,
            )
        ).first()
        if hu:
            db.delete(hu)
            db.commit()

        hu = HouseholdUser(household_id=household.id, user_id=test_user.id, role_id=user_role.id)
        db.add(hu)
        db.commit()

        response = client.get(f"/api/households/{household.id}/backfill-status")
        assert response.status_code == 403
