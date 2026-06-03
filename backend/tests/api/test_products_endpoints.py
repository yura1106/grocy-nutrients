"""
Integration tests for app/api/endpoints/products.py

Focus: the PATCH /products/{id}/fresh toggle endpoint — auth/membership,
household scoping, and the flag round-trip into product reads.
"""

from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.household import Household, HouseholdUser, Role
from app.models.product import Product, ProductData
from tests.conftest import TEST_HOUSEHOLD_ID

HID = TEST_HOUSEHOLD_ID


def _make_product(db, *, grocy_id, household_id=HID, is_fresh=False):
    product = Product(
        grocy_id=grocy_id,
        name=f"Product {grocy_id}",
        product_group_id=1,
        active=True,
        is_fresh=is_fresh,
        household_id=household_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    # Latest data so the product appears in reads
    db.add(ProductData(product_id=product.id, calories=10.0, carbohydrates_of_sugars=5.0))
    db.commit()
    return product


@pytest.mark.integration
class TestSetProductFreshEndpoint:
    """Tests for PATCH /api/products/{id}/fresh."""

    def test_toggle_fresh_on_returns_updated_flag(self, client, db, test_household):
        product = _make_product(db, grocy_id=201, is_fresh=False)

        response = client.patch(
            f"/api/products/{product.id}/fresh",
            json={"is_fresh": True},
            params={"household_id": HID},
        )
        assert response.status_code == 200
        assert response.json() == {"id": product.id, "is_fresh": True}

        db.refresh(product)
        assert product.is_fresh is True

    def test_toggle_fresh_off(self, client, db, test_household):
        product = _make_product(db, grocy_id=202, is_fresh=True)

        response = client.patch(
            f"/api/products/{product.id}/fresh",
            json={"is_fresh": False},
            params={"household_id": HID},
        )
        assert response.status_code == 200
        assert response.json()["is_fresh"] is False
        db.refresh(product)
        assert product.is_fresh is False

    def test_unknown_product_returns_404(self, client, test_household):
        response = client.patch(
            "/api/products/999999/fresh",
            json={"is_fresh": True},
            params={"household_id": HID},
        )
        assert response.status_code == 404

    def test_product_in_other_household_returns_404(self, client, db, test_household):
        """A product that exists but belongs to a household the (member) user
        passes as household_id mismatch → scoped query yields nothing → 404."""
        # Product belongs to another household, but we query with HID.
        other = _make_product(db, grocy_id=203, household_id=HID + 999)
        response = client.patch(
            f"/api/products/{other.id}/fresh",
            json={"is_fresh": True},
            params={"household_id": HID},
        )
        assert response.status_code == 404

    def test_not_a_member_returns_403(self, client, db, test_household):
        """User is authed but not a member of the target household → 403."""
        role = db.exec(select(Role).where(Role.name == "admin")).first()
        other_hh = Household(id=HID + 1, name="Other Household", created_at=datetime.now(UTC))
        db.add(other_hh)
        db.commit()
        # No HouseholdUser membership created for test_user in other_hh.
        product = _make_product(db, grocy_id=204, household_id=other_hh.id)

        response = client.patch(
            f"/api/products/{product.id}/fresh",
            json={"is_fresh": True},
            params={"household_id": other_hh.id},
        )
        assert response.status_code == 403
        # Flag untouched
        db.refresh(product)
        assert product.is_fresh is False
        assert role is not None  # sanity: admin role exists from test_household

    def test_inactive_membership_returns_403(self, client, db, test_user):
        """Inactive membership is not a member → 403."""
        role = Role(name="member")
        db.add(role)
        db.commit()
        db.refresh(role)
        hh = Household(id=HID + 2, name="Inactive HH", created_at=datetime.now(UTC))
        db.add(hh)
        db.commit()
        db.add(
            HouseholdUser(
                household_id=hh.id,
                user_id=test_user.id,
                role_id=role.id,
                is_active=False,
            )
        )
        db.commit()
        product = _make_product(db, grocy_id=205, household_id=hh.id)

        response = client.patch(
            f"/api/products/{product.id}/fresh",
            json={"is_fresh": True},
            params={"household_id": hh.id},
        )
        assert response.status_code == 403

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.patch(
            "/api/products/1/fresh",
            json={"is_fresh": True},
            params={"household_id": HID},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestProductReadsExposeIsFresh:
    """is_fresh round-trips into the product list and detail reads."""

    def test_products_list_includes_is_fresh(self, client, db, test_household):
        _make_product(db, grocy_id=210, is_fresh=True)
        response = client.get("/api/products", params={"household_id": HID})
        assert response.status_code == 200
        product = next(p for p in response.json()["products"] if p["grocy_id"] == 210)
        assert product["is_fresh"] is True

    def test_product_detail_includes_is_fresh(self, client, db, test_household):
        product = _make_product(db, grocy_id=211, is_fresh=True)
        response = client.get(f"/api/products/{product.id}", params={"household_id": HID})
        assert response.status_code == 200
        assert response.json()["is_fresh"] is True
