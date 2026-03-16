"""
Integration tests for app/services/user.py

Tests: get_by_email, get_by_username, get_by_id, create, update, authenticate
Uses real SQLite in-memory via the db fixture.
"""

import pytest

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services import user as user_service


@pytest.mark.integration
class TestGetByEmail:
    """Tests for the user lookup by email function."""

    def test_returns_user_when_email_exists(self, db, test_user):
        # Arrange & Act
        result = user_service.get_by_email(db, email="test@example.com")
        # Assert
        assert result is not None
        assert result.id == test_user.id

    def test_returns_none_when_email_not_found(self, db):
        result = user_service.get_by_email(db, email="nonexistent@example.com")
        assert result is None

    def test_case_sensitive_email_lookup(self, db, test_user):
        # Email is stored as-is; uppercase does not match
        result = user_service.get_by_email(db, email="TEST@EXAMPLE.COM")
        assert result is None

    def test_returns_correct_user_among_multiple(self, db, test_user):
        # Create a second user
        other = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash("password"),
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        result = user_service.get_by_email(db, email="test@example.com")
        assert result is not None
        assert result.id == test_user.id
        assert result.email == "test@example.com"


@pytest.mark.integration
class TestGetByUsername:
    """Tests for the user lookup by username function."""

    def test_returns_user_when_username_exists(self, db, test_user):
        result = user_service.get_by_username(db, username="testuser")
        assert result is not None
        assert result.email == "test@example.com"

    def test_returns_none_when_username_not_found(self, db):
        result = user_service.get_by_username(db, username="nobody")
        assert result is None

    def test_case_sensitive_username_lookup(self, db, test_user):
        result = user_service.get_by_username(db, username="TESTUSER")
        assert result is None

    def test_returns_correct_user_by_username(self, db, test_user):
        result = user_service.get_by_username(db, username="testuser")
        assert result.id == test_user.id


@pytest.mark.integration
class TestGetById:
    """Tests for the user lookup by ID function."""

    def test_returns_user_when_id_exists(self, db, test_user):
        result = user_service.get_by_id(db, user_id=test_user.id)
        assert result is not None
        assert result.username == "testuser"

    def test_returns_none_when_id_not_found(self, db):
        result = user_service.get_by_id(db, user_id=99999)
        assert result is None

    def test_returns_correct_user_by_id(self, db, test_user):
        result = user_service.get_by_id(db, user_id=test_user.id)
        assert result.email == "test@example.com"
        assert result.username == "testuser"


@pytest.mark.integration
class TestCreate:
    """Tests for the user creation function."""

    def test_creates_user_and_returns_user_object(self, db):
        # Arrange
        user_in = UserCreate(
            email="new@example.com",
            username="newuser",
            password="Secure@password123",
        )
        # Act
        user = user_service.create(db, user_in=user_in)
        # Assert
        assert user is not None
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.username == "newuser"

    def test_password_is_stored_as_hash_not_plaintext(self, db):
        user_in = UserCreate(
            email="hash@example.com",
            username="hashuser",
            password="Secure@password123",
        )
        user = user_service.create(db, user_in=user_in)
        # Password is not stored in plaintext
        assert user.hashed_password != "Secure@password123"
        assert user.hashed_password.startswith("$2b$")

    def test_created_password_is_verifiable(self, db):
        user_in = UserCreate(
            email="verify@example.com",
            username="verifyuser",
            password="My@password456",
        )
        user = user_service.create(db, user_in=user_in)
        assert verify_password("My@password456", user.hashed_password) is True

    def test_created_user_is_active_by_default(self, db):
        user_in = UserCreate(
            email="active@example.com",
            username="activeuser",
            password="Password@12345",
        )
        user = user_service.create(db, user_in=user_in)
        assert user.is_active is True

    def test_created_user_is_persisted_in_db(self, db):
        user_in = UserCreate(
            email="persist@example.com",
            username="persistuser",
            password="Password@12345",
        )
        user = user_service.create(db, user_in=user_in)
        # Verify that the user is persisted in the DB
        found = user_service.get_by_id(db, user_id=user.id)
        assert found is not None
        assert found.email == "persist@example.com"


@pytest.mark.integration
class TestUpdate:
    """Tests for the user update function."""

    def test_updates_email_field(self, db, test_user):
        user_in = UserUpdate(email="updated@example.com")
        updated = user_service.update(db, db_user=test_user, user_in=user_in)
        assert updated.email == "updated@example.com"

    def test_updates_username_field(self, db, test_user):
        user_in = UserUpdate(username="updateduser")
        updated = user_service.update(db, db_user=test_user, user_in=user_in)
        assert updated.username == "updateduser"

    def test_updates_password_with_new_hash(self, db, test_user):
        user_in = UserUpdate(password="New@password456")
        updated = user_service.update(db, db_user=test_user, user_in=user_in)
        # New password is hashed
        assert verify_password("New@password456", updated.hashed_password) is True

    def test_old_password_invalid_after_update(self, db, test_user):
        user_in = UserUpdate(password="New@password456")
        updated = user_service.update(db, db_user=test_user, user_in=user_in)
        # Old password no longer works
        assert verify_password("testpassword123", updated.hashed_password) is False

    def test_partial_update_does_not_clear_other_fields(self, db, test_user):
        # Save the original email
        original_email = test_user.email
        user_in = UserUpdate(username="partialupdated")
        updated = user_service.update(db, db_user=test_user, user_in=user_in)
        # Email was not changed
        assert updated.email == original_email

    def test_update_with_none_password_does_not_change_hash(self, db, test_user):
        # Update with password=None does not change the password hash
        original_hash = test_user.hashed_password
        user_in = UserUpdate(email="newemail@example.com")
        updated = user_service.update(db, db_user=test_user, user_in=user_in)
        assert updated.hashed_password == original_hash


@pytest.mark.integration
class TestAuthenticate:
    """Tests for the user authentication function."""

    def test_valid_credentials_returns_user(self, db, test_user):
        # Arrange & Act
        result = user_service.authenticate(db, username="testuser", password="testpassword123")
        # Assert
        assert result is not None
        assert result.id == test_user.id

    def test_wrong_password_returns_none(self, db, test_user):
        result = user_service.authenticate(db, username="testuser", password="wrongpassword")
        assert result is None

    def test_unknown_username_returns_none(self, db):
        result = user_service.authenticate(db, username="nobody", password="anything")
        assert result is None

    def test_authenticate_is_case_sensitive_for_password(self, db, test_user):
        # Password is case-sensitive
        result = user_service.authenticate(db, username="testuser", password="TESTPASSWORD123")
        assert result is None

    def test_authenticate_is_case_sensitive_for_username(self, db, test_user):
        # Username is case-sensitive
        result = user_service.authenticate(db, username="TESTUSER", password="testpassword123")
        assert result is None

    def test_authenticate_inactive_user_returns_user_object(self, db):
        # authenticate returns an object even for inactive users
        # (is_active check happens in the endpoint, not in the service)
        inactive = User(
            email="inactive@example.com",
            username="inactiveauth",
            hashed_password=get_password_hash("password123"),
            is_active=False,
        )
        db.add(inactive)
        db.commit()

        result = user_service.authenticate(db, username="inactiveauth", password="password123")
        # Service returns the user; activity check is in the endpoint
        assert result is not None
