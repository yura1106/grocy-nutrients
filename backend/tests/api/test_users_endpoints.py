"""
Integration tests for app/api/endpoints/users.py

Tests: GET /api/users/me, PUT /api/users/me, GET /api/users/grocy/system-info
"""

import pytest

from app.core.security import get_password_hash
from app.models.user import User
from app.services.grocy_api import GrocyAuthError, GrocyError, GrocyRequestError


@pytest.mark.integration
class TestGetCurrentUserEndpoint:
    """Tests for the get current user endpoint."""

    def test_returns_current_user_data(self, client):
        # Arrange & Act
        response = client.get("/api/users/me")
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_returns_user_id_field(self, client):
        response = client.get("/api/users/me")
        assert "id" in response.json()
        assert response.json()["id"] is not None

    def test_does_not_expose_hashed_password(self, client):
        response = client.get("/api/users/me")
        data = response.json()
        assert "hashed_password" not in data
        assert "password" not in data

    def test_returns_is_active_field(self, client):
        response = client.get("/api/users/me")
        data = response.json()
        assert "is_active" in data
        assert data["is_active"] is True

    def test_unauthenticated_request_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 401


@pytest.mark.integration
class TestUpdateCurrentUserEndpoint:
    """Tests for the update current user endpoint."""

    def test_update_email_returns_200_with_new_email(self, client):
        response = client.put("/api/users/me", json={"email": "updated@example.com"})
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_update_with_same_email_as_own_is_allowed(self, client, test_user):
        # Updating with the same email should not return 400
        response = client.put("/api/users/me", json={"email": test_user.email})
        assert response.status_code == 200

    def test_update_with_same_username_as_own_is_allowed(self, client, test_user):
        response = client.put("/api/users/me", json={"username": test_user.username})
        assert response.status_code == 200

    def test_update_with_duplicate_email_returns_400(self, client, db):
        # Create a second user with a different email
        other = User(
            email="other_users@example.com",
            username="otheruseruniq",
            hashed_password=get_password_hash("password123"),
        )
        db.add(other)
        db.commit()

        # Attempt to update email to the second user's email
        response = client.put("/api/users/me", json={"email": "other_users@example.com"})
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_update_with_duplicate_username_returns_400(self, client, db):
        other = User(
            email="other2_users@example.com",
            username="otheruseruniq2",
            hashed_password=get_password_hash("password123"),
        )
        db.add(other)
        db.commit()

        response = client.put("/api/users/me", json={"username": "otheruseruniq2"})
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_update_empty_body_returns_200(self, client):
        # Empty request body — nothing changes
        response = client.put("/api/users/me", json={})
        assert response.status_code == 200

    def test_unauthenticated_update_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.put("/api/users/me", json={"email": "x@x.com"})
        assert response.status_code == 401


@pytest.mark.integration
class TestGrocySystemInfoEndpoint:
    """Tests for the Grocy system info endpoint."""

    def test_missing_household_id_returns_422(self, client):
        # No household_id query param → validation error
        response = client.get("/api/users/grocy/system-info")
        assert response.status_code == 422

    def test_grocy_auth_error_returns_401(self, grocy_client, mock_grocy_api):
        # GrocyAuthError (wrong API key) → HTTP 401
        mock_grocy_api.get_product.side_effect = GrocyAuthError("Invalid Grocy API key")
        response = grocy_client.get("/api/users/grocy/system-info")
        assert response.status_code == 401
        assert "Invalid Grocy API key" in response.json()["detail"]

    def test_grocy_request_error_returns_502(self, grocy_client, mock_grocy_api):
        # GrocyRequestError (network/connection issue) → HTTP 502
        mock_grocy_api.get_product.side_effect = GrocyRequestError("Connection refused")
        response = grocy_client.get("/api/users/grocy/system-info")
        assert response.status_code == 502
        assert "Error contacting Grocy" in response.json()["detail"]

    def test_generic_grocy_error_returns_502(self, grocy_client, mock_grocy_api):
        # Generic GrocyError → HTTP 502
        mock_grocy_api.get_product.side_effect = GrocyError("Unknown Grocy error")
        response = grocy_client.get("/api/users/grocy/system-info")
        assert response.status_code == 502

    def test_successful_grocy_call_returns_200(self, grocy_client, mock_grocy_api):
        # Successful Grocy call → HTTP 200
        mock_grocy_api.get_product.return_value = {"id": 10, "name": "Test Product"}
        response = grocy_client.get("/api/users/grocy/system-info")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 10
        assert data["name"] == "Test Product"

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/users/grocy/system-info")
        assert response.status_code == 401
