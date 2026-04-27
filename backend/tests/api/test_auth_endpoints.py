"""
Integration tests for app/api/endpoints/auth.py

Tests: register, login, refresh, logout, logout-all — all on the cookie auth flow.
"""

import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.models.user import User


@pytest.mark.integration
class TestRegisterEndpoint:
    """Tests for the new user registration endpoint."""

    def test_register_new_user_returns_200_with_user_data(self, unauthenticated_client):
        payload = {
            "email": "newuser@example.com",
            "username": "newuser123",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
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
        assert "hashed_password" not in data
        assert "password" not in data

    def test_register_duplicate_email_returns_400(self, unauthenticated_client, test_user):
        payload = {
            "email": "test@example.com",
            "username": "differentuser",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 400

    def test_register_duplicate_username_returns_400(self, unauthenticated_client, test_user):
        payload = {
            "email": "different@example.com",
            "username": "testuser",
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
        payload = {
            "email": "shortpw@example.com",
            "username": "shortpwuser",
            "password": "short",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_non_alphanumeric_username_returns_422(self, unauthenticated_client):
        payload = {
            "email": "user@example.com",
            "username": "user-with-hyphen",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_username_too_short_returns_422(self, unauthenticated_client):
        payload = {
            "email": "ab@example.com",
            "username": "ab",
            "password": "Secure@password123",
        }
        response = unauthenticated_client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_missing_required_fields_returns_422(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/auth/register", json={})
        assert response.status_code == 422


@pytest.mark.integration
class TestLoginEndpoint:
    """Tests for the user login endpoint (sets HttpOnly cookies, returns 204)."""

    def test_valid_credentials_returns_204_and_sets_cookies(
        self, unauthenticated_client, test_user
    ):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert response.status_code == 204
        # Both auth cookies are set on the response
        assert settings.access_cookie_name in response.cookies
        assert settings.refresh_cookie_name in response.cookies
        assert response.cookies[settings.access_cookie_name]
        assert response.cookies[settings.refresh_cookie_name]

    def test_login_does_not_return_tokens_in_body(self, unauthenticated_client, test_user):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        # 204 No Content — no tokens leaked into the JSON body
        assert response.status_code == 204
        assert response.content == b""

    def test_wrong_password_returns_401(self, unauthenticated_client, test_user):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_unknown_username_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/auth/login",
            data={"username": "nosuchuser", "password": "anypassword"},
        )
        assert response.status_code == 401

    def test_inactive_user_returns_400(self, unauthenticated_client, db):
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
class TestRefreshEndpoint:
    """Tests for the refresh-token rotation flow."""

    def test_valid_refresh_returns_204_and_rotates_pair(self, unauthenticated_client, test_user):
        refresh = create_refresh_token(
            subject=test_user.id, token_version=test_user.token_version or 0
        )
        unauthenticated_client.cookies.set(settings.refresh_cookie_name, refresh)

        response = unauthenticated_client.post("/api/auth/refresh")
        assert response.status_code == 204
        # Fresh access + refresh cookies issued
        assert settings.access_cookie_name in response.cookies
        new_refresh = response.cookies.get(settings.refresh_cookie_name)
        assert new_refresh and new_refresh != refresh

    def test_missing_refresh_cookie_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/auth/refresh")
        assert response.status_code == 401

    def test_invalid_refresh_token_returns_401(self, unauthenticated_client):
        unauthenticated_client.cookies.set(settings.refresh_cookie_name, "garbage")
        response = unauthenticated_client.post("/api/auth/refresh")
        assert response.status_code == 401

    def test_refresh_reuse_returns_401_and_clears_cookies(self, unauthenticated_client, test_user):
        refresh = create_refresh_token(
            subject=test_user.id, token_version=test_user.token_version or 0
        )
        unauthenticated_client.cookies.set(settings.refresh_cookie_name, refresh)

        # First call rotates successfully.
        first = unauthenticated_client.post("/api/auth/refresh")
        assert first.status_code == 204

        # Replay the original (now-blacklisted) refresh.
        unauthenticated_client.cookies.set(settings.refresh_cookie_name, refresh)
        second = unauthenticated_client.post("/api/auth/refresh")
        assert second.status_code == 401
        # Cookies cleared on the response (Max-Age=0 / expired)
        set_cookie = second.headers.get("set-cookie", "")
        assert settings.access_cookie_name in set_cookie
        assert settings.refresh_cookie_name in set_cookie


@pytest.mark.integration
class TestLogoutEndpoint:
    """Tests for the single-session logout endpoint."""

    def test_logout_with_authenticated_user_returns_204(self, client):
        response = client.post("/api/auth/logout")
        assert response.status_code == 204

    def test_logout_without_token_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/auth/logout")
        assert response.status_code == 401


@pytest.mark.integration
class TestLogoutAllEndpoint:
    """Tests for logout-all-devices: bumps token_version, invalidates prior tokens."""

    def test_logout_all_returns_204_and_bumps_token_version(
        self, unauthenticated_client, test_user
    ):
        starting_version = test_user.token_version or 0
        access = create_access_token(subject=test_user.id, token_version=starting_version)
        unauthenticated_client.cookies.set(settings.access_cookie_name, access)

        response = unauthenticated_client.post("/api/auth/logout-all")
        assert response.status_code == 204

        # The same token now fails validation because token_version was bumped.
        unauthenticated_client.cookies.set(settings.access_cookie_name, access)
        check = unauthenticated_client.get("/api/users/me")
        assert check.status_code == 401
