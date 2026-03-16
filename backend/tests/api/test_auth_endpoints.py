"""
Integration tests for app/api/endpoints/auth.py

Tests: POST /api/auth/register, POST /api/auth/login, POST /api/auth/logout
Uses unauthenticated_client (only get_db overridden) for authentication endpoints.
"""

import pytest

from app.core.security import get_password_hash
from app.models.user import User


@pytest.mark.integration
class TestRegisterEndpoint:
    """Tests for the new user registration endpoint."""

    def test_register_new_user_returns_200_with_user_data(self, unauthenticated_client):
        # Arrange
        payload = {
            "email": "newuser@example.com",
            "username": "newuser123",
            "password": "Secure@password123",
        }
        # Act
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser123"
        assert "id" in data

    def test_register_does_not_return_hashed_password(self, unauthenticated_client):
        payload = {
            "email": "nopw@example.com",
            "username": "nopwuser",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        # The password hash must not be in the response
        assert "hashed_password" not in data
        assert "password" not in data

    def test_register_duplicate_email_returns_400(self, unauthenticated_client, test_user):
        payload = {
            "email": "test@example.com",  # already used by test_user
            "username": "differentuser",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 400

    def test_register_duplicate_username_returns_400(self, unauthenticated_client, test_user):
        payload = {
            "email": "different@example.com",
            "username": "testuser",  # already used by test_user
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 400

    def test_register_invalid_email_returns_422(self, unauthenticated_client):
        payload = {
            "email": "not-an-email",
            "username": "someuser123",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_short_password_returns_422(self, unauthenticated_client):
        # Minimum password length is 8 characters
        payload = {
            "email": "shortpw@example.com",
            "username": "shortpwuser",
            "password": "short",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_non_alphanumeric_username_returns_422(self, unauthenticated_client):
        # Username must be alphanumeric (validator check)
        payload = {
            "email": "user@example.com",
            "username": "user-with-hyphen",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_username_too_short_returns_422(self, unauthenticated_client):
        # Minimum username length is 3 characters
        payload = {
            "email": "ab@example.com",
            "username": "ab",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_missing_required_fields_returns_422(self, unauthenticated_client):
        # Missing required fields
        response = unauthenticated_client.post("/api/auth/register", json={})
        assert response.status_code == 422


@pytest.mark.integration
class TestLoginEndpoint:
    """Tests for the user login endpoint (OAuth2 password flow)."""

    def test_valid_credentials_returns_access_token(self, unauthenticated_client, test_user):
        # Login uses form data (OAuth2 password flow)
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 0

    def test_valid_login_returns_bearer_token_type(self, unauthenticated_client, test_user):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, unauthenticated_client, test_user):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_wrong_password_returns_www_authenticate_header(
        self, unauthenticated_client, test_user
    ):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_unknown_username_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "nosuchuser", "password": "anypassword"},
        )
        assert response.status_code == 401

    def test_inactive_user_returns_400(self, unauthenticated_client, db):
        # Create an inactive user
        inactive_user = User(
            email="inactive_login@example.com",
            username="inactivelogin",
            hashed_password=get_password_hash("password123"),
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()

        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "inactivelogin", "password": "password123"},
        )
        assert response.status_code == 400
        assert "Inactive" in response.json()["detail"]

    def test_login_with_json_instead_of_form_returns_422(self, unauthenticated_client, test_user):
        # Login expects form data, not JSON
        response = unauthenticated_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        assert response.status_code == 422

    def test_login_missing_password_returns_422(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestLogoutEndpoint:
    """Tests for the logout endpoint."""

    def test_logout_with_authenticated_user_returns_200(self, client):
        # The client fixture overrides get_current_user
        response = client.post("/api/auth/logout")
        assert response.status_code == 200

    def test_logout_returns_success_message(self, client):
        response = client.post("/api/auth/logout")
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    def test_logout_without_token_returns_401(self, unauthenticated_client):
        # Without token — 401
        response = unauthenticated_client.post("/api/auth/logout")
        assert response.status_code == 401
