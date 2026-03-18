"""
Consumption service - handles meal plan consumption logic
"""

import contextlib
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.models.household import Household  # noqa: F401 — register FK target table
from app.models.product import (
    ConsumedProduct,
    MealPlanConsumption,
    NoteNutrients,
)
from app.models.recipe import Recipe, RecipeData
from app.models.user import User  # noqa: F401 — register FK target table
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.product import (
    get_latest_product_data,
    get_product_by_grocy_id,
    update_grocy_product_nutrients,
)


class ConsumptionError(Exception):
    """Exception raised during consumption processing"""

    pass


# Mapping of Ukrainian nutrient names in meal plan notes to field names
# Format: "Калорій:500/Білків:30/Вуглеводів:60/Жирів:15"
_NOTE_NUTRIENT_MAP = {
    "Калорій": "calories",
    "Білків": "proteins",
    "Вуглеводів": "carbohydrates",
    "Жирів": "fats",
    "Жирів нас.": "fats_saturated",
    "Вуглеводів цукрів": "carbohydrates_of_sugars",
    "Солі": "salt",
    "Клітковини": "fibers",
}


def _parse_note_nutrients(note: str) -> dict[str, float]:
    """Parse nutrient values from a meal plan note string."""
    result: dict[str, float] = {}
    for part in note.split("/"):
        kv = part.split(":")
        if len(kv) == 2:
            key = _NOTE_NUTRIENT_MAP.get(kv[0].strip())
            if key:
                with contextlib.suppress(ValueError):
                    result[key] = float(kv[1].strip())
    return result


def check_products_availability(
    db: Session,
    grocy_api: GrocyAPI,
    date_str: str,
    household_id: int | None = None,
) -> dict[str, Any]:
    """
    Check if all products from meal plan are available in stock.
    For recipes, uses Grocy's fulfillment API which correctly accounts for substitutions.
    For standalone products, checks stock directly.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    try:
        meal_plan = grocy_api.get_meal_plan(day=date_str, week=None)
    except GrocyError as e:
        raise ConsumptionError(f"Failed to fetch meal plan: {e!s}") from e

    products_to_buy = {}
    products_to_buy_detailed = []
    products_to_consume = {}
    products_to_consume_detailed = []
    allocated = {}  # Track cross-recipe product allocations

    for meal in meal_plan:
        if meal["type"] == "note" or meal.get("done"):
            continue

        if meal["type"] == "recipe":
            recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
            shadow_id = recipe_meal["id"]
            recipe_data = grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")
            recipe_name = recipe_data.get("name", f"Recipe #{meal['recipe_id']}")

            # Use Grocy's fulfillment API — it correctly handles substitutions
            fulfillment = grocy_api.get(f"/recipes/{shadow_id}/fulfillment")
            missing_count = fulfillment.get("missing_products_count", 0)

            resolved = grocy_api.get(
                "/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={shadow_id}"]}
            )

            for pos in resolved:
                if pos["product_id_effective"] is None:
                    continue

                total_amount = _calc_recipe_product_amount(
                    db, grocy_api, pos, household_id=household_id
                )
                note = recipe_name + " | "
                parent_product_id = pos["product_id"]
                effective_product_id = pos["product_id_effective"]

                # Expand parent-product into individual sub-products with their stock amounts
                if parent_product_id != effective_product_id:
                    sub_products = (
                        grocy_api.get(
                            "/objects/products",
                            {"query[]": [f"parent_product_id={parent_product_id}"]},
                        )
                        or []
                    )
                    candidates = []
                    for sub in sub_products:
                        try:
                            stock_data = grocy_api.get(f"/stock/products/{sub['id']}")
                            sub_stock = float(stock_data.get("stock_amount_aggregated", 0))
                        except GrocyError:
                            sub_stock = 0
                        candidates.append((sub["id"], sub_stock))

                    remaining = total_amount
                    for sub_id, sub_stock in candidates:
                        if remaining <= 0:
                            break
                        # Subtract amounts already allocated by earlier meals
                        available = sub_stock - allocated.get(sub_id, 0)
                        if available <= 0:
                            continue
                        sub_amount = min(remaining, available)
                        remaining -= sub_amount
                        allocated[sub_id] = allocated.get(sub_id, 0) + sub_amount
                        if sub_id not in products_to_consume:
                            products_to_consume[sub_id] = {"amount": 0, "note": ""}
                        products_to_consume[sub_id]["amount"] += sub_amount
                        products_to_consume[sub_id]["note"] += note

                    # If nothing covered (missing_count > 0), add shortage to shopping list
                    if missing_count > 0 and remaining > 0:
                        shortage = round(remaining, 4)
                        pid = effective_product_id
                        product = get_product_by_grocy_id(
                            db, grocy_id=pid, household_id=household_id
                        )
                        product_name = product.name if product else f"Product #{pid}"
                        if not product:
                            try:
                                grocy_product = grocy_api.get_product(pid)
                                product_name = grocy_product.get("name", f"Product #{pid}")
                            except GrocyError:
                                product_name = f"Product #{pid}"
                        if pid not in products_to_buy:
                            products_to_buy[pid] = {"amount": shortage, "note": note}
                            products_to_buy_detailed.append(
                                {
                                    "product_id": pid,
                                    "name": product_name,
                                    "amount": shortage,
                                    "note": note,
                                }
                            )
                        else:
                            products_to_buy[pid]["amount"] += shortage
                            products_to_buy[pid]["note"] += note
                else:
                    allocated[effective_product_id] = (
                        allocated.get(effective_product_id, 0) + total_amount
                    )
                    if effective_product_id not in products_to_consume:
                        products_to_consume[effective_product_id] = {
                            "amount": 0,
                            "note": "",
                        }
                    products_to_consume[effective_product_id]["amount"] += total_amount
                    products_to_consume[effective_product_id]["note"] += note

                    # Regular shortage check (no sub-products)
                    if missing_count > 0:
                        try:
                            stock_data = grocy_api.get(f"/stock/products/{effective_product_id}")
                            stock_amount = float(stock_data.get("stock_amount_aggregated", 0))
                        except GrocyError:
                            stock_amount = 0
                        if total_amount > stock_amount:
                            shortage = round(total_amount - stock_amount, 4)
                            product = get_product_by_grocy_id(
                                db, grocy_id=effective_product_id, household_id=household_id
                            )
                            product_name = (
                                product.name if product else f"Product #{effective_product_id}"
                            )
                            if not product:
                                try:
                                    grocy_product = grocy_api.get_product(effective_product_id)
                                    product_name = grocy_product.get(
                                        "name", f"Product #{effective_product_id}"
                                    )
                                except GrocyError:
                                    product_name = f"Product #{effective_product_id}"
                            if effective_product_id not in products_to_buy:
                                products_to_buy[effective_product_id] = {
                                    "amount": shortage,
                                    "note": note,
                                }
                                products_to_buy_detailed.append(
                                    {
                                        "product_id": effective_product_id,
                                        "name": product_name,
                                        "amount": shortage,
                                        "note": note,
                                    }
                                )
                            else:
                                products_to_buy[effective_product_id]["amount"] += shortage
                                products_to_buy[effective_product_id]["note"] += note

            continue

        # Standalone product
        product_id = meal.get("product_id")
        if product_id is None:
            continue

        amount_needed = meal.get("product_amount", 0)

        product = get_product_by_grocy_id(db, grocy_id=product_id, household_id=household_id)
        product_name = product.name if product else f"Product #{product_id}"
        if not product:
            try:
                grocy_product = grocy_api.get_product(product_id)
                product_name = grocy_product.get("name", f"Product #{product_id}")
            except GrocyError:
                product_name = f"Product #{product_id}"

        allocated[product_id] = allocated.get(product_id, 0) + amount_needed
        if product_id not in products_to_consume:
            products_to_consume[product_id] = {"amount": 0, "note": ""}
        products_to_consume[product_id]["amount"] += amount_needed

        try:
            data = grocy_api.get(f"/stock/products/{product_id}")
            if allocated[product_id] > data["stock_amount_aggregated"]:
                shortage = round(allocated[product_id] - data["stock_amount_aggregated"], 4)
                if product_id not in products_to_buy:
                    products_to_buy[product_id] = {"amount": shortage, "note": ""}
                    products_to_buy_detailed.append(
                        {
                            "product_id": product_id,
                            "name": product_name,
                            "amount": shortage,
                            "note": "",
                        }
                    )
                else:
                    products_to_buy[product_id]["amount"] += shortage
        except GrocyError as e:
            print(f"Error checking product {product_id}: {e!s}")
            continue

        products_to_consume_detailed.append(
            {
                "product_id": product_id,
                "name": product_name,
                "amount": amount_needed,
                "note": "",
            }
        )

    # Build products_to_consume_detailed from aggregated dict (for recipes + products)
    for product_id, info in products_to_consume.items():
        product = get_product_by_grocy_id(db, grocy_id=product_id, household_id=household_id)
        product_name = product.name if product else f"Product #{product_id}"
        # Avoid duplicates from standalone products already appended above
        if not any(d["product_id"] == product_id for d in products_to_consume_detailed):
            products_to_consume_detailed.append(
                {
                    "product_id": product_id,
                    "name": product_name,
                    "amount": info["amount"],
                    "note": info["note"],
                }
            )

    # ── Cross-recipe stock validation ──────────────────────────────
    # Grocy's fulfillment API checks each recipe in isolation, so when the
    # same (sub-)product appears in multiple recipes, per-recipe checks may
    # all pass even though the aggregate demand exceeds stock.
    for product_id, info in products_to_consume.items():
        total_needed = info["amount"]
        try:
            stock_data = grocy_api.get(f"/stock/products/{product_id}")
            stock_amount = float(stock_data.get("stock_amount_aggregated", 0))
        except GrocyError:
            stock_amount = 0

        if total_needed > stock_amount:
            shortage = round(total_needed - stock_amount, 4)
            if product_id not in products_to_buy:
                product = get_product_by_grocy_id(
                    db, grocy_id=product_id, household_id=household_id
                )
                product_name = product.name if product else f"Product #{product_id}"
                if not product:
                    try:
                        grocy_product = grocy_api.get_product(product_id)
                        product_name = grocy_product.get("name", f"Product #{product_id}")
                    except GrocyError:
                        product_name = f"Product #{product_id}"
                products_to_buy[product_id] = {
                    "amount": shortage,
                    "note": info.get("note", ""),
                }
                products_to_buy_detailed.append(
                    {
                        "product_id": product_id,
                        "name": product_name,
                        "amount": shortage,
                        "note": info.get("note", ""),
                    }
                )
            else:
                # Update shortage to the correct cross-recipe total
                products_to_buy[product_id]["amount"] = shortage
                for detail in products_to_buy_detailed:
                    if detail["product_id"] == product_id:
                        detail["amount"] = shortage
                        break

    if products_to_buy:
        return {
            "status": "insufficient_stock",
            "products_to_consume": products_to_consume,
            "products_to_buy": products_to_buy,
            "products_to_buy_detailed": products_to_buy_detailed,
            "products_to_consume_detailed": products_to_consume_detailed,
            "message": "Some products are not available in sufficient quantity",
        }
    else:
        return {
            "status": "success",
            "products_to_consume": products_to_consume,
            "products_to_buy": {},
            "products_to_buy_detailed": [],
            "products_to_consume_detailed": products_to_consume_detailed,
            "message": "All products are available",
        }


def create_shopping_list(
    grocy_api: GrocyAPI, date_str: str, products_to_buy: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """
    Create shopping list in Grocy
    """
    grocy_api.create_shopping_list(date_str, None, products_to_buy)

    return {
        "status": "success",
        "message": f"Shopping list created for {date_str}",
        "products_count": len(products_to_buy),
    }


def dry_run_consumption(
    db: Session,
    grocy_api: GrocyAPI,
    date_str: str,
    household_id: int | None = None,
) -> dict[str, Any]:
    """
    Dry run - show what products will be consumed, grouped by meal/recipe
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    try:
        meal_plan = grocy_api.get_meal_plan(day=date_str, week=None)
    except GrocyError as e:
        raise ConsumptionError(f"Failed to fetch meal plan: {e!s}") from e

    meals_preview = []
    total_calories = 0.0
    total_nutrients = {
        "carbohydrates": 0.0,
        "carbohydrates_of_sugars": 0.0,
        "proteins": 0.0,
        "fats": 0.0,
        "fats_saturated": 0.0,
        "salt": 0.0,
        "fibers": 0.0,
    }
    total_products_count = 0
    allocated = {}  # Track cross-recipe product allocations

    for meal in meal_plan:
        if meal.get("done"):
            continue

        if meal["type"] == "note":
            note_nutrients = _parse_note_nutrients(meal.get("note") or "")
            if note_nutrients:
                total_calories += note_nutrients.get("calories", 0.0)
                for key in total_nutrients:
                    if key in note_nutrients:
                        total_nutrients[key] += note_nutrients[key]
                meals_preview.append(
                    {
                        "type": "note",
                        "recipe_name": meal.get("note"),
                        "recipe_grocy_id": None,
                        "available": True,
                        "missing_products_count": 0,
                        "products": [],
                        "note_nutrients": note_nutrients,
                    }
                )
            continue

        if meal["type"] == "product":
            product_id = meal["product_id"]
            amount_needed = meal.get("product_amount", 0)
            allocated[product_id] = allocated.get(product_id, 0) + amount_needed

            product_preview = _build_product_preview(
                db,
                grocy_api,
                product_id,
                amount_needed,
                household_id=household_id,
            )
            if product_preview:
                # Check stock against total allocated (cross-meal)
                is_available = True
                try:
                    stock_data = grocy_api.get(f"/stock/products/{product_id}")
                    if stock_data["stock_amount"] < allocated[product_id]:
                        is_available = False
                except GrocyError:
                    is_available = False

                if is_available:
                    _accumulate_nutrients(product_preview, total_nutrients)
                    total_calories += (product_preview.get("calories") or 0) * product_preview[
                        "quantity"
                    ]

                meals_preview.append(
                    {
                        "type": "product",
                        "recipe_name": None,
                        "recipe_grocy_id": None,
                        "available": is_available,
                        "missing_products_count": 0 if is_available else 1,
                        "products": [product_preview],
                    }
                )
                total_products_count += 1
            continue

        if meal["type"] == "recipe":
            recipe_data = grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")
            recipe_name = recipe_data.get("name", f"Recipe #{meal['recipe_id']}")

            recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
            shadow_id = recipe_meal["id"]

            # Check fulfillment (like old script)
            fulfillment = grocy_api.get(f"/recipes/{shadow_id}/fulfillment")
            missing_count = fulfillment.get("missing_products_count", 0)
            is_available = missing_count == 0

            resolved = grocy_api.get(
                "/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={shadow_id}"]}
            )

            recipe_products = []
            recipe_has_cross_shortage = False
            for pos in resolved:
                parent_product_id = pos["product_id"]
                effective_product_id = pos["product_id_effective"]
                total_amount = _calc_recipe_product_amount(
                    db, grocy_api, pos, household_id=household_id
                )

                # If the ingredient uses parent-product/sub-product substitution,
                # show each sub-product with its actual available stock as the amount.
                # Grocy will split consumption across them during execute.
                if parent_product_id != effective_product_id:
                    # Find all sub-products of this parent
                    sub_products = (
                        grocy_api.get(
                            "/objects/products",
                            {"query[]": [f"parent_product_id={parent_product_id}"]},
                        )
                        or []
                    )

                    remaining = total_amount
                    for sub in sub_products:
                        if remaining <= 0:
                            break
                        sub_id = sub["id"]
                        try:
                            stock_data = grocy_api.get(f"/stock/products/{sub_id}")
                            sub_stock = float(stock_data.get("stock_amount_aggregated", 0))
                        except GrocyError:
                            sub_stock = 0

                        # Subtract amounts already allocated by earlier meals
                        sub_stock -= allocated.get(sub_id, 0)

                        if sub_stock <= 0:
                            continue

                        sub_amount = min(remaining, sub_stock)
                        remaining -= sub_amount
                        allocated[sub_id] = allocated.get(sub_id, 0) + sub_amount

                        product_preview = _build_product_preview(
                            db, grocy_api, sub_id, sub_amount, household_id=household_id
                        )
                        if product_preview:
                            recipe_products.append(product_preview)
                            total_products_count += 1

                    if remaining > 0:
                        recipe_has_cross_shortage = True
                else:
                    # Track allocation for cross-recipe validation
                    allocated[effective_product_id] = (
                        allocated.get(effective_product_id, 0) + total_amount
                    )

                    product_preview = _build_product_preview(
                        db,
                        grocy_api,
                        effective_product_id,
                        total_amount,
                        household_id=household_id,
                    )
                    if product_preview:
                        recipe_products.append(product_preview)
                        total_products_count += 1

            # Override availability if cross-recipe shortage detected
            if recipe_has_cross_shortage:
                is_available = False

            # Accumulate nutrients only for available recipes
            if is_available:
                for product_preview in recipe_products:
                    _accumulate_nutrients(product_preview, total_nutrients)
                    total_calories += (
                        product_preview.get("calories") or 0
                    ) * product_preview["quantity"]

            meals_preview.append(
                {
                    "type": "recipe",
                    "recipe_name": recipe_name,
                    "recipe_grocy_id": meal["recipe_id"],
                    "available": is_available,
                    "missing_products_count": missing_count,
                    "products": recipe_products,
                }
            )

    return {
        "status": "success",
        "date": date_str,
        "meals": meals_preview,
        "total_calories": round(total_calories, 4),
        "total_nutrients": {k: round(v, 4) for k, v in total_nutrients.items()},
        "products_count": total_products_count,
    }


def execute_consumption(
    db: Session,
    grocy_api: GrocyAPI,
    date_str: str,
    household_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Execute consumption - consume products/recipes in Grocy and save to database.
    Ports the logic from consume_old_script.py.
    """
    try:
        consume_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    try:
        meal_plan = grocy_api.get_meal_plan(day=date_str, week=None)
    except GrocyError as e:
        raise ConsumptionError(f"Failed to fetch meal plan: {e!s}") from e

    consumed_meals = []
    consumed_products_list = []
    skipped_meals = []

    for meal in meal_plan:
        if meal.get("done"):
            continue

        # Notes: parse nutrients if present, save to note_nutrients table, mark as done
        if meal["type"] == "note":
            note_text = meal.get("note") or ""
            note_nutrients = _parse_note_nutrients(note_text)
            if note_nutrients:
                # Dedup: skip if same note already saved for this day
                existing_note = db.exec(
                    select(NoteNutrients).where(
                        NoteNutrients.date == consume_date,
                        NoteNutrients.note == note_text,
                    )
                ).first()
                if not existing_note:
                    db.add(
                        NoteNutrients(
                            date=consume_date,
                            note=note_text,
                            household_id=household_id,
                            user_id=user_id,
                            calories=note_nutrients.get("calories"),
                            proteins=note_nutrients.get("proteins"),
                            carbohydrates=note_nutrients.get("carbohydrates"),
                            carbohydrates_of_sugars=note_nutrients.get("carbohydrates_of_sugars"),
                            fats=note_nutrients.get("fats"),
                            fats_saturated=note_nutrients.get("fats_saturated"),
                            salt=note_nutrients.get("salt"),
                            fibers=note_nutrients.get("fibers"),
                        )
                    )
            with contextlib.suppress(GrocyError):
                grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})
            continue

        # Standalone product
        if meal["type"] == "product":
            try:
                product_data = grocy_api.get(f"/stock/products/{meal['product_id']}")
                if product_data["stock_amount"] < meal.get("product_amount", 0):
                    skipped_meals.append(
                        {
                            "meal_plan_id": meal["id"],
                            "recipe_name": product_data.get("product", {}).get(
                                "name", f"Product #{meal['product_id']}"
                            ),
                            "reason": "Insufficient stock",
                        }
                    )
                    continue

                consume_response = grocy_api.post(
                    f"/stock/products/{meal['product_id']}/consume",
                    data={"amount": meal["product_amount"], "spoiled": 0},
                )
                grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})

                # Extract cost from consume response (list of stock_log entries)
                product_cost = None
                if isinstance(consume_response, list) and consume_response:
                    total_cost = 0.0
                    for entry in consume_response:
                        entry_amount = abs(float(entry.get("amount", 0)))
                        entry_price = float(entry.get("price", 0))
                        total_cost += entry_amount * entry_price
                    if total_cost > 0:
                        product_cost = round(total_cost, 4)

                # Save consumed product to DB
                _save_consumed_product(
                    db,
                    grocy_api,
                    meal["product_id"],
                    meal["product_amount"],
                    consume_date,
                    recipe_grocy_id=None,
                    household_id=household_id,
                    user_id=user_id,
                    cost=product_cost,
                )
                product = get_product_by_grocy_id(
                    db, grocy_id=meal["product_id"], household_id=household_id
                )
                consumed_products_list.append(
                    {
                        "grocy_id": meal["product_id"],
                        "name": product.name if product else f"Product #{meal['product_id']}",
                        "quantity": meal["product_amount"],
                        "recipe_grocy_id": None,
                    }
                )
            except GrocyError as e:
                skipped_meals.append(
                    {
                        "meal_plan_id": meal["id"],
                        "recipe_name": f"Product #{meal.get('product_id', '?')}",
                        "reason": str(e),
                    }
                )
            continue

        # Recipe
        if meal["type"] == "recipe":
            try:
                recipe_data = grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")
                recipe_name = recipe_data.get("name", f"Recipe #{meal['recipe_id']}")

                recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
                shadow_id = recipe_meal["id"]

                fulfillment = grocy_api.get(f"/recipes/{shadow_id}/fulfillment")
                if fulfillment.get("missing_products_count", 0) > 0:
                    skipped_meals.append(
                        {
                            "meal_plan_id": meal["id"],
                            "recipe_name": recipe_name,
                            "reason": f"Missing {fulfillment['missing_products_count']} products",
                        }
                    )
                    continue

                # Consume shadow recipe in Grocy (only shadow recipes with negative IDs)
                grocy_api.post(f"/recipes/{shadow_id}/consume")
                grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})

                # Read actual consumed products from stock_log filtered by shadow recipe id.
                # Grocy records every stock entry it touched (including substitutions)
                # with recipe_id = shadow_id, so this gives the real picture.
                stock_log = (
                    grocy_api.get(
                        "/objects/stock_log",
                        {
                            "query[]": [
                                f"recipe_id={shadow_id}",
                                "transaction_type=consume",
                            ]
                        },
                    )
                    or []
                )

                # Save meal plan consumption record with shadow recipe ID (dedup by meal_plan_id)
                existing_mpc = db.exec(
                    select(MealPlanConsumption).where(
                        MealPlanConsumption.meal_plan_id == meal["id"]
                    )
                ).first()
                if not existing_mpc:
                    db.add(
                        MealPlanConsumption(
                            date=consume_date,
                            meal_plan_id=meal["id"],
                            recipe_grocy_id=shadow_id,
                            household_id=household_id,
                            user_id=user_id,
                        )
                    )

                consumed_meals.append(
                    {
                        "meal_plan_id": meal["id"],
                        "recipe_grocy_id": shadow_id,
                        "recipe_name": recipe_name,
                    }
                )

                # Accumulate nutrients per recipe for recipes_data
                recipe_total_nutrients = {
                    "calories": 0.0,
                    "proteins": 0.0,
                    "carbohydrates": 0.0,
                    "carbohydrates_of_sugars": 0.0,
                    "fats": 0.0,
                    "fats_saturated": 0.0,
                    "salt": 0.0,
                    "fibers": 0.0,
                }
                recipe_products_for_data: list[dict] = []

                # Save each consumed product with recipe association (from actual stock log)
                for log_entry in stock_log:
                    grocy_product_id = log_entry.get("product_id")
                    amount = abs(float(log_entry.get("amount", 0)))
                    price_per_unit = float(log_entry.get("price", 0))
                    entry_cost = round(amount * price_per_unit, 4) if price_per_unit else None

                    _save_consumed_product(
                        db,
                        grocy_api,
                        grocy_product_id,
                        amount,
                        consume_date,
                        recipe_grocy_id=meal["recipe_id"],
                        recipe_grocy_id_shadow=shadow_id,
                        household_id=household_id,
                        user_id=user_id,
                        cost=entry_cost,
                    )

                    # Accumulate nutrients for recipe data
                    product = get_product_by_grocy_id(
                        db, grocy_id=grocy_product_id, household_id=household_id
                    )
                    if product and product.id is not None:
                        qty = amount * grocy_api.get_conversion_factor_safe(
                            grocy_product_id, product.qu_id_stock, (82, 85)
                        )
                        latest_data = get_latest_product_data(db, product.id)
                        if latest_data:
                            for key in recipe_total_nutrients:
                                val = getattr(latest_data, key, None)
                                if val:
                                    recipe_total_nutrients[key] += val * qty
                            recipe_products_for_data.append(
                                {
                                    "product_data_id": latest_data.id,
                                    "quantity": qty,
                                    "cost": entry_cost,
                                }
                            )

                    consumed_products_list.append(
                        {
                            "grocy_id": grocy_product_id,
                            "name": product.name if product else f"Product #{grocy_product_id}",
                            "quantity": amount,
                            "recipe_grocy_id": meal["recipe_id"],
                        }
                    )

                # Extract weight_per_serving from product unit conversion (portion -> grams)
                weight_per_serving = None
                linked_product_id = recipe_data.get("product_id")
                if linked_product_id:
                    try:
                        linked_product = grocy_api.get_product(linked_product_id)
                        qu_id_stock = linked_product.get("qu_id_stock")
                        if qu_id_stock and qu_id_stock not in (82, 85):
                            factor, _ = grocy_api.get_conversion_factor_with_unit(
                                str(linked_product_id), qu_id_stock, (82, 85)
                            )
                            weight_per_serving = factor
                    except GrocyError:
                        pass

                # Save recipe consumption data to recipes_data table
                _save_recipe_data(
                    db,
                    meal["recipe_id"],
                    fulfillment,
                    recipe_total_nutrients,
                    weight_per_serving,
                    consume_date,
                    user_id=user_id,
                    household_id=household_id,
                    consumed_products_data=recipe_products_for_data,
                )

                # Update linked product nutrients in Grocy and sync back
                if linked_product_id and recipe_data.get("desired_servings"):
                    try:
                        update_grocy_product_nutrients(
                            db,
                            grocy_api,
                            linked_product_id,
                            recipe_total_nutrients,
                            int(recipe_data["desired_servings"]),
                            household_id=household_id,
                        )
                    except GrocyError as nutrient_err:
                        print(
                            f"Warning: Failed to update product {linked_product_id} nutrients: {nutrient_err!s}"
                        )

            except GrocyError as e:
                skipped_meals.append(
                    {
                        "meal_plan_id": meal["id"],
                        "recipe_name": f"Recipe #{meal.get('recipe_id', '?')}",
                        "reason": str(e),
                    }
                )
                continue

    # Commit all DB changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ConsumptionError(f"Failed to save consumption data: {e!s}") from e

    consumed_count = len(consumed_meals)
    skipped_count = len(skipped_meals)
    msg = f"Consumed {consumed_count} meals ({len(consumed_products_list)} products)"
    if skipped_count > 0:
        msg += f", skipped {skipped_count} meals"

    return {
        "status": "success",
        "date": date_str,
        "consumed_meals": consumed_meals,
        "consumed_products": consumed_products_list,
        "skipped_meals": skipped_meals,
        "products_count": len(consumed_products_list),
        "message": msg,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _calc_recipe_product_amount(
    db: Session,
    grocy_api: GrocyAPI,
    pos: dict[str, Any],
    household_id: int | None = None,
) -> float:
    """Calculate the actual amount of a product from a recipe position,
    applying unit conversion if needed."""
    grocy_product_id = pos["product_id_effective"]
    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id, household_id=household_id)
    product_base = get_product_by_grocy_id(db, pos["product_id"], household_id=household_id)

    factor = 1
    if product and product_base and product.qu_id_stock and product_base.qu_id_stock:
        if product.qu_id_stock != product_base.qu_id_stock:
            factor = grocy_api.get_unit_conversion_factor(
                grocy_product_id, product_base.qu_id_stock, product.qu_id_stock
            )
    else:
        product_api = grocy_api.get_product(grocy_product_id)
        product_base_api = grocy_api.get_product(pos["product_id"])
        if product_api["qu_id_stock"] != product_base_api["qu_id_stock"]:
            factor = grocy_api.get_unit_conversion_factor(
                grocy_product_id,
                product_base_api["qu_id_stock"],
                product_api["qu_id_stock"],
            )

    return factor * pos["recipe_amount"]


def _save_consumed_product(
    db: Session,
    grocy_api: GrocyAPI,
    grocy_product_id: int,
    amount: float,
    consume_date,
    recipe_grocy_id: int | None,
    recipe_grocy_id_shadow: int | None = None,
    household_id: int | None = None,
    user_id: int | None = None,
    cost: float | None = None,
):
    """Save a single consumed product record to database."""
    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id, household_id=household_id)
    if not product:
        return

    qty = amount * grocy_api.get_conversion_factor_safe(
        grocy_product_id, product.qu_id_stock, (82, 85)
    )
    latest_data = get_latest_product_data(db, product.id)
    if not latest_data:
        return

    consumed = ConsumedProduct(
        product_data_id=latest_data.id,
        date=consume_date,
        quantity=qty,
        cost=cost,
        recipe_grocy_id=recipe_grocy_id,
        recipe_grocy_id_shadow=recipe_grocy_id_shadow,
        household_id=household_id,
        user_id=user_id,
    )
    db.add(consumed)


def _save_recipe_data(
    db: Session,
    original_recipe_grocy_id: int,
    fulfillment: dict[str, Any],
    total_nutrients: dict[str, float],
    weight_per_serving: float | None = None,
    consume_date=None,
    user_id: int | None = None,
    household_id: int | None = None,
    consumed_products_data: list[dict] | None = None,
):
    """Save recipe consumption data to recipes_data table."""
    from app.models.recipe import RecipeConsumedProduct

    stmt = select(Recipe).where(Recipe.grocy_id == original_recipe_grocy_id)
    if household_id is not None:
        stmt = stmt.where(Recipe.household_id == household_id)
    recipe = db.exec(stmt).first()
    if not recipe:
        return

    # Calculate weight_per_serving from consumed products if not provided
    if weight_per_serving is None and consumed_products_data:
        total_weight = sum(item["quantity"] for item in consumed_products_data)
        if total_weight > 0:
            weight_per_serving = round(total_weight, 4)  # servings=1 for meal plan

    recipe_data = RecipeData(
        recipe_id=recipe.id,
        servings=1,
        price_per_serving=fulfillment.get("costs"),
        weight_per_serving=weight_per_serving,
        user_id=user_id,
        calories=round(total_nutrients.get("calories", 0), 4),
        carbohydrates=round(total_nutrients.get("carbohydrates", 0), 4),
        carbohydrates_of_sugars=round(total_nutrients.get("carbohydrates_of_sugars", 0), 4),
        proteins=round(total_nutrients.get("proteins", 0), 4),
        fats=round(total_nutrients.get("fats", 0), 4),
        fats_saturated=round(total_nutrients.get("fats_saturated", 0), 4),
        salt=round(total_nutrients.get("salt", 0), 4),
        fibers=round(total_nutrients.get("fibers", 0), 4),
        consumed_date=consume_date,
    )
    db.add(recipe_data)

    if consumed_products_data:
        db.flush()
        for item in consumed_products_data:
            db.add(
                RecipeConsumedProduct(
                    recipe_data_id=recipe_data.id,
                    product_data_id=item["product_data_id"],
                    quantity=item["quantity"],
                    cost=item["cost"],
                )
            )


def _build_product_preview(
    db: Session,
    grocy_api: GrocyAPI,
    grocy_product_id: int,
    amount: float,
    household_id: int | None = None,
) -> dict[str, Any] | None:
    """Build a product preview dict with nutritional info for dry-run."""
    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id, household_id=household_id)
    if not product:
        return {
            "grocy_id": grocy_product_id,
            "product_id": None,
            "name": "Unknown (not synced)",
            "quantity": amount,
            "note": "",
        }

    qty = amount * grocy_api.get_conversion_factor_safe(
        grocy_product_id, product.qu_id_stock, (82, 85)
    )
    latest_data = get_latest_product_data(db, product.id)

    return {
        "grocy_id": grocy_product_id,
        "product_id": product.id,
        "name": product.name,
        "quantity": qty,
        "note": "",
        "calories": latest_data.calories if latest_data else None,
        "carbohydrates": latest_data.carbohydrates if latest_data else None,
        "carbohydrates_of_sugars": latest_data.carbohydrates_of_sugars if latest_data else None,
        "proteins": latest_data.proteins if latest_data else None,
        "fats": latest_data.fats if latest_data else None,
        "fats_saturated": latest_data.fats_saturated if latest_data else None,
        "salt": latest_data.salt if latest_data else None,
        "fibers": latest_data.fibers if latest_data else None,
    }


def _accumulate_nutrients(product_preview: dict[str, Any], totals: dict[str, float]):
    """Add product nutrients * quantity to running totals."""
    qty = product_preview["quantity"]
    for key in totals:
        value = product_preview.get(key)
        if value:
            totals[key] += value * qty


def _get_products_flat(
    db: Session,
    grocy_api: GrocyAPI,
    date_str: str,
    household_id: int | None = None,
) -> dict[int, dict[str, Any]]:
    """
    Get products to consume from Grocy meal plan (flat aggregated dict).
    Used by check_products_availability.
    """
    products_to_consume = {}

    try:
        meal_plan = grocy_api.get_meal_plan(day=date_str, week=None)
    except GrocyError as e:
        raise ConsumptionError(f"Failed to fetch meal plan: {e!s}") from e

    for meal in meal_plan:
        if meal["type"] == "note" or meal.get("done"):
            continue

        if meal["type"] == "recipe":
            recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
            resolved = grocy_api.get(
                "/objects/recipes_pos_resolved",
                {"query[]": [f"recipe_id={recipe_meal['id']}"]},
            )

            for pos in resolved:
                if pos["product_id_effective"] not in products_to_consume:
                    products_to_consume[pos["product_id_effective"]] = {
                        "amount": 0,
                        "note": "",
                    }

                recipe = grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")

                amount = _calc_recipe_product_amount(db, grocy_api, pos, household_id=household_id)

                products_to_consume[pos["product_id_effective"]]["amount"] += amount
                products_to_consume[pos["product_id_effective"]]["note"] += recipe["name"] + " | "
            continue

        # Regular product in meal plan
        if meal.get("product_id") not in products_to_consume:
            products_to_consume[meal["product_id"]] = {"amount": 0, "note": ""}

        products_to_consume[meal["product_id"]]["amount"] += meal.get("product_amount", 0)

    return products_to_consume
