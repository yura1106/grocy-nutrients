"""
Unit tests for app/core/security.py

Tests: create_access_token, verify_password, get_password_hash
No database required — pure unit tests.
"""
import pytest
from datetime import timedelta, datetime

from jose import jwt

from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings


@pytest.mark.unit
class TestGetPasswordHash:
    """Tests for the password hashing function."""

    def test_returns_hashed_string_not_plain_text(self):
        # Arrange
        password = "mypassword123"
        # Act
        hashed = get_password_hash(password)
        # Assert
        assert hashed != password
        assert isinstance(hashed, str)

    def test_returns_bcrypt_hash_format(self):
        # bcrypt hashes start with $2b$
        hashed = get_password_hash("anypassword")
        assert hashed.startswith("$2b$")

    def test_different_hashes_for_same_password(self):
        # bcrypt uses a random salt each time
        hash1 = get_password_hash("same_password")
        hash2 = get_password_hash("same_password")
        assert hash1 != hash2

    def test_hash_is_deterministically_verifiable(self):
        # The hash must be verifiable using verify_password
        password = "verifyable_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_empty_password_hashes_successfully(self):
        # Empty string is also hashed (bcrypt supports it)
        hashed = get_password_hash("")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")


@pytest.mark.unit
class TestVerifyPassword:
    """Tests for the password verification function."""

    def test_correct_password_returns_true(self):
        # Arrange
        hashed = get_password_hash("correct_password")
        # Act & Assert
        assert verify_password("correct_password", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_empty_password_against_non_empty_hash_returns_false(self):
        hashed = get_password_hash("some_password")
        assert verify_password("", hashed) is False

    def test_case_sensitive_password_comparison(self):
        # Passwords are case-sensitive
        hashed = get_password_hash("Password123")
        assert verify_password("password123", hashed) is False
        assert verify_password("PASSWORD123", hashed) is False
        assert verify_password("Password123", hashed) is True

    def test_unicode_password_verification(self):
        # Unicode password support
        password = "serhsehrserh"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False


@pytest.mark.unit
class TestCreateAccessToken:
    """Tests for the JWT token creation function."""

    def test_returns_non_empty_string(self):
        # Arrange & Act
        token = create_access_token(subject=42)
        # Assert
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_correct_subject(self):
        # subject is stored as a string in the payload
        token = create_access_token(subject=99)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "99"

    def test_token_contains_expiry_claim(self):
        token = create_access_token(subject=1)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert "exp" in payload

    def test_custom_expiry_delta_is_respected(self):
        # Token should expire in ~1 hour
        delta = timedelta(hours=1)
        before = datetime.utcnow()
        token = create_access_token(subject=1, expires_delta=delta)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        expire_ts = payload["exp"]
        # Verify the token expires no earlier than 59 minutes from now
        assert expire_ts > before.timestamp() + 59 * 60

    def test_default_expiry_uses_settings(self):
        # Without a custom delta, settings.ACCESS_TOKEN_EXPIRE_MINUTES is used
        before = datetime.utcnow()
        token = create_access_token(subject=1)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        expire_ts = payload["exp"]
        expected_min_expiry = before.timestamp() + (settings.ACCESS_TOKEN_EXPIRE_MINUTES - 1) * 60
        assert expire_ts > expected_min_expiry

    def test_subject_as_string_is_preserved(self):
        token = create_access_token(subject="user_string_id")
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "user_string_id"

    def test_integer_subject_is_converted_to_string(self):
        # Integer subject is converted to string via str()
        token = create_access_token(subject=123)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "123"

    def test_expired_token_fails_decode(self):
        # A token with an expired timestamp cannot be decoded
        expired_token = create_access_token(
            subject=1,
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception):  # ExpiredSignatureError
            jwt.decode(
                expired_token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

    def test_token_signed_with_correct_key(self):
        # A token signed with a different key cannot be decoded
        token = create_access_token(subject=1)
        with pytest.raises(Exception):  # JWTError
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.JWT_ALGORITHM])
