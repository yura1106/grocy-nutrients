"""Tests for API-key generation, parsing, and the authenticate_api_key path."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.core.auth import authenticate_api_key
from app.core.security import generate_api_key, parse_api_key
from app.models.user import User
from app.models.user_api_key import UserAPIKey


@pytest.fixture()
def api_key_user(db: Session) -> User:
    user = User(
        email="keyuser@example.com",
        username="keyuser",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _store_key(db: Session, user_id: int, **overrides) -> str:
    """Mint a key, persist it for the user, return the plaintext."""
    full_key, prefix, key_hash = generate_api_key()
    row = UserAPIKey(
        user_id=user_id,
        name="test",
        key_prefix=prefix,
        key_hash=key_hash,
        created_at=datetime.now(UTC),
        **overrides,
    )
    db.add(row)
    db.commit()
    return full_key


def test_generate_and_parse_roundtrip():
    full_key, prefix, _key_hash = generate_api_key()
    assert full_key.startswith("gnk_")
    parsed = parse_api_key(full_key)
    assert parsed is not None
    assert parsed[0] == prefix


@pytest.mark.parametrize("bad", ["", "gnk_", "gnk_onlyprefix", "nope_a_b", "a_b"])
def test_parse_rejects_malformed(bad: str):
    assert parse_api_key(bad) is None


def test_authenticate_valid_key(db: Session, api_key_user: User):
    full_key = _store_key(db, api_key_user.id)
    user, household_id = authenticate_api_key(full_key, db)
    assert user.id == api_key_user.id
    # Legacy key (no household bound) — auth still returns the user; MCP rejects None.
    assert household_id is None


def test_authenticate_returns_bound_household(db: Session, api_key_user: User):
    full_key = _store_key(db, api_key_user.id, household_id=42)
    user, household_id = authenticate_api_key(full_key, db)
    assert user.id == api_key_user.id
    assert household_id == 42


def test_authenticate_unknown_prefix_is_401(db: Session):
    with pytest.raises(HTTPException) as exc:
        authenticate_api_key("gnk_doesnotexist_secret", db)
    assert exc.value.status_code == 401


def test_authenticate_wrong_secret_is_401(db: Session, api_key_user: User):
    _store_key(db, api_key_user.id)
    # Right prefix is unknown to us; forge a key with a random prefix+secret.
    with pytest.raises(HTTPException) as exc:
        authenticate_api_key("gnk_someprefix_wrongsecret", db)
    assert exc.value.status_code == 401


def test_authenticate_malformed_is_401(db: Session):
    with pytest.raises(HTTPException) as exc:
        authenticate_api_key("not-a-valid-key", db)
    assert exc.value.status_code == 401


def test_authenticate_expired_is_401(db: Session, api_key_user: User):
    full_key = _store_key(db, api_key_user.id, expires_at=datetime.now(UTC) - timedelta(days=1))
    with pytest.raises(HTTPException) as exc:
        authenticate_api_key(full_key, db)
    assert exc.value.status_code == 401


def test_authenticate_inactive_user_is_401(db: Session, api_key_user: User):
    full_key = _store_key(db, api_key_user.id)
    api_key_user.is_active = False
    db.add(api_key_user)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        authenticate_api_key(full_key, db)
    assert exc.value.status_code == 401
