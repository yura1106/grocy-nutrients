"""
Integration tests for app/core/auth.py

Tests: get_current_user and get_grocy_api dependencies via TestClient.
Uses real SQLite in-memory and genuine JWT logic.
"""
import pytest
from datetime import timedelta

from app.core.security import create_access_token, get_password_hash
from app.models.user import User


@pytest.mark.integration
class TestGetCurrentUserDependency:
    """
    Tests for the get_current_user dependency.
    The GET /api/users/me endpoint uses this dependency end-to-end.
    """

    def test_valid_token_via_override_returns_200(self, client):
        # The client fixture already overrides get_current_user with test_user
        response = client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_missing_token_returns_401(self, unauthenticated_client):
        # No Authorization header
        response = unauthenticated_client.get("/api/users/me")
        assert response.status_code == 401

    def test_invalid_jwt_token_returns_401(self, unauthenticated_client):
        # Malformed token format
        response = unauthenticated_client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(self, unauthenticated_client, test_user):
        # Expired JWT token
        expired_token = create_access_token(
            subject=test_user.id,
            expires_delta=timedelta(seconds=-1),
        )
        response = unauthenticated_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_token_with_nonexistent_user_id_returns_404(self, unauthenticated_client):
        # Token with a non-existent user ID
        token = create_access_token(subject=99999)
        response = unauthenticated_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_token_for_inactive_user_returns_400(self, unauthenticated_client, db):
        # Inactive user cannot authenticate
        inactive_user = User(
            email="inactive_auth@example.com",
            username="inactiveauthuser",
            hashed_password=get_password_hash("password123"),
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()
        db.refresh(inactive_user)

        token = create_access_token(subject=inactive_user.id)
        response = unauthenticated_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "Inactive" in response.json()["detail"]

    def test_wrong_bearer_scheme_returns_401(self, unauthenticated_client, test_user):
        # Wrong authentication scheme
        token = create_access_token(subject=test_user.id)
        response = unauthenticated_client.get(
            "/api/users/me",
            headers={"Authorization": f"Token {token}"},  # "Token" instead of "Bearer"
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestGetGrocyApiDependency:
    """
    Tests for the get_grocy_api dependency.
    Verifies that HTTP 400 is returned when grocy is not configured.
    Endpoint: GET /api/users/grocy/system-info
    """

    def test_user_without_grocy_api_key_returns_400(self, client):
        # client uses test_user which has no grocy_api_key
        response = client.get("/api/users/grocy/system-info")
        assert response.status_code == 400
        assert "Grocy API key not configured" in response.json()["detail"]

    def test_error_message_includes_profile_hint(self, client):
        # The error message should hint where to configure the key
        response = client.get("/api/users/grocy/system-info")
        detail = response.json()["detail"]
        assert "profile" in detail.lower()
