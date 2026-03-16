import contextlib
from datetime import datetime, timedelta

import requests

from app.utils.helpers import get_first_day_of_current_week, get_week_range, handle_response


class GrocyError(Exception):
    """Base exception for Grocy API errors."""


class GrocyAuthError(GrocyError):
    """Authentication/authorization error (e.g. invalid API key)."""


class GrocyRequestError(GrocyError):
    """Network/transport-level error when calling Grocy."""


class GrocyAPI:
    def __init__(self, key: str, url: str):
        self.base_url = url.rstrip("/")
        self.url = f"{url.rstrip('/')}/api"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "GROCY-API-KEY": key,
        }

    def get_base_url(self):
        return self.base_url

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
            raise GrocyError(f"Grocy returned error {response.status_code}: {response.text}")

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
            ],
        }
        return self.get("/objects/stock_log", params)

    def get_meal_plan(self, day, week):
        if day is not None:
            params = {"query[]": ["day=" + day]}
        elif week is not None:
            data = week.split("-")
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
            self.put(
                f"/objects/quantity_unit_conversions/{conversion_id}",
                {"factor": factor},
            )
        else:
            self.post(
                "/objects/quantity_unit_conversions",
                {
                    "product_id": int(product_id),
                    "from_qu_id": int(from_qu_id),
                    "to_qu_id": int(to_qu_id),
                    "factor": factor,
                },
            )

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
        if day is not None:
            shopping_list_name += day
        elif week is not None:
            shopping_list_name += week
        else:
            shopping_list_name += get_first_day_of_current_week()

        response = self.post("/objects/shopping_lists", data={"name": shopping_list_name})
        shopping_list_id = response["created_object_id"]
        for product_id, amount_to_buy in products_to_buy.items():
            # Fetch product's stock unit so Grocy interprets the amount correctly.
            # Without qu_id, Grocy defaults to qu_id_purchase, causing wrong unit display
            # when our amounts are in qu_id_stock (e.g. sending 119.8 grams → shows as
            # "119.8 Пачок" instead of "119.8 g").
            qu_id = amount_to_buy.get("qu_id")
            if qu_id is None:
                try:
                    product_info = self.get_product(int(product_id))
                    qu_id = product_info.get("qu_id_stock")
                except Exception:
                    pass

            item_data: dict = {
                "product_id": product_id,
                "amount": amount_to_buy["amount"],
                "shopping_list_id": shopping_list_id,
                "note": amount_to_buy["note"],
            }
            if qu_id is not None:
                item_data["qu_id"] = qu_id

            self.post("/objects/shopping_list", data=item_data)

    def create_recipe_shopping_list(self, recipe_id: int, list_name: str) -> dict:
        """Create a Grocy shopping list with missing products for a recipe.

        Returns dict with shopping_list_id and items_added count.
        """
        resolved = self.get(
            "/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={recipe_id}"]}
        )

        # Aggregate needed amounts per product, converting from ingredient unit to stock unit
        needed: dict[int, float] = {}
        qu_id_stock_map: dict[int, int] = {}
        product_names: dict[int, str] = {}

        for pos in resolved:
            pid = pos["product_id_effective"]
            recipe_amount = float(pos.get("recipe_amount", 0))
            ingredient_qu_id = pos.get("qu_id")

            # Look up product's stock unit once per product
            if pid not in qu_id_stock_map:
                try:
                    product_info = self.get_product(pid)
                    qu_id_stock_map[pid] = product_info["qu_id_stock"]
                except Exception:
                    qu_id_stock_map[pid] = ingredient_qu_id

            stock_qu_id = qu_id_stock_map[pid]

            # Convert recipe_amount from ingredient unit to stock unit
            factor = 1
            if ingredient_qu_id and stock_qu_id and ingredient_qu_id != stock_qu_id:
                with contextlib.suppress(Exception):
                    factor = self.get_unit_conversion_factor(pid, ingredient_qu_id, stock_qu_id)

            needed[pid] = needed.get(pid, 0) + recipe_amount * factor

            if pid not in product_names:
                product_names[pid] = pos.get("product_name", f"Product #{pid}")

        # Check stock and collect missing items
        missing: dict[int, float] = {}
        for pid, amount_needed in needed.items():
            try:
                stock_info = self.get(f"/stock/products/{pid}")
                # use aggregated (includes sub-products) and same unit as qu_id_stock
                stock_amount = float(stock_info.get("stock_amount_aggregated", 0))
            except Exception:
                stock_amount = 0
            deficit = amount_needed - stock_amount
            if deficit > 0:
                missing[pid] = deficit

        if not missing:
            return {"shopping_list_id": None, "items_added": 0}

        # Create shopping list
        response = self.post("/objects/shopping_lists", data={"name": list_name})
        shopping_list_id = response["created_object_id"]

        # Add missing products with qu_id so Grocy interprets the unit correctly
        items_added = 0
        for pid, deficit in missing.items():
            item_data: dict = {
                "product_id": pid,
                "amount": round(deficit, 2),
                "shopping_list_id": shopping_list_id,
                "note": product_names.get(pid, ""),
            }
            stock_qu_id = qu_id_stock_map.get(pid)
            if stock_qu_id:
                item_data["qu_id"] = stock_qu_id
            self.post("/objects/shopping_list", data=item_data)
            items_added += 1

        return {"shopping_list_id": shopping_list_id, "items_added": items_added}
