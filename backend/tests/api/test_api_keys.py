"""Tests for the /api/users/me/api-keys CRUD endpoints."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.household import Household
from app.models.user import User
from app.models.user_api_key import UserAPIKey

TEST_HOUSEHOLD_ID = 1  # matches conftest.test_household


def test_create_returns_plaintext_once(
    client: TestClient, db: Session, test_user: User, test_household: Household
):
    resp = client.post(
        "/api/users/me/api-keys",
        json={"name": "laptop", "household_id": TEST_HOUSEHOLD_ID},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "laptop"
    assert body["household_id"] == TEST_HOUSEHOLD_ID
    assert body["key"].startswith("gnk_")
    # The stored row must not contain the plaintext secret.
    row = db.exec(select(UserAPIKey).where(UserAPIKey.user_id == test_user.id)).first()
    assert row is not None
    assert row.household_id == TEST_HOUSEHOLD_ID
    assert row.key_hash not in body["key"]
    assert body["key_prefix"] == row.key_prefix


def test_create_rejects_non_member_household(
    client: TestClient, test_user: User, test_household: Household
):
    resp = client.post(
        "/api/users/me/api-keys",
        json={"name": "laptop", "household_id": 9999},
    )
    assert resp.status_code == 403


def test_list_excludes_secret(client: TestClient, db: Session, test_user: User):
    db.add(
        UserAPIKey(
            user_id=test_user.id,
            name="k1",
            key_prefix="abc",
            key_hash="hash",
            household_id=7,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    resp = client.get("/api/users/me/api-keys")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert "key" not in items[0]
    assert "key_hash" not in items[0]
    assert items[0]["name"] == "k1"
    assert items[0]["household_id"] == 7


def test_revoke_deletes_own_key(client: TestClient, db: Session, test_user: User):
    row = UserAPIKey(
        user_id=test_user.id,
        name="k",
        key_prefix="abc",
        key_hash="hash",
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    resp = client.delete(f"/api/users/me/api-keys/{row.id}")
    assert resp.status_code == 204
    assert db.get(UserAPIKey, row.id) is None


def test_revoke_other_users_key_is_404(client: TestClient, db: Session, test_user: User):
    other = User(
        email="other@example.com",
        username="other",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    row = UserAPIKey(
        user_id=other.id,
        name="k",
        key_prefix="xyz",
        key_hash="hash",
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    resp = client.delete(f"/api/users/me/api-keys/{row.id}")
    assert resp.status_code == 404
    # The other user's key must still exist.
    assert db.get(UserAPIKey, row.id) is not None
