"""
Integration tests for app/api/endpoints/consumption.py

Tests for all 8 consumption endpoints with real SQLite + mocked GrocyAPI.
"""
import pytest
from datetime import date
from unittest.mock import patch

from app.models.product import (
    ConsumedProduct,
    MealPlanConsumption,
    NoteNutrients,
    Product,
    ProductData,
)
from app.models.recipe import Recipe
from app.services.consumption import ConsumptionError


@pytest.mark.integration
class TestConsumptionHistoryEndpoint:
    """Tests for the GET /api/consumption/history endpoint."""

    def test_empty_history_returns_empty_items_and_zero_total(self, client):
        # Arrange & Act
        response = client.get("/api/consumption/history")
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_history_with_records_returns_correct_count(self, client, db):
        record = MealPlanConsumption(
            date=date(2024, 1, 15),
            meal_plan_id=101,
            recipe_grocy_id=5,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_history_item_contains_expected_fields(self, client, db):
        record = MealPlanConsumption(
            date=date(2024, 2, 20),
            meal_plan_id=202,
            recipe_grocy_id=7,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "id" in item
        assert "date" in item
        assert "meal_plan_id" in item
        assert "recipe_grocy_id" in item
        assert item["meal_plan_id"] == 202

    def test_history_pagination_with_limit(self, client, db):
        for i in range(5):
            db.add(MealPlanConsumption(
                date=date(2024, 1, i + 1),
                meal_plan_id=200 + i,
                recipe_grocy_id=1,
            ))
        db.commit()

        response = client.get("/api/consumption/history?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_history_pagination_with_skip(self, client, db):
        for i in range(5):
            db.add(MealPlanConsumption(
                date=date(2024, 3, i + 1),
                meal_plan_id=300 + i,
                recipe_grocy_id=1,
            ))
        db.commit()

        response = client.get("/api/consumption/history?skip=3&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2  # 5 - 3 = 2

    def test_history_recipe_name_from_local_recipes_table(self, client, db):
        # If the recipe is in the local table — show its name
        recipe = Recipe(grocy_id=99, name="Test Recipe Name")
        db.add(recipe)
        db.commit()

        record = MealPlanConsumption(
            date=date(2024, 4, 1),
            meal_plan_id=401,
            recipe_grocy_id=99,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["recipe_name"] == "Test Recipe Name"

    def test_history_fallback_recipe_name_when_not_in_db(self, client, db):
        # If the recipe is not found — fallback to "Recipe #<id>"
        record = MealPlanConsumption(
            date=date(2024, 5, 1),
            meal_plan_id=501,
            recipe_grocy_id=9999,  # does not exist in recipes
        )
        db.add(record)
        db.commit()

        response = client.get("/api/consumption/history")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["recipe_name"] == "Recipe #9999"

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/consumption/history")
        assert response.status_code == 401


@pytest.mark.integration
class TestImportHistoryEndpoint:
    """Tests for the POST /api/consumption/import-history endpoint."""

    def test_import_new_records_returns_correct_counts(self, client):
        payload = {
            "rows": [
                {"meal_plan_id": 301, "recipe_id": 10, "day": "2024-03-01"},
                {"meal_plan_id": 302, "recipe_id": 11, "day": "2024-03-02"},
            ]
        }
        response = client.post("/api/consumption/import-history", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0

    def test_import_skips_duplicate_meal_plan_ids(self, client, db):
        # Pre-existing record
        existing = MealPlanConsumption(
            date=date(2024, 3, 1),
            meal_plan_id=401,
            recipe_grocy_id=10,
        )
        db.add(existing)
        db.commit()

        payload = {
            "rows": [
                {"meal_plan_id": 401, "recipe_id": 10, "day": "2024-03-01"},  # duplicate
                {"meal_plan_id": 402, "recipe_id": 11, "day": "2024-03-02"},  # new
            ]
        }
        response = client.post("/api/consumption/import-history", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_import_skips_invalid_date_format(self, client):
        payload = {
            "rows": [
                {"meal_plan_id": 501, "recipe_id": 1, "day": "not-a-date"},
            ]
        }
        response = client.post("/api/consumption/import-history", json=payload)
        assert response.status_code == 200
        assert response.json()["skipped"] == 1
        assert response.json()["imported"] == 0

    def test_import_empty_rows_returns_zero_counts(self, client):
        payload = {"rows": []}
        response = client.post("/api/consumption/import-history", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 0
        assert data["skipped"] == 0

    def test_import_returns_descriptive_message(self, client):
        payload = {
            "rows": [
                {"meal_plan_id": 601, "recipe_id": 1, "day": "2024-06-01"},
            ]
        }
        response = client.post("/api/consumption/import-history", json=payload)
        assert response.status_code == 200
        assert "message" in response.json()

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/import-history",
            json={"rows": []},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestConsumedStatsEndpoint:
    """Tests for the GET /api/consumption/stats endpoint."""

    def test_empty_stats_returns_empty_days_and_zero_total(self, client):
        response = client.get("/api/consumption/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == []
        assert data["total"] == 0

    def test_stats_with_consumed_product_returns_correct_day(self, client, db):
        # Create the hierarchy: Product → ProductData → ConsumedProduct
        product = Product(grocy_id=1, name="Chicken", product_group_id=1, active=True)
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
        )
        db.add(consumed)
        db.commit()

        response = client.get("/api/consumption/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["days"]) >= 1

    def test_stats_calculates_calories_correctly(self, client, db):
        # calories per 100g = 100, quantity = 2.0 → total = 200
        product = Product(grocy_id=2, name="Rice", product_group_id=1, active=True)
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
        )
        db.add(consumed)
        db.commit()

        response = client.get("/api/consumption/stats")
        assert response.status_code == 200
        days = response.json()["days"]
        may_day = next((d for d in days if d["date"] == "2024-05-15"), None)
        assert may_day is not None
        assert may_day["total_calories"] == 200.0  # 100 * 2

    def test_stats_includes_note_nutrients(self, client, db):
        # NoteNutrients are also counted in the stats
        note = NoteNutrients(
            date=date(2024, 7, 10),
            note="Protein shake",
            calories=200.0,
            proteins=30.0,
            carbohydrates=10.0,
        )
        db.add(note)
        db.commit()

        response = client.get("/api/consumption/stats")
        assert response.status_code == 200
        days = response.json()["days"]
        july_day = next((d for d in days if d["date"] == "2024-07-10"), None)
        assert july_day is not None
        assert july_day["total_calories"] == 200.0

    def test_stats_pagination_limit(self, client, db):
        # Verify pagination — at most limit records are returned
        response = client.get("/api/consumption/stats?limit=5")
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/consumption/stats")
        assert response.status_code == 401


@pytest.mark.integration
class TestConsumedDayDetailEndpoint:
    """Tests for the GET /api/consumption/stats/{date} endpoint."""

    def test_valid_date_with_no_data_returns_empty_response(self, client):
        response = client.get("/api/consumption/stats/2024-01-01")
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2024-01-01"
        assert data["products"] == []
        assert data["notes"] == []
        assert data["total_calories"] == 0.0

    def test_invalid_date_format_returns_400(self, client):
        response = client.get("/api/consumption/stats/not-a-date")
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_day_detail_includes_correct_product_totals(self, client, db):
        # calories = 50, quantity = 3 → total_calories = 150
        product = Product(grocy_id=10, name="Detail Product", product_group_id=1, active=True)
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
        )
        db.add(consumed)
        db.commit()

        response = client.get("/api/consumption/stats/2024-05-10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 1
        assert data["total_calories"] == 150.0  # 50 * 3
        assert data["products"][0]["product_name"] == "Detail Product"
        assert data["products"][0]["quantity"] == 3.0

    def test_day_detail_includes_notes(self, client, db):
        note = NoteNutrients(
            date=date(2024, 8, 20),
            note="Coffee",
            calories=50.0,
            proteins=0.5,
        )
        db.add(note)
        db.commit()

        response = client.get("/api/consumption/stats/2024-08-20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 1
        assert data["notes"][0]["note"] == "Coffee"
        assert data["total_calories"] == 50.0

    def test_day_detail_aggregates_products_and_notes(self, client, db):
        # Product: 100 kcal, Note: 50 kcal → total 150 kcal
        product = Product(grocy_id=20, name="Agg Product", product_group_id=1, active=True)
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
        )
        db.add(consumed)

        note = NoteNutrients(
            date=date(2024, 9, 5),
            note="Extra",
            calories=50.0,
        )
        db.add(note)
        db.commit()

        response = client.get("/api/consumption/stats/2024-09-05")
        assert response.status_code == 200
        data = response.json()
        assert data["total_calories"] == 150.0

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/consumption/stats/2024-01-01")
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
            )
        assert response.status_code == 500

    def test_missing_date_field_returns_422(self, grocy_client):
        response = grocy_client.post("/api/consumption/check", json={})
        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/check",
            json={"date": "2024-03-01"},
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
            )
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/dry-run",
            json={"date": "2024-03-01"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestExecuteConsumptionEndpoint:
    """Tests for the POST /api/consumption/execute endpoint."""

    def test_execute_with_mocked_service_returns_200(self, grocy_client):
        mock_result = {
            "status": "success",
            "date": "2024-03-01",
            "consumed_meals": [],
            "consumed_products": [],
            "skipped_meals": [],
            "products_count": 0,
            "message": "Consumption executed successfully",
        }
        with patch(
            "app.api.endpoints.consumption.execute_consumption",
            return_value=mock_result,
        ):
            response = grocy_client.post(
                "/api/consumption/execute",
                json={"date": "2024-03-01"},
            )
        assert response.status_code == 200

    def test_execute_value_error_returns_400(self, grocy_client):
        def raise_value_error(*args, **kwargs):
            raise ValueError("Already consumed today")

        with patch(
            "app.api.endpoints.consumption.execute_consumption",
            side_effect=raise_value_error,
        ):
            response = grocy_client.post(
                "/api/consumption/execute",
                json={"date": "2024-03-01"},
            )
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/consumption/execute",
            json={"date": "2024-03-01"},
        )
        assert response.status_code == 401
