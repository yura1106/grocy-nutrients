"""Tests for create_household seeding HouseholdGrocyMapping rows and the
MissingHouseholdSetting -> 422 exception handler shape.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.grocy_mapping_keys import GrocyMappingKey, MissingHouseholdSetting
from app.main import app
from app.models.household import Household, HouseholdGrocyMapping
from app.schemas.household import HouseholdCreate
from app.services.household import create_household


def _query(db: Session, statement):
    return list(db.exec(statement).all())


def _query_one(db: Session, statement):
    return db.exec(statement).first()


class TestCreateHouseholdSeedsMapping:
    def test_creates_three_mapping_rows(self, db: Session, test_user):
        with patch.dict(
            os.environ,
            {"GROCY_GRAM_UNIT_ID": "", "GROCY_ML_UNIT_ID": "", "GROCY_PORTION_UNIT_ID": ""},
            clear=False,
        ):
            create_household(
                db, HouseholdCreate(name="Seeded Home"), creator_id=test_user.id
            )

        h = _query_one(db, select(Household).where(Household.name == "Seeded Home"))
        assert h is not None

        rows = _query(
            db,
            select(HouseholdGrocyMapping).where(
                HouseholdGrocyMapping.household_id == h.id
            ),
        )
        keys = {r.key for r in rows}
        assert keys == {"gram_unit_id", "ml_unit_id", "portion_unit_id"}
        # No env fallback set → all NULL.
        assert all(r.value is None for r in rows)

    def test_uses_env_fallback_when_set(self, db: Session, test_user):
        with patch.dict(
            os.environ,
            {
                "GROCY_GRAM_UNIT_ID": "82",
                "GROCY_ML_UNIT_ID": "85",
                "GROCY_PORTION_UNIT_ID": "9",
            },
            clear=False,
        ):
            create_household(
                db, HouseholdCreate(name="Env Home"), creator_id=test_user.id
            )

        h = _query_one(db, select(Household).where(Household.name == "Env Home"))
        rows = _query(
            db,
            select(HouseholdGrocyMapping).where(
                HouseholdGrocyMapping.household_id == h.id
            ),
        )
        by_key = {r.key: r.value for r in rows}
        assert by_key["gram_unit_id"] == "82"
        assert by_key["ml_unit_id"] == "85"
        assert by_key["portion_unit_id"] == "9"

    def test_via_post_endpoint(self, client):
        response = client.post(
            "/api/households",
            json={"name": "API Home", "grocy_url": None, "address": None},
        )
        assert response.status_code == 200


class TestMissingHouseholdSettingHandler:
    """The exception handler in main.py converts MissingHouseholdSetting into
    a 422 with a structured body. The frontend's axios interceptor depends on
    that exact shape — guard it.
    """

    @pytest.fixture(autouse=True)
    def register_test_route(self):
        @app.get("/__test__/missing-setting/{key}")
        def _raise_missing(key: str):
            raise MissingHouseholdSetting(key)

        yield

        app.routes[:] = [
            r
            for r in app.routes
            if getattr(r, "path", None) != "/__test__/missing-setting/{key}"
        ]

    def test_returns_422_with_code_and_key(self):
        with TestClient(app) as c:
            c.headers.update({"Origin": "http://localhost:5173"})
            response = c.get("/__test__/missing-setting/gram_unit_id")
        assert response.status_code == 422
        body = response.json()
        assert body == {"code": "missing_household_setting", "key": "gram_unit_id"}

    def test_works_for_any_key(self):
        with TestClient(app) as c:
            c.headers.update({"Origin": "http://localhost:5173"})
            response = c.get("/__test__/missing-setting/portion_unit_id")
        assert response.status_code == 422
        assert response.json()["key"] == "portion_unit_id"

    def test_handler_covers_all_registry_keys(self):
        with TestClient(app) as c:
            c.headers.update({"Origin": "http://localhost:5173"})
            for key in GrocyMappingKey:
                response = c.get(f"/__test__/missing-setting/{key.value}")
                assert response.status_code == 422
                assert response.json() == {
                    "code": "missing_household_setting",
                    "key": key.value,
                }
