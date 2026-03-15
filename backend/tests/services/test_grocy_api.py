from unittest.mock import Mock, patch

import pytest
import requests

from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError


@pytest.fixture
def grocy_api():
    """Fixture to create a GrocyAPI instance with a test key."""
    return GrocyAPI(key="test_api_key")


@pytest.fixture
def mock_response():
    """Fixture to create a mock response object."""
    response = Mock(spec=requests.Response)
    response.ok = True
    response.status_code = 200
    response.json.return_value = {"test": "data"}
    response.text = "Response text"
    return response


class TestGrocyAPIInit:
    """Tests for GrocyAPI initialization."""

    @patch("app.services.grocy_api.settings")
    def test_init_strips_trailing_slash(self, mock_settings):
        """Test that trailing slash is stripped from GROCY_URL."""
        mock_settings.GROCY_URL = "https://grocy.example.com/"
        api = GrocyAPI(key="test_key")
        assert api.url == "https://grocy.example.com/api"

    @patch("app.services.grocy_api.settings")
    def test_init_without_trailing_slash(self, mock_settings):
        """Test URL construction without trailing slash."""
        mock_settings.GROCY_URL = "https://grocy.example.com"
        api = GrocyAPI(key="test_key")
        assert api.url == "https://grocy.example.com/api"

    def test_init_sets_headers_correctly(self, grocy_api):
        """Test that headers are set correctly with API key."""
        assert grocy_api.headers["Accept"] == "application/json"
        assert grocy_api.headers["Content-Type"] == "application/json"
        assert grocy_api.headers["GROCY-API-KEY"] == "test_api_key"


class TestGrocyAPIRequest:
    """Tests for the _request method."""

    @patch("app.services.grocy_api.requests.request")
    def test_request_success(self, mock_request, grocy_api, mock_response):
        """Test successful request."""
        mock_request.return_value = mock_response

        response = grocy_api._request("GET", "/test")

        assert response == mock_response
        mock_request.assert_called_once_with(
            "GET",
            grocy_api.url + "/test",
            json=None,
            params=[],
            headers=grocy_api.headers,
            timeout=10,
        )

    @patch("app.services.grocy_api.requests.request")
    def test_request_with_data_and_params(self, mock_request, grocy_api, mock_response):
        """Test request with data and params."""
        mock_request.return_value = mock_response
        test_data = {"key": "value"}
        test_params = {"param": "test"}

        response = grocy_api._request("POST", "/test", data=test_data, params=test_params)

        assert response == mock_response
        mock_request.assert_called_once_with(
            "POST",
            grocy_api.url + "/test",
            json=test_data,
            params=test_params,
            headers=grocy_api.headers,
            timeout=10,
        )

    @patch("app.services.grocy_api.requests.request")
    def test_request_network_error(self, mock_request, grocy_api):
        """Test request with network error."""
        mock_request.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(GrocyRequestError, match="Network error"):
            grocy_api._request("GET", "/test")

    @patch("app.services.grocy_api.requests.request")
    def test_request_timeout_error(self, mock_request, grocy_api):
        """Test request with timeout error."""
        mock_request.side_effect = requests.Timeout("Request timeout")

        with pytest.raises(GrocyRequestError, match="Request timeout"):
            grocy_api._request("GET", "/test")

    @patch("app.services.grocy_api.requests.request")
    def test_request_auth_error(self, mock_request, grocy_api):
        """Test request with 401 authentication error."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.ok = False
        mock_request.return_value = mock_response

        with pytest.raises(GrocyAuthError, match="Invalid Grocy API key"):
            grocy_api._request("GET", "/test")

    @patch("app.services.grocy_api.requests.request")
    def test_request_other_error(self, mock_request, grocy_api):
        """Test request with non-401 error status."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.text = "Internal server error"
        mock_request.return_value = mock_response

        with pytest.raises(GrocyError, match="Grocy returned error 500: Internal server error"):
            grocy_api._request("GET", "/test")


class TestGrocyAPIHTTPMethods:
    """Tests for GET, POST, PUT methods."""

    @patch.object(GrocyAPI, "_request")
    def test_get_method(self, mock_request, grocy_api, mock_response):
        """Test GET method."""
        mock_request.return_value = mock_response

        result = grocy_api.get("/test", params={"key": "value"})

        assert result == {"test": "data"}
        mock_request.assert_called_once_with("GET", "/test", params={"key": "value"})

    @patch.object(GrocyAPI, "_request")
    @patch("app.services.grocy_api.handle_response")
    def test_post_method(self, mock_handle_response, mock_request, grocy_api, mock_response):
        """Test POST method."""
        mock_request.return_value = mock_response
        mock_handle_response.return_value = {"created": "object"}
        test_data = {"key": "value"}

        result = grocy_api.post("/test", data=test_data, params={"param": "test"})

        assert result == {"created": "object"}
        mock_request.assert_called_once_with(
            "POST", "/test", data=test_data, params={"param": "test"}
        )
        mock_handle_response.assert_called_once_with(mock_response)

    @patch.object(GrocyAPI, "_request")
    @patch("app.services.grocy_api.handle_response")
    def test_put_method(self, mock_handle_response, mock_request, grocy_api, mock_response):
        """Test PUT method."""
        mock_request.return_value = mock_response
        mock_handle_response.return_value = {"updated": "object"}
        test_data = {"key": "value"}

        result = grocy_api.put("/test", data=test_data, params={"param": "test"})

        assert result == {"updated": "object"}
        mock_request.assert_called_once_with(
            "PUT", "/test", data=test_data, params={"param": "test"}
        )
        mock_handle_response.assert_called_once_with(mock_response)


class TestGrocyAPIProducts:
    """Tests for product-related methods."""

    @patch.object(GrocyAPI, "get")
    def test_get_product(self, mock_get, grocy_api):
        """Test get_product method."""
        mock_get.return_value = {"id": 123, "name": "Test Product"}

        result = grocy_api.get_product(123)

        assert result == {"id": 123, "name": "Test Product"}
        mock_get.assert_called_once_with("/objects/products/123")

    @patch.object(GrocyAPI, "get")
    def test_get_product_with_string_id(self, mock_get, grocy_api):
        """Test get_product converts ID to string."""
        mock_get.return_value = {"id": 456, "name": "Another Product"}

        result = grocy_api.get_product("456")

        assert result == {"id": 456, "name": "Another Product"}
        mock_get.assert_called_once_with("/objects/products/456")


class TestGrocyAPIMealPlan:
    """Tests for meal plan related methods."""

    @patch.object(GrocyAPI, "get")
    def test_get_meal_plan_recipe(self, mock_get, grocy_api):
        """Test get_meal_plan_recipe method."""
        mock_get.return_value = [{"id": 1, "name": "2024-01-15#5", "recipe": "Test Recipe"}]

        result = grocy_api.get_meal_plan_recipe("2024-01-15", 5)

        assert result == {"id": 1, "name": "2024-01-15#5", "recipe": "Test Recipe"}
        mock_get.assert_called_once_with("/objects/recipes", {"query[]": ["name=2024-01-15#5"]})

    @patch.object(GrocyAPI, "get")
    @patch("app.services.grocy_api.get_first_day_of_current_week")
    def test_get_meal_plan_with_day(self, mock_get_first_day, mock_get, grocy_api):
        """Test get_meal_plan with day parameter."""
        mock_get.return_value = [{"id": 1, "day": "2024-01-15"}]

        result = grocy_api.get_meal_plan(day="2024-01-15", week=None)

        assert result == [{"id": 1, "day": "2024-01-15"}]
        mock_get.assert_called_once_with("/objects/meal_plan", {"query[]": ["day=2024-01-15"]})
        mock_get_first_day.assert_not_called()

    @patch.object(GrocyAPI, "get")
    @patch("app.services.grocy_api.get_week_range")
    def test_get_meal_plan_with_week(self, mock_get_week_range, mock_get, grocy_api):
        """Test get_meal_plan with week parameter."""
        mock_get_week_range.return_value = ("2024-01-15", "2024-01-21")
        mock_get.return_value = [{"id": 1, "week": "2024-3"}]

        result = grocy_api.get_meal_plan(day=None, week="2024-3")

        assert result == [{"id": 1, "week": "2024-3"}]
        mock_get_week_range.assert_called_once_with(year=2024, week=2)
        mock_get.assert_called_once_with(
            "/objects/meal_plan", {"query[]": ["day>=2024-01-15", "day<=2024-01-21"]}
        )

    @patch.object(GrocyAPI, "get")
    @patch("app.services.grocy_api.get_first_day_of_current_week")
    def test_get_meal_plan_without_parameters(self, mock_get_first_day, mock_get, grocy_api):
        """Test get_meal_plan without day or week parameters."""
        mock_get_first_day.return_value = "2024-01-15"
        mock_get.return_value = [{"id": 1, "default": True}]

        result = grocy_api.get_meal_plan(day=None, week=None)

        assert result == [{"id": 1, "default": True}]
        mock_get_first_day.assert_called_once()
        mock_get.assert_called_once_with("/objects/meal_plan", {"query[]": ["day<=2024-01-15"]})


class TestGrocyAPIStockLog:
    """Tests for stock log methods."""

    @patch.object(GrocyAPI, "get")
    def test_get_stock_log(self, mock_get, grocy_api):
        """Test get_stock_log method."""
        mock_get.return_value = [{"id": 1, "product_id": 123}]

        result = grocy_api.get_stock_log(123, "2024-01-15")

        assert result == [{"id": 1, "product_id": 123}]
        expected_params = {
            "limit": 50,
            "order": "id:asc",
            "query[]": [
                "product_id=123",
                "transaction_type=consume",
                "row_created_timestamp>=2024-01-15",
                "row_created_timestamp<=2024-01-21",
            ],
        }
        mock_get.assert_called_once_with("/objects/stock_log", expected_params)

    @patch.object(GrocyAPI, "get")
    def test_get_stock_log_date_parsing(self, mock_get, grocy_api):
        """Test get_stock_log correctly parses date and calculates end date."""
        mock_get.return_value = []

        grocy_api.get_stock_log(456, "2024-12-25")

        call_args = mock_get.call_args
        params = call_args[0][1]

        # Verify the end date is 6 days later
        assert "row_created_timestamp>=2024-12-25" in params["query[]"]
        assert "row_created_timestamp<=2024-12-31" in params["query[]"]


class TestGrocyAPIUnitConversions:
    """Tests for unit conversion methods."""

    @patch.object(GrocyAPI, "get")
    def test_get_unit_conversion_factor_success(self, mock_get, grocy_api):
        """Test successful unit conversion factor retrieval."""
        mock_get.return_value = [{"factor": 1.5}]

        result = grocy_api.get_unit_conversion_factor(123, 1, 2)

        assert result == 1.5
        expected_params = {
            "query[]": [
                "product_id=123",
                "from_qu_id=1",
                "to_qu_id=2",
            ]
        }
        mock_get.assert_called_once_with(
            "/objects/quantity_unit_conversions_resolved", expected_params
        )

    @patch.object(GrocyAPI, "get")
    def test_get_unit_conversion_factor_not_found(self, mock_get, grocy_api):
        """Test unit conversion factor when no conversion exists."""
        mock_get.return_value = []

        with pytest.raises(Exception, match="No unit conversation for product id:123"):
            grocy_api.get_unit_conversion_factor(123, 1, 2)

    @patch.object(GrocyAPI, "get_unit_conversion_factor")
    def test_get_conversion_factor_safe_success_first_try(self, mock_get_conversion, grocy_api):
        """Test get_conversion_factor_safe succeeds on first unit."""
        mock_get_conversion.return_value = 2.0

        result = grocy_api.get_conversion_factor_safe(123, 1, [2, 3, 4])

        assert result == 2.0
        mock_get_conversion.assert_called_once_with(123, 1, 2)

    @patch.object(GrocyAPI, "get_unit_conversion_factor")
    def test_get_conversion_factor_safe_success_after_retry(self, mock_get_conversion, grocy_api):
        """Test get_conversion_factor_safe succeeds after retrying units."""
        mock_get_conversion.side_effect = [
            Exception("No conversion"),
            Exception("No conversion"),
            3.5,
        ]

        result = grocy_api.get_conversion_factor_safe(123, 1, [2, 3, 4])

        assert result == 3.5
        assert mock_get_conversion.call_count == 3

    @patch.object(GrocyAPI, "get_unit_conversion_factor")
    def test_get_conversion_factor_safe_all_fail(self, mock_get_conversion, grocy_api):
        """Test get_conversion_factor_safe when all units fail."""
        mock_get_conversion.side_effect = Exception("No conversion")

        with pytest.raises(Exception, match="No unit conversion for product id: 123"):
            grocy_api.get_conversion_factor_safe(123, 1, [2, 3, 4])

        assert mock_get_conversion.call_count == 3


class TestGrocyAPIShoppingList:
    """Tests for shopping list creation."""

    @patch.object(GrocyAPI, "post")
    @patch("app.services.grocy_api.get_first_day_of_current_week")
    def test_create_shopping_list_with_day(self, mock_get_first_day, mock_post, grocy_api):
        """Test create_shopping_list with day parameter."""
        mock_post.side_effect = [
            {"created_object_id": 42},
            {"id": 1},
            {"id": 2},
        ]

        products_to_buy = {
            123: {"amount": 5, "note": "Test note 1"},
            456: {"amount": 3, "note": "Test note 2"},
        }

        grocy_api.create_shopping_list(
            day="2024-01-15", week=None, products_to_buy=products_to_buy
        )

        # Check shopping list creation
        assert mock_post.call_count == 3
        mock_post.assert_any_call(
            "/objects/shopping_lists", data={"name": "Prepare to eat: 2024-01-15"}
        )

        # Check product additions
        mock_post.assert_any_call(
            "/objects/shopping_list",
            data={
                "product_id": 123,
                "amount": 5,
                "shopping_list_id": 42,
                "note": "Test note 1",
            },
        )
        mock_post.assert_any_call(
            "/objects/shopping_list",
            data={
                "product_id": 456,
                "amount": 3,
                "shopping_list_id": 42,
                "note": "Test note 2",
            },
        )
        mock_get_first_day.assert_not_called()

    @patch.object(GrocyAPI, "post")
    def test_create_shopping_list_with_week(self, mock_post, grocy_api):
        """Test create_shopping_list with week parameter."""
        mock_post.side_effect = [
            {"created_object_id": 99},
            {"id": 1},
        ]

        products_to_buy = {
            789: {"amount": 2, "note": "Week note"},
        }

        grocy_api.create_shopping_list(day=None, week="2024-3", products_to_buy=products_to_buy)

        mock_post.assert_any_call(
            "/objects/shopping_lists", data={"name": "Prepare to eat: 2024-3"}
        )

    @patch.object(GrocyAPI, "post")
    @patch("app.services.grocy_api.get_first_day_of_current_week")
    def test_create_shopping_list_without_parameters(
        self, mock_get_first_day, mock_post, grocy_api
    ):
        """Test create_shopping_list without day or week parameters."""
        mock_get_first_day.return_value = "2024-01-15"
        mock_post.side_effect = [
            {"created_object_id": 55},
            {"id": 1},
        ]

        products_to_buy = {
            111: {"amount": 10, "note": "Default note"},
        }

        grocy_api.create_shopping_list(day=None, week=None, products_to_buy=products_to_buy)

        mock_get_first_day.assert_called_once()
        mock_post.assert_any_call(
            "/objects/shopping_lists", data={"name": "Prepare to eat: 2024-01-15"}
        )

    @patch.object(GrocyAPI, "post")
    def test_create_shopping_list_empty_products(self, mock_post, grocy_api):
        """Test create_shopping_list with empty products dict."""
        mock_post.return_value = {"created_object_id": 77}

        grocy_api.create_shopping_list(day="2024-01-15", week=None, products_to_buy={})

        # Should only create the shopping list, no products added
        mock_post.assert_called_once_with(
            "/objects/shopping_lists", data={"name": "Prepare to eat: 2024-01-15"}
        )


class TestGrocyAPIExceptions:
    """Tests for custom exception classes."""

    def test_grocy_error_inheritance(self):
        """Test GrocyError is an Exception."""
        error = GrocyError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_grocy_auth_error_inheritance(self):
        """Test GrocyAuthError inherits from GrocyError."""
        error = GrocyAuthError("Auth failed")
        assert isinstance(error, GrocyError)
        assert isinstance(error, Exception)
        assert str(error) == "Auth failed"

    def test_grocy_request_error_inheritance(self):
        """Test GrocyRequestError inherits from GrocyError."""
        error = GrocyRequestError("Network failed")
        assert isinstance(error, GrocyError)
        assert isinstance(error, Exception)
        assert str(error) == "Network failed"
