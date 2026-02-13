import requests
from datetime import datetime, timedelta

from app.utils.helpers import (
    get_first_day_of_current_week,
    get_week_range,
    handle_response,
)
from app.core.config import settings


class GrocyError(Exception):
    """Base exception for Grocy API errors."""


class GrocyAuthError(GrocyError):
    """Authentication/authorization error (e.g. invalid API key)."""


class GrocyRequestError(GrocyError):
    """Network/transport-level error when calling Grocy."""


class GrocyAPI:
    def __init__(self, key: str):
        self.url = f"{settings.GROCY_URL.rstrip('/')}/api"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "GROCY-API-KEY": key,
        }

    def _request(self, method: str, path: str, *, data=None, params=None) -> requests.Response:
        """Low-level HTTP request wrapper with basic error handling."""
        params = params or []
        try:
            response = requests.request(
                method,
                self.url + path,
                json=data,
                params=params,
                headers=self.headers,
                timeout=10,
            )
        except requests.RequestException as exc:
            # Network or connection issue
            raise GrocyRequestError(str(exc)) from exc

        # Auth error
        if response.status_code == 401:
            raise GrocyAuthError("Invalid Grocy API key")

        # Other non-success statuses
        if not response.ok:
            raise GrocyError(
                f"Grocy returned error {response.status_code}: {response.text}"
            )

        return response

    def get(self, path: str, params=None):
        """Perform GET and return parsed JSON on success."""
        response = self._request("GET", path, params=params)
        return response.json()

    def post(self, path: str, data=None, params=None):
        """Perform POST and return parsed/handled content."""
        response = self._request("POST", path, data=data, params=params)
        return handle_response(response)

    def put(self, path: str, data=None, params=None):
        """Perform PUT and return parsed/handled content."""
        response = self._request("PUT", path, data=data, params=params)
        return handle_response(response)
    
    def get_product(self, product_id):
        product = self.get("/objects/products/" + str(product_id))
        return product
    
    def get_meal_plan_recipe(self, day, meal_id):
        params = {"query[]": ["name=" + day + "#" + str(meal_id)]}
        recipes = self.get("/objects/recipes", params)
        return recipes[0]

    def get_stock_log(self, product_id, day):
        partsOfDay = day.split("-")
        # todo check if recipe_id is null for non recipe products
        date = datetime(int(partsOfDay[0]), int(partsOfDay[1]), int(partsOfDay[2]))
        params = {
            "limit": 50,
            "order": "id:asc",
            "query[]": [
                "product_id=" + str(product_id),
                "transaction_type=consume",
                "row_created_timestamp>=" + day,
                "row_created_timestamp<=" + (date + timedelta(days=6)).strftime("%Y-%m-%d"),
            ]
        }
        return self.get("/objects/stock_log", params)

    def get_meal_plan(self, day, week):
        if (day is not None):
            params = {"query[]": ["day=" + day]}
        elif (week is not None):
            data = week.split('-')
            fist_day, last_day = get_week_range(year=int(data[0]), week=int(data[1]) - 1)
            params = {"query[]": ["day>=" + fist_day, "day<=" + last_day]}
        else:
            params = {"query[]": ["day<=" + get_first_day_of_current_week()]}

        return self.get("/objects/meal_plan", params)
    
    def get_conversion_factor_safe(self, product_id, qu_id_stock, units):
        for unit_id in units:
            try:
                return self.get_unit_conversion_factor(product_id, qu_id_stock, unit_id)
            except Exception:
                continue
        raise Exception(f"No unit conversion for product id: {product_id}")
    
    def get_conversion_reverse_factor_safe(self, product_id, qu_id_stock, units):
        for unit_id in units:
            try:
                return self.get_unit_conversion_factor(product_id, unit_id, qu_id_stock)
            except Exception:
                continue
        raise GrocyError(f"No unit conversion for product id: {product_id}")

    def get_conversion_factor_with_unit(self, product_id, qu_id_stock, units):
        """Returns (factor, target_unit_id) tuple or (None, None) if not found."""
        for unit_id in units:
            try:
                factor = self.get_unit_conversion_factor(product_id, qu_id_stock, unit_id)
                return factor, unit_id
            except Exception:
                continue
        return None, None

    def update_unit_conversion(self, product_id, from_qu_id, to_qu_id, factor):
        """Update or create unit conversion for a product in Grocy."""
        params = {
            "query[]": [
                f"product_id={product_id}",
                f"from_qu_id={from_qu_id}",
                f"to_qu_id={to_qu_id}",
            ]
        }
        existing = self.get("/objects/quantity_unit_conversions", params)

        if existing and len(existing) > 0:
            conversion_id = existing[0]["id"]
            self.put(f"/objects/quantity_unit_conversions/{conversion_id}", {"factor": factor})
        else:
            self.post("/objects/quantity_unit_conversions", {
                "product_id": int(product_id),
                "from_qu_id": int(from_qu_id),
                "to_qu_id": int(to_qu_id),
                "factor": factor,
            })

    def get_unit_conversion_factor(self, product_id, from_qu, to_qu):
        params = {
            "query[]": [
                "product_id=" + str(product_id),
                "from_qu_id=" + str(from_qu),
                "to_qu_id=" + str(to_qu),
            ]
        }
        quantity_unit = self.get("/objects/quantity_unit_conversions_resolved", params)
        if len(quantity_unit) == 0:
            raise Exception("No unit conversation for product id:" + str(product_id))
        
        return quantity_unit[0]["factor"] 

    def create_shopping_list(self, day, week, products_to_buy):
        shopping_list_name = "Prepare to eat: "
        if (day is not None):
            shopping_list_name += day
        elif (week is not None):
            shopping_list_name += week
        else:
            shopping_list_name += get_first_day_of_current_week()

        response = self.post("/objects/shopping_lists", data={"name": shopping_list_name})
        shopping_list_id = response["created_object_id"]
        for product_id, amount_to_buy in products_to_buy.items(): 
            response = self.post("/objects/shopping_list", data={
                "product_id": product_id,
                "amount": amount_to_buy["amount"],
                "shopping_list_id": shopping_list_id,
                "note": amount_to_buy["note"]
            })
            