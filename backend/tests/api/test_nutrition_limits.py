"""Integration tests for /api/nutrition-limits endpoints."""

from datetime import UTC, date, datetime

import pytest
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models.nutrition_limit import DailyNutritionLimit
from app.models.user import User
from app.models.user_health_profile import UserHealthProfile


def make_limit(db: Session, user_id: int, d: date, **kwargs) -> DailyNutritionLimit:
    record = DailyNutritionLimit(
        user_id=user_id,
        date=d,
        calories=2000.0,
        proteins=150.0,
        carbohydrates=200.0,
        carbohydrates_of_sugars=50.0,
        fats=67.0,
        fats_saturated=22.0,
        salt=5.0,
        fibers=28.0,
        **kwargs,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@pytest.mark.integration
class TestPreviewLimits:
    def test_returns_preview_for_maintain_goal(self, client, db, test_user):
        profile = UserHealthProfile(
            user_id=test_user.id, goal="maintain", calorie_deficit_percent=15.0
        )
        db.add(profile)
        db.commit()

        response = client.post(
            "/api/nutrition-limits/preview",
            json={"calories_burned": 2000.0, "body_weight": 75.0, "activity_level": "sedentary"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["calories"] == pytest.approx(2000.0)
        assert "proteins" in data
        assert "carbohydrates" in data

    def test_defaults_to_maintain_when_no_profile(self, client):
        response = client.post(
            "/api/nutrition-limits/preview",
            json={"calories_burned": 2000.0, "body_weight": 75.0, "activity_level": "sedentary"},
        )
        assert response.status_code == 200
        assert response.json()["calories"] == pytest.approx(2000.0)

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/nutrition-limits/preview",
            json={"calories_burned": 2000.0, "body_weight": 75.0, "activity_level": "sedentary"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestCreateLimit:
    def test_creates_record_with_user_id_from_token(self, client, test_user):
        payload = {
            "date": "2026-03-27",
            "calories_burned": 2500.0,
            "body_weight": 80.0,
            "activity_level": "moderately_active",
            "calories": 2125.0,
            "proteins": 148.0,
            "carbohydrates": 250.0,
            "carbohydrates_of_sugars": 53.0,
            "fats": 59.0,
            "fats_saturated": 23.6,
            "salt": 5.5,
            "fibers": 29.75,
        }
        response = client.post("/api/nutrition-limits", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["date"] == "2026-03-27"
        assert data["calories"] == pytest.approx(2125.0)
        assert "id" in data

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/nutrition-limits",
            json={"date": "2026-03-27", "calories": 2000.0},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestGetTodayLimit:
    def test_returns_null_when_no_record(self, client):
        response = client.get("/api/nutrition-limits/today", params={"today": "2026-03-27"})
        assert response.status_code == 200
        assert response.json() is None

    def test_returns_todays_record(self, client, db, test_user):
        make_limit(db, test_user.id, date(2026, 3, 27))
        response = client.get("/api/nutrition-limits/today", params={"today": "2026-03-27"})
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-03-27"
        assert data["calories"] == pytest.approx(2000.0)


@pytest.mark.integration
class TestUpdateLimit:
    def test_updates_fields(self, client, db, test_user):
        record = make_limit(db, test_user.id, date(2026, 3, 27))
        response = client.put(
            f"/api/nutrition-limits/{record.id}",
            json={"calories": 1800.0},
        )
        assert response.status_code == 200
        assert response.json()["calories"] == pytest.approx(1800.0)

    def test_returns_403_for_another_users_record(self, client, db):
        other = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash("Pass1234!"),
            created_at=datetime.now(UTC),
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        record = make_limit(db, other.id, date(2026, 3, 27))
        response = client.put(f"/api/nutrition-limits/{record.id}", json={"calories": 999.0})
        assert response.status_code == 403


@pytest.mark.integration
class TestDeleteLimit:
    def test_returns_204_on_success(self, client, db, test_user):
        record = make_limit(db, test_user.id, date(2026, 3, 27))
        response = client.delete(f"/api/nutrition-limits/{record.id}")
        assert response.status_code == 204

    def test_returns_403_for_another_users_record(self, client, db):
        other = User(
            email="other2@example.com",
            username="otheruser2",
            hashed_password=get_password_hash("Pass1234!"),
            created_at=datetime.now(UTC),
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        record = make_limit(db, other.id, date(2026, 3, 20))
        response = client.delete(f"/api/nutrition-limits/{record.id}")
        assert response.status_code == 403
