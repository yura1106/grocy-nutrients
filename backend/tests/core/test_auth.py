"""
Integration tests for app/core/auth.py

Tests: get_current_user (cookie-based) and get_grocy_api dependencies via TestClient.
Uses real SQLite in-memory and genuine JWT logic.
"""

from datetime import timedelta

import pytest

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import User


def _set_cookie(client, token: str) -> None:
    client.cookies.set(settings.access_cookie_name, token)


@pytest.mark.integration
class TestGetCurrentUserDependency:
    """
    Tests for the get_current_user dependency.
    The GET /api/users/me endpoint uses this dependency end-to-end.
    """

    def test_valid_token_via_override_returns_200(self, client):
        # The client fixture overrides get_current_user with test_user
        response = client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_missing_cookie_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 401

    def test_invalid_jwt_in_cookie_returns_401(self, unauthenticated_client):
        _set_cookie(unauthenticated_client, "not-a-valid-jwt")
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 401

    def test_expired_token_returns_401(self, unauthenticated_client, test_user):
        expired_token = create_access_token(
            subject=test_user.id,
            token_version=test_user.token_version or 0,
            expires_delta=timedelta(seconds=-1),
        )
        _set_cookie(unauthenticated_client, expired_token)
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 401

    def test_token_with_nonexistent_user_id_returns_404(self, unauthenticated_client):
        token = create_access_token(subject=99999, token_version=0)
        _set_cookie(unauthenticated_client, token)
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 404

    def test_token_for_inactive_user_returns_400(self, unauthenticated_client, db):
        inactive_user = User(
            email="inactive_auth@example.com",
            username="inactiveauthuser",
            hashed_password=get_password_hash("password123"),
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()
        db.refresh(inactive_user)

        token = create_access_token(
            subject=inactive_user.id, token_version=inactive_user.token_version or 0
        )
        _set_cookie(unauthenticated_client, token)
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 400
        assert "Inactive" in response.json()["detail"]

    def test_authorization_header_is_ignored(self, unauthenticated_client, test_user):
        # Cookie auth replaces header auth — Bearer header alone must not authenticate.
        token = create_access_token(
            subject=test_user.id, token_version=test_user.token_version or 0
        )
        response = unauthenticated_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_token_version_mismatch_returns_401(self, unauthenticated_client, test_user, db):
        # Token issued at version 0; bump user's version to simulate logout-all.
        token = create_access_token(subject=test_user.id, token_version=0)
        test_user.token_version = 1
        db.add(test_user)
        db.commit()

        _set_cookie(unauthenticated_client, token)
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()


@pytest.mark.integration
class TestGetGrocyApiDependency:
    """
    Tests for the get_grocy_api dependency.
    Verifies correct errors when household header is missing or invalid.
    Endpoint: GET /api/users/grocy/system-info
    """

    def test_missing_household_id_returns_422(self, client):
        response = client.get("/api/users/grocy/system-info")
        assert response.status_code == 422

    def test_non_member_household_returns_403(self, client):
        response = client.get(
            "/api/users/grocy/system-info",
            params={"household_id": 99999},
        )
        assert response.status_code == 403
