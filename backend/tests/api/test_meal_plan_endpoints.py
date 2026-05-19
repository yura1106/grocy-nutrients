"""Integration tests for app/api/endpoints/meal_plan.py."""

from unittest.mock import patch

import pytest

from tests.conftest import TEST_HOUSEHOLD_ID

HID = TEST_HOUSEHOLD_ID


@pytest.mark.integration
class TestPullDayEndpoint:
    """Tests for POST /api/meal-plan/pull-day."""

    def test_authenticated_pull_returns_200_with_counters_and_lines(
        self, grocy_client, test_household
    ):
        service_result = {
            "pulled": 2,
            "pulled_already_done": 1,
            "skipped_already_local": 0,
            "skipped_other_owner": 1,
            "skipped_notes": 0,
            "userfield_write_failures": 0,
            "rows": [],
        }
        with (
            patch(
                "app.api.endpoints.meal_plan.pull_grocy_day_to_local",
                return_value=service_result,
            ),
            patch(
                "app.api.endpoints.meal_plan.enrich_lines",
                return_value=[],
            ),
        ):
            response = grocy_client.post(
                "/api/meal-plan/pull-day",
                json={"day": "2026-05-19"},
                params={"household_id": HID},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["pulled"] == 2
        assert data["pulled_already_done"] == 1
        assert data["skipped_other_owner"] == 1
        assert data["skipped_already_local"] == 0
        assert data["skipped_notes"] == 0
        assert data["userfield_write_failures"] == 0
        assert data["lines"] == []

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/meal-plan/pull-day",
            json={"day": "2026-05-19"},
            params={"household_id": HID},
        )
        assert response.status_code == 401

    def test_missing_day_returns_422(self, grocy_client, test_household):
        response = grocy_client.post(
            "/api/meal-plan/pull-day",
            json={},
            params={"household_id": HID},
        )
        assert response.status_code == 422

    def test_invalid_day_format_returns_422(self, grocy_client, test_household):
        response = grocy_client.post(
            "/api/meal-plan/pull-day",
            json={"day": "not-a-date"},
            params={"household_id": HID},
        )
        assert response.status_code == 422
