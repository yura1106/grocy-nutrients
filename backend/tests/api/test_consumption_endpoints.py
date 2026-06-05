"""
Integration tests for app/api/endpoints/consumption.py

Tests for all 8 consumption endpoints with real SQLite + mocked GrocyAPI.
"""

from datetime import date
from unittest.mock import patch

import pytest

from app.models.product import (
    ConsumedProduct,
    MealPlanConsumption,
    NoteNutrients,
    Product,
    ProductData,
)
from app.models.recipe import Recipe
from app.services.consumption import ConsumptionError
from tests.conftest import TEST_HOUSEHOLD_ID

HID = TEST_HOUSEHOLD_ID


@pytest.mark.integration
class TestConsumptionHistoryEndpoint:
    """Tests for the GET /api/consumption/history endpoint."""

    def test_empty_history_returns_empty_items_and_zero_total(self, client, test_household):
        response = client.get("/api/consumption/history", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_history_with_records_returns_correct_count(
        self, client, db, test_user, test_household
    ):
        record = MealPlanConsumption(
            date=date(2024, 1, 15),
            meal_plan_id=101,
            recipe_grocy_id=5,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_history_item_contains_expected_fields(self, client, db, test_user, test_household):
        record = MealPlanConsumption(
            date=date(2024, 2, 20),
            meal_plan_id=202,
            recipe_grocy_id=7,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history", params={"household_id": HID})
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "id" in item
        assert "date" in item
        assert "meal_plan_id" in item
        assert "recipe_grocy_id" in item
        assert item["meal_plan_id"] == 202

    def test_history_pagination_with_limit(self, client, db, test_user, test_household):
        for i in range(5):
            db.add(
                MealPlanConsumption(
                    date=date(2024, 1, i + 1),
                    meal_plan_id=200 + i,
                    recipe_grocy_id=1,
                    household_id=HID,
                    user_id=test_user.id,
                )
            )
        db.commit()

        response = client.get(
            "/api/consumption/history", params={"household_id": HID, "skip": 0, "limit": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_history_pagination_with_skip(self, client, db, test_user, test_household):
        for i in range(5):
            db.add(
                MealPlanConsumption(
                    date=date(2024, 3, i + 1),
                    meal_plan_id=300 + i,
                    recipe_grocy_id=1,
                    household_id=HID,
                    user_id=test_user.id,
                )
            )
        db.commit()

        response = client.get(
            "/api/consumption/history", params={"household_id": HID, "skip": 3, "limit": 50}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2  # 5 - 3 = 2

    def test_history_recipe_name_from_local_recipes_table(
        self, client, db, test_user, test_household
    ):
        recipe = Recipe(grocy_id=99, name="Test Recipe Name", household_id=HID)
        db.add(recipe)
        db.commit()

        record = MealPlanConsumption(
            date=date(2024, 4, 1),
            meal_plan_id=401,
            recipe_grocy_id=99,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history", params={"household_id": HID})
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["recipe_name"] == "Test Recipe Name"

    def test_history_fallback_recipe_name_when_not_in_db(
        self, client, db, test_user, test_household
    ):
        record = MealPlanConsumption(
            date=date(2024, 5, 1),
            meal_plan_id=501,
            recipe_grocy_id=9999,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history", params={"household_id": HID})
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["recipe_name"] == "Recipe #9999"

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get(
            "/api/consumption/history", params={"household_id": HID}
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestImportHistoryEndpoint:
    """Tests for the POST /api/consumption/import-history endpoint."""

    def test_import_new_records_returns_correct_counts(self, client, test_household):
        payload = {
            "rows": [
                {"meal_plan_id": 301, "recipe_id": 10, "day": "2024-03-01"},
                {"meal_plan_id": 302, "recipe_id": 11, "day": "2024-03-02"},
            ]
        }
        response = client.post(
            "/api/consumption/import-history", json=payload, params={"household_id": HID}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0

    def test_import_skips_duplicate_meal_plan_ids(self, client, db, test_user, test_household):
        existing = MealPlanConsumption(
            date=date(2024, 3, 1),
            meal_plan_id=401,
            recipe_grocy_id=10,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(existing)
        db.commit()

        payload = {
            "rows": [
                {"meal_plan_id": 401, "recipe_id": 10, "day": "2024-03-01"},
                {"meal_plan_id": 402, "recipe_id": 11, "day": "2024-03-02"},
            ]
        }
        response = client.post(
            "/api/consumption/import-history", json=payload, params={"household_id": HID}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_import_skips_invalid_date_format(self, client, test_household):
        payload = {
            "rows": [
                {"meal_plan_id": 501, "recipe_id": 1, "day": "not-a-date"},
            ]
        }
        response = client.post(
            "/api/consumption/import-history", json=payload, params={"household_id": HID}
        )
        assert response.status_code == 200
        assert response.json()["skipped"] == 1
        assert response.json()["imported"] == 0

    def test_import_empty_rows_returns_zero_counts(self, client, test_household):
        payload = {"rows": []}
        response = client.post(
            "/api/consumption/import-history", json=payload, params={"household_id": HID}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 0
        assert data["skipped"] == 0

    def test_import_returns_descriptive_message(self, client, test_household):
        payload = {
            "rows": [
                {"meal_plan_id": 601, "recipe_id": 1, "day": "2024-06-01"},
            ]
        }
        response = client.post(
            "/api/consumption/import-history", json=payload, params={"household_id": HID}
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/import-history",
            json={"rows": []},
            params={"household_id": HID},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestConsumedStatsEndpoint:
    """Tests for the GET /api/consumption/stats endpoint."""

    def test_empty_stats_returns_empty_days_and_zero_total(self, client, test_household):
        response = client.get("/api/consumption/stats", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == []
        assert data["total"] == 0

    def test_stats_with_consumed_product_returns_correct_day(
        self, client, db, test_user, test_household
    ):
        product = Product(
            grocy_id=1, name="Chicken", product_group_id=1, active=True, household_id=HID
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        product_data = ProductData(
            product_id=product.id,
            calories=200.0,
            proteins=30.0,
            carbohydrates=0.0,
            fats=10.0,
        )
        db.add(product_data)
        db.commit()
        db.refresh(product_data)

        consumed = ConsumedProduct(
            product_data_id=product_data.id,
            date=date(2024, 3, 1),
            quantity=1.0,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(consumed)
        db.commit()

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["days"]) >= 1

    def test_stats_calculates_calories_correctly(self, client, db, test_user, test_household):
        product = Product(
            grocy_id=2, name="Rice", product_group_id=1, active=True, household_id=HID
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        product_data = ProductData(
            product_id=product.id,
            calories=100.0,
            proteins=0.0,
            carbohydrates=0.0,
            fats=0.0,
        )
        db.add(product_data)
        db.commit()
        db.refresh(product_data)

        consumed = ConsumedProduct(
            product_data_id=product_data.id,
            date=date(2024, 5, 15),
            quantity=2.0,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(consumed)
        db.commit()

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        assert response.status_code == 200
        days = response.json()["days"]
        may_day = next((d for d in days if d["date"] == "2024-05-15"), None)
        assert may_day is not None
        assert may_day["total_calories"] == 200.0

    def test_stats_includes_note_nutrients(self, client, db, test_user, test_household):
        note = NoteNutrients(
            date=date(2024, 7, 10),
            note="Protein shake",
            calories=200.0,
            proteins=30.0,
            carbohydrates=10.0,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(note)
        db.commit()

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        assert response.status_code == 200
        days = response.json()["days"]
        july_day = next((d for d in days if d["date"] == "2024-07-10"), None)
        assert july_day is not None
        assert july_day["total_calories"] == 200.0

    def test_stats_pagination_limit(self, client, test_household):
        response = client.get("/api/consumption/stats", params={"household_id": HID, "limit": 5})
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get(
            "/api/consumption/stats", params={"household_id": HID}
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestConsumedDayDetailEndpoint:
    """Tests for the GET /api/consumption/stats/{date} endpoint."""

    def test_valid_date_with_no_data_returns_empty_response(self, client, test_household):
        response = client.get("/api/consumption/stats/2024-01-01", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2024-01-01"
        assert data["products"] == []
        assert data["notes"] == []
        assert data["total_calories"] == 0.0

    def test_invalid_date_format_returns_400(self, client, test_household):
        response = client.get("/api/consumption/stats/not-a-date", params={"household_id": HID})
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_day_detail_includes_correct_product_totals(
        self, client, db, test_user, test_household
    ):
        product = Product(
            grocy_id=10, name="Detail Product", product_group_id=1, active=True, household_id=HID
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        product_data = ProductData(
            product_id=product.id,
            calories=50.0,
            proteins=5.0,
            carbohydrates=10.0,
            fats=2.0,
        )
        db.add(product_data)
        db.commit()
        db.refresh(product_data)

        consumed = ConsumedProduct(
            product_data_id=product_data.id,
            date=date(2024, 5, 10),
            quantity=3.0,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(consumed)
        db.commit()

        response = client.get("/api/consumption/stats/2024-05-10", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 1
        assert data["total_calories"] == 150.0
        assert data["products"][0]["product_name"] == "Detail Product"
        assert data["products"][0]["quantity"] == 3.0

    def test_day_detail_includes_notes(self, client, db, test_user, test_household):
        note = NoteNutrients(
            date=date(2024, 8, 20),
            note="Coffee",
            calories=50.0,
            proteins=0.5,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(note)
        db.commit()

        response = client.get("/api/consumption/stats/2024-08-20", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 1
        assert data["notes"][0]["note"] == "Coffee"
        assert data["total_calories"] == 50.0

    def test_day_detail_aggregates_products_and_notes(self, client, db, test_user, test_household):
        product = Product(
            grocy_id=20, name="Agg Product", product_group_id=1, active=True, household_id=HID
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        product_data = ProductData(
            product_id=product.id,
            calories=100.0,
            proteins=0.0,
            carbohydrates=0.0,
            fats=0.0,
        )
        db.add(product_data)
        db.commit()
        db.refresh(product_data)

        consumed = ConsumedProduct(
            product_data_id=product_data.id,
            date=date(2024, 9, 5),
            quantity=1.0,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(consumed)

        note = NoteNutrients(
            date=date(2024, 9, 5),
            note="Extra",
            calories=50.0,
            household_id=HID,
            user_id=test_user.id,
        )
        db.add(note)
        db.commit()

        response = client.get("/api/consumption/stats/2024-09-05", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        assert data["total_calories"] == 150.0

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get(
            "/api/consumption/stats/2024-01-01", params={"household_id": HID}
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestConsumptionCheckEndpoint:
    """Tests for the POST /api/consumption/check endpoint."""

    def test_valid_date_with_mocked_service_returns_200(self, grocy_client):
        mock_result = {
            "status": "success",
            "products_to_consume": {},
            "products_to_buy": {},
            "products_to_buy_detailed": [],
            "products_to_consume_detailed": [],
            "message": "All products available",
        }
        with patch(
            "app.api.endpoints.consumption.check_products_availability",
            return_value=mock_result,
        ):
            response = grocy_client.post(
                "/api/consumption/check",
                json={"date": "2024-03-01"},
                params={"household_id": HID},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_value_error_from_service_returns_400(self, grocy_client):
        def raise_value_error(*args, **kwargs):
            raise ValueError("No meal plan found for date")

        with patch(
            "app.api.endpoints.consumption.check_products_availability",
            side_effect=raise_value_error,
        ):
            response = grocy_client.post(
                "/api/consumption/check",
                json={"date": "2024-03-01"},
                params={"household_id": HID},
            )
        assert response.status_code == 400
        assert "No meal plan found" in response.json()["detail"]

    def test_consumption_error_from_service_returns_500(self, grocy_client):
        def raise_consumption_error(*args, **kwargs):
            raise ConsumptionError("Internal consumption error")

        with patch(
            "app.api.endpoints.consumption.check_products_availability",
            side_effect=raise_consumption_error,
        ):
            response = grocy_client.post(
                "/api/consumption/check",
                json={"date": "2024-03-01"},
                params={"household_id": HID},
            )
        assert response.status_code == 500

    def test_missing_date_field_returns_422(self, grocy_client):
        response = grocy_client.post(
            "/api/consumption/check", json={}, params={"household_id": HID}
        )
        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/check",
            json={"date": "2024-03-01"},
            params={"household_id": HID},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestDryRunEndpoint:
    """Tests for the POST /api/consumption/dry-run endpoint."""

    def test_dry_run_with_mocked_service_returns_200(self, grocy_client):
        mock_result = {
            "status": "success",
            "date": "2024-03-01",
            "meals": [],
            "total_calories": 0.0,
            "total_nutrients": {},
            "products_count": 0,
        }
        with patch(
            "app.api.endpoints.consumption.dry_run_consumption",
            return_value=mock_result,
        ):
            response = grocy_client.post(
                "/api/consumption/dry-run",
                json={"date": "2024-03-01"},
                params={"household_id": HID},
            )
        assert response.status_code == 200

    def test_dry_run_value_error_returns_400(self, grocy_client):
        def raise_value_error(*args, **kwargs):
            raise ValueError("No products for date")

        with patch(
            "app.api.endpoints.consumption.dry_run_consumption",
            side_effect=raise_value_error,
        ):
            response = grocy_client.post(
                "/api/consumption/dry-run",
                json={"date": "2024-03-01"},
                params={"household_id": HID},
            )
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/dry-run",
            json={"date": "2024-03-01"},
            params={"household_id": HID},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestExecuteConsumptionEndpoint:
    """Tests for the POST /api/consumption/execute endpoint."""

    def test_execute_enqueues_task_and_returns_task_id(self, grocy_client):
        with patch("app.api.endpoints.consumption.execute_consumption_task") as mock_task:
            mock_task.delay.return_value.id = "fake-task-id"
            response = grocy_client.post(
                "/api/consumption/execute",
                json={"date": "2024-03-01"},
                params={"household_id": HID},
            )
        assert response.status_code == 200
        assert response.json()["task_id"] == "fake-task-id"
        assert response.json()["status"] == "queued"

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/execute",
            json={"date": "2024-03-01"},
            params={"household_id": HID},
        )
        assert response.status_code == 401


def _consume_product(
    db,
    *,
    test_user,
    grocy_id,
    sugars,
    is_fresh,
    consume_date,
    quantity=1.0,
    recipe_grocy_id=None,
    originating_recipe_grocy_id=None,
):
    """Helper: create a Product + ProductData + ConsumedProduct for a day.

    Pass ``recipe_grocy_id`` to simulate recipe-sourced consumption (fresh
    exclusion must NOT apply to it). Pass ``originating_recipe_grocy_id`` to
    simulate a product attributed to an originating sub-recipe (the bundle test
    runs against this, falling back to ``recipe_grocy_id``).
    """
    product = Product(
        grocy_id=grocy_id,
        name=f"Product {grocy_id}",
        product_group_id=1,
        active=True,
        is_fresh=is_fresh,
        household_id=HID,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    product_data = ProductData(
        product_id=product.id,
        calories=100.0,
        carbohydrates=50.0,
        carbohydrates_of_sugars=sugars,
        proteins=0.0,
        fats=0.0,
    )
    db.add(product_data)
    db.commit()
    db.refresh(product_data)

    db.add(
        ConsumedProduct(
            product_data_id=product_data.id,
            date=consume_date,
            quantity=quantity,
            recipe_grocy_id=recipe_grocy_id,
            originating_recipe_grocy_id=originating_recipe_grocy_id,
            household_id=HID,
            user_id=test_user.id,
        )
    )
    db.commit()
    return product


@pytest.mark.integration
class TestFreshSugarsExclusion:
    """Fresh products' sugars are excluded from the tracked sugar total and
    reported separately as total_fresh_sugars — in both stats read paths."""

    def test_stats_excludes_fresh_sugars_from_tracked_total(
        self, client, db, test_user, test_household
    ):
        d = date(2024, 9, 1)
        # 10g sugars fresh (banana) + 20g sugars non-fresh (cookie)
        _consume_product(
            db, test_user=test_user, grocy_id=101, sugars=10.0, is_fresh=True, consume_date=d
        )
        _consume_product(
            db, test_user=test_user, grocy_id=102, sugars=20.0, is_fresh=False, consume_date=d
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        assert response.status_code == 200
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-09-01")
        assert day["total_carbohydrates_of_sugars"] == 20.0
        assert day["total_fresh_sugars"] == 10.0
        # Carbs unaffected by freshness: both products contribute 50g each.
        assert day["total_carbohydrates"] == 100.0

    def test_stats_all_fresh_yields_zero_tracked_sugars(
        self, client, db, test_user, test_household
    ):
        d = date(2024, 9, 2)
        _consume_product(
            db, test_user=test_user, grocy_id=103, sugars=15.0, is_fresh=True, consume_date=d
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-09-02")
        assert day["total_carbohydrates_of_sugars"] == 0.0
        assert day["total_fresh_sugars"] == 15.0

    def test_day_detail_splits_fresh_sugars_and_flags_products(
        self, client, db, test_user, test_household
    ):
        d = date(2024, 9, 3)
        _consume_product(
            db,
            test_user=test_user,
            grocy_id=104,
            sugars=10.0,
            is_fresh=True,
            consume_date=d,
            quantity=2.0,
        )
        _consume_product(
            db, test_user=test_user, grocy_id=105, sugars=5.0, is_fresh=False, consume_date=d
        )

        response = client.get("/api/consumption/stats/2024-09-03", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        # fresh: 10 * 2 = 20 excluded; non-fresh: 5 * 1 = 5 tracked
        assert data["total_carbohydrates_of_sugars"] == 5.0
        assert data["total_fresh_sugars"] == 20.0
        by_grocy = {p["product_name"]: p for p in data["products"]}
        assert by_grocy["Product 104"]["is_fresh"] is True
        assert by_grocy["Product 105"]["is_fresh"] is False

    def test_stats_fresh_from_recipe_counts_toward_total(
        self, client, db, test_user, test_household
    ):
        """A fresh product consumed inside a recipe (recipe_grocy_id set) is NOT
        excluded — its sugars count toward the tracked total, not fresh sugars."""
        d = date(2024, 9, 4)
        # Same fresh product (sugars=12), once standalone and once from a recipe.
        _consume_product(
            db, test_user=test_user, grocy_id=110, sugars=12.0, is_fresh=True, consume_date=d
        )
        _consume_product(
            db,
            test_user=test_user,
            grocy_id=111,
            sugars=12.0,
            is_fresh=True,
            consume_date=d,
            recipe_grocy_id=42,
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-09-04")
        # standalone fresh excluded; recipe-sourced fresh counts toward the total
        assert day["total_fresh_sugars"] == 12.0
        assert day["total_carbohydrates_of_sugars"] == 12.0

    def test_day_detail_exposes_product_id_and_recipe_flag(
        self, client, db, test_user, test_household
    ):
        """Detail items expose product_id (PATCH target) and recipe_grocy_id so the
        UI can distinguish excluded (fresh+standalone) from recipe-sourced rows."""
        d = date(2024, 9, 5)
        standalone = _consume_product(
            db, test_user=test_user, grocy_id=120, sugars=8.0, is_fresh=True, consume_date=d
        )
        from_recipe = _consume_product(
            db,
            test_user=test_user,
            grocy_id=121,
            sugars=8.0,
            is_fresh=True,
            consume_date=d,
            recipe_grocy_id=7,
        )

        response = client.get("/api/consumption/stats/2024-09-05", params={"household_id": HID})
        assert response.status_code == 200
        data = response.json()
        by_grocy = {p["product_name"]: p for p in data["products"]}
        assert by_grocy["Product 120"]["product_id"] == standalone.id
        assert by_grocy["Product 120"]["recipe_grocy_id"] is None
        assert by_grocy["Product 121"]["product_id"] == from_recipe.id
        assert by_grocy["Product 121"]["recipe_grocy_id"] == 7
        # standalone fresh excluded (8); recipe-sourced fresh counts (8)
        assert data["total_fresh_sugars"] == 8.0
        assert data["total_carbohydrates_of_sugars"] == 8.0


def _make_bundle_recipe(db, grocy_id, *, is_bundle):
    """Helper: create a Recipe row, optionally flagged as a bundle."""
    recipe = Recipe(
        grocy_id=grocy_id,
        name=f"Recipe {grocy_id}",
        is_bundle=is_bundle,
        household_id=HID,
    )
    db.add(recipe)
    db.commit()
    return recipe


@pytest.mark.integration
class TestBundleRecipeSugarsExclusion:
    """Fresh products consumed inside a bundle recipe have their sugars excluded,
    as if eaten standalone (ADR-0001). The bundle test runs against the
    ORIGINATING sub-recipe, falling back to the top-level recipe_grocy_id."""

    def test_fresh_in_bundle_recipe_is_excluded(self, client, db, test_user, test_household):
        """Fresh product sourced from a recipe flagged is_bundle → sugars excluded."""
        d = date(2024, 10, 1)
        _make_bundle_recipe(db, 500, is_bundle=True)
        _consume_product(
            db,
            test_user=test_user,
            grocy_id=200,
            sugars=10.0,
            is_fresh=True,
            consume_date=d,
            recipe_grocy_id=500,
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-10-01")
        assert day["total_carbohydrates_of_sugars"] == 0.0
        assert day["total_fresh_sugars"] == 10.0

    def test_fresh_in_nonbundle_recipe_counts_toward_total(
        self, client, db, test_user, test_household
    ):
        """Fresh product from a non-bundle recipe is NOT excluded (regular dish)."""
        d = date(2024, 10, 2)
        _make_bundle_recipe(db, 501, is_bundle=False)
        _consume_product(
            db,
            test_user=test_user,
            grocy_id=201,
            sugars=10.0,
            is_fresh=True,
            consume_date=d,
            recipe_grocy_id=501,
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-10-02")
        assert day["total_carbohydrates_of_sugars"] == 10.0
        assert day["total_fresh_sugars"] == 0.0

    def test_originating_bundle_excludes_even_when_toplevel_is_not_bundle(
        self, client, db, test_user, test_household
    ):
        """Nested case: a bundle sub-recipe (originating_recipe_grocy_id) is the
        bundle, while the top-level recipe_grocy_id is a normal dish. Exclusion
        must follow the ORIGINATING sub-recipe."""
        d = date(2024, 10, 3)
        _make_bundle_recipe(db, 600, is_bundle=False)  # top-level dish, not a bundle
        _make_bundle_recipe(db, 601, is_bundle=True)  # nested bundle sub-recipe
        _consume_product(
            db,
            test_user=test_user,
            grocy_id=202,
            sugars=10.0,
            is_fresh=True,
            consume_date=d,
            recipe_grocy_id=600,
            originating_recipe_grocy_id=601,
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-10-03")
        assert day["total_carbohydrates_of_sugars"] == 0.0
        assert day["total_fresh_sugars"] == 10.0

    def test_originating_nonbundle_counts_even_when_toplevel_is_bundle(
        self, client, db, test_user, test_household
    ):
        """Inverse nested case: top-level is a bundle but the originating
        sub-recipe is a normal dish → NOT excluded (originating wins over top)."""
        d = date(2024, 10, 4)
        _make_bundle_recipe(db, 700, is_bundle=True)  # top-level bundle
        _make_bundle_recipe(db, 701, is_bundle=False)  # nested normal sub-recipe
        _consume_product(
            db,
            test_user=test_user,
            grocy_id=203,
            sugars=10.0,
            is_fresh=True,
            consume_date=d,
            recipe_grocy_id=700,
            originating_recipe_grocy_id=701,
        )

        response = client.get("/api/consumption/stats", params={"household_id": HID})
        day = next(d_ for d_ in response.json()["days"] if d_["date"] == "2024-10-04")
        assert day["total_carbohydrates_of_sugars"] == 10.0
        assert day["total_fresh_sugars"] == 0.0


class TestIsSugarExcluded:
    """Unit tests for _is_sugar_excluded: NULL-COALESCE semantics on the
    originating recipe id (a 0 id must not fall through to recipe_grocy_id)."""

    def test_non_fresh_never_excluded(self):
        from app.api.endpoints.consumption import _is_sugar_excluded

        assert _is_sugar_excluded(False, None, None, set()) is False

    def test_fresh_standalone_excluded(self):
        from app.api.endpoints.consumption import _is_sugar_excluded

        assert _is_sugar_excluded(True, None, None, set()) is True

    def test_fresh_from_bundle_recipe_excluded(self):
        from app.api.endpoints.consumption import _is_sugar_excluded

        assert _is_sugar_excluded(True, 500, None, {500}) is True

    def test_fresh_from_non_bundle_recipe_not_excluded(self):
        from app.api.endpoints.consumption import _is_sugar_excluded

        assert _is_sugar_excluded(True, 500, None, set()) is False

    def test_originating_overrides_top_level(self):
        from app.api.endpoints.consumption import _is_sugar_excluded

        # originating is the bundle, top-level is not → excluded
        assert _is_sugar_excluded(True, 600, 601, {601}) is True
        # originating is not a bundle, top-level is → NOT excluded
        assert _is_sugar_excluded(True, 700, 701, {700}) is False

    def test_zero_originating_id_does_not_fall_through(self):
        """NULL-COALESCE, not truthiness: originating id 0 is used as-is and must
        NOT fall back to recipe_grocy_id. (Guards the fix for the `or` bug.)"""
        from app.api.endpoints.consumption import _is_sugar_excluded

        # originating=0 (falsy but not None). bundle set has recipe_grocy_id 500.
        # With `or`, origin would wrongly become 500 → excluded. Correct: origin
        # stays 0 → not in bundle set → not excluded.
        assert _is_sugar_excluded(True, 500, 0, {500}) is False
