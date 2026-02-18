"""
Consumption service - handles meal plan consumption logic
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlmodel import Session, select

from app.models.product import Product, ProductData, ConsumedProduct, MealPlanConsumption, NoteNutrients
from app.models.recipe import Recipe, RecipeData
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.product import get_product_by_grocy_id, get_latest_product_data


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


def _parse_note_nutrients(note: str) -> Dict[str, float]:
    """Parse nutrient values from a meal plan note string."""
    result: Dict[str, float] = {}
    for part in note.split("/"):
        kv = part.split(":")
        if len(kv) == 2:
            key = _NOTE_NUTRIENT_MAP.get(kv[0].strip())
            if key:
                try:
                    result[key] = float(kv[1].strip())
                except ValueError:
                    pass
    return result


def check_products_availability(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[str, Any]:
    """
    Check if all products from meal plan are available in stock
    """
    try:
        consume_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    products_to_consume = _get_products_flat(db, grocy_api, date_str)

    products_to_buy = {}
    products_to_buy_detailed = []
    products_to_consume_detailed = []

    for product_id, product_info in products_to_consume.items():
        if product_id is None:
            continue

        product = get_product_by_grocy_id(db, grocy_id=product_id)
        product_name = product.name if product else f"Product #{product_id}"

        if not product:
            try:
                grocy_product = grocy_api.get_product(product_id)
                product_name = grocy_product.get("name", f"Product #{product_id}")
            except GrocyError:
                product_name = f"Product #{product_id}"

        try:
            data = grocy_api.get(f"/stock/products/{product_id}")
            if product_info["amount"] > data["stock_amount_aggregated"]:
                shortage = round(product_info["amount"] - data["stock_amount_aggregated"], 2)
                products_to_buy[product_id] = {
                    "amount": shortage,
                    "note": product_info["note"]
                }
                products_to_buy_detailed.append({
                    "product_id": product_id,
                    "name": product_name,
                    "amount": shortage,
                    "note": product_info["note"]
                })

            products_to_consume_detailed.append({
                "product_id": product_id,
                "name": product_name,
                "amount": product_info["amount"],
                "note": product_info["note"]
            })
        except GrocyError as e:
            print(f"Error checking product {product_id}: {str(e)}")
            continue

    if len(products_to_buy) > 0:
        return {
            "status": "insufficient_stock",
            "products_to_consume": products_to_consume,
            "products_to_buy": products_to_buy,
            "products_to_buy_detailed": products_to_buy_detailed,
            "products_to_consume_detailed": products_to_consume_detailed,
            "message": "Some products are not available in sufficient quantity"
        }
    else:
        return {
            "status": "success",
            "products_to_consume": products_to_consume,
            "products_to_buy": {},
            "products_to_buy_detailed": [],
            "products_to_consume_detailed": products_to_consume_detailed,
            "message": "All products are available"
        }


def create_shopping_list(
    grocy_api: GrocyAPI, date_str: str, products_to_buy: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create shopping list in Grocy
    """
    grocy_api.create_shopping_list(date_str, None, products_to_buy)

    return {
        "status": "success",
        "message": f"Shopping list created for {date_str}",
        "products_count": len(products_to_buy)
    }


def dry_run_consumption(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[str, Any]:
    """
    Dry run - show what products will be consumed, grouped by meal/recipe
    """
    try:
        consume_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    try:
        meal_plan = grocy_api.get_meal_plan(day=date_str, week=None)
    except GrocyError as e:
        raise ConsumptionError(f"Failed to fetch meal plan: {str(e)}") from e

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
                meals_preview.append({
                    "type": "note",
                    "recipe_name": meal.get("note"),
                    "recipe_grocy_id": None,
                    "available": True,
                    "missing_products_count": 0,
                    "products": [],
                    "note_nutrients": note_nutrients,
                })
            continue

        if meal["type"] == "product":
            product_preview = _build_product_preview(
                db, grocy_api, meal["product_id"], meal.get("product_amount", 0)
            )
            if product_preview:
                # Check stock for standalone product
                is_available = True
                try:
                    stock_data = grocy_api.get(f"/stock/products/{meal['product_id']}")
                    if stock_data["stock_amount"] < meal.get("product_amount", 0):
                        is_available = False
                except GrocyError:
                    is_available = False

                if is_available:
                    _accumulate_nutrients(product_preview, total_nutrients)
                    total_calories += (product_preview.get("calories") or 0) * product_preview["quantity"]

                meals_preview.append({
                    "type": "product",
                    "recipe_name": None,
                    "recipe_grocy_id": None,
                    "available": is_available,
                    "missing_products_count": 0 if is_available else 1,
                    "products": [product_preview],
                })
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
                "/objects/recipes_pos_resolved",
                {"query[]": [f"recipe_id={shadow_id}"]}
            )

            recipe_products = []
            for pos in resolved:
                grocy_product_id = pos["product_id_effective"]
                amount = _calc_recipe_product_amount(db, grocy_api, pos)

                product_preview = _build_product_preview(
                    db, grocy_api, grocy_product_id, amount
                )
                if product_preview:
                    # Only count nutrients for available recipes
                    if is_available:
                        _accumulate_nutrients(product_preview, total_nutrients)
                        total_calories += (product_preview.get("calories") or 0) * product_preview["quantity"]
                    recipe_products.append(product_preview)
                    total_products_count += 1

            meals_preview.append({
                "type": "recipe",
                "recipe_name": recipe_name,
                "recipe_grocy_id": meal["recipe_id"],
                "available": is_available,
                "missing_products_count": missing_count,
                "products": recipe_products,
            })

    return {
        "status": "success",
        "date": date_str,
        "meals": meals_preview,
        "total_calories": round(total_calories, 2),
        "total_nutrients": {k: round(v, 2) for k, v in total_nutrients.items()},
        "products_count": total_products_count,
    }


def execute_consumption(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[str, Any]:
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
        raise ConsumptionError(f"Failed to fetch meal plan: {str(e)}") from e

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
                db.add(NoteNutrients(
                    date=consume_date,
                    note=note_text,
                    calories=note_nutrients.get("calories"),
                    proteins=note_nutrients.get("proteins"),
                    carbohydrates=note_nutrients.get("carbohydrates"),
                    carbohydrates_of_sugars=note_nutrients.get("carbohydrates_of_sugars"),
                    fats=note_nutrients.get("fats"),
                    fats_saturated=note_nutrients.get("fats_saturated"),
                    salt=note_nutrients.get("salt"),
                    fibers=note_nutrients.get("fibers"),
                ))
            try:
                grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})
            except GrocyError:
                pass
            continue

        # Standalone product
        if meal["type"] == "product":
            try:
                product_data = grocy_api.get(f"/stock/products/{meal['product_id']}")
                if product_data["stock_amount"] < meal.get("product_amount", 0):
                    skipped_meals.append({
                        "meal_plan_id": meal["id"],
                        "recipe_name": product_data.get("product", {}).get("name", f"Product #{meal['product_id']}"),
                        "reason": "Insufficient stock",
                    })
                    continue

                grocy_api.post(
                    f"/stock/products/{meal['product_id']}/consume",
                    data={"amount": meal["product_amount"], "spoiled": 0},
                )
                grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})

                # Save consumed product to DB
                _save_consumed_product(
                    db, grocy_api, meal["product_id"], meal["product_amount"],
                    consume_date, recipe_grocy_id=None,
                )
                product = get_product_by_grocy_id(db, grocy_id=meal["product_id"])
                consumed_products_list.append({
                    "grocy_id": meal["product_id"],
                    "name": product.name if product else f"Product #{meal['product_id']}",
                    "quantity": meal["product_amount"],
                    "recipe_grocy_id": None,
                })
            except GrocyError as e:
                skipped_meals.append({
                    "meal_plan_id": meal["id"],
                    "recipe_name": f"Product #{meal.get('product_id', '?')}",
                    "reason": str(e),
                })
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
                    skipped_meals.append({
                        "meal_plan_id": meal["id"],
                        "recipe_name": recipe_name,
                        "reason": f"Missing {fulfillment['missing_products_count']} products",
                    })
                    continue

                # Get resolved products before consuming (for saving to DB)
                resolved = grocy_api.get(
                    "/objects/recipes_pos_resolved",
                    {"query[]": [f"recipe_id={shadow_id}"]}
                )

                # Consume shadow recipe in Grocy (only shadow recipes with negative IDs)
                grocy_api.post(f"/recipes/{shadow_id}/consume")
                grocy_api.put(f"/objects/meal_plan/{meal['id']}", data={"done": 1})

                # Save meal plan consumption record with shadow recipe ID
                meal_plan_record = MealPlanConsumption(
                    date=consume_date,
                    meal_plan_id=meal["id"],
                    recipe_grocy_id=shadow_id,
                )
                db.add(meal_plan_record)

                consumed_meals.append({
                    "meal_plan_id": meal["id"],
                    "recipe_grocy_id": shadow_id,
                    "recipe_name": recipe_name,
                })

                # Accumulate nutrients per recipe for recipes_data
                recipe_total_nutrients = {
                    "calories": 0.0, "proteins": 0.0,
                    "carbohydrates": 0.0, "carbohydrates_of_sugars": 0.0,
                    "fats": 0.0, "fats_saturated": 0.0,
                    "salt": 0.0, "fibers": 0.0,
                }

                # Save each consumed product with recipe association
                for pos in resolved:
                    grocy_product_id = pos["product_id_effective"]
                    amount = _calc_recipe_product_amount(db, grocy_api, pos)

                    _save_consumed_product(
                        db, grocy_api, grocy_product_id, amount,
                        consume_date, recipe_grocy_id=meal["recipe_id"],
                        recipe_grocy_id_shadow=shadow_id,
                    )

                    # Accumulate nutrients for recipe data
                    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id)
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

                    consumed_products_list.append({
                        "grocy_id": grocy_product_id,
                        "name": product.name if product else f"Product #{grocy_product_id}",
                        "quantity": amount,
                        "recipe_grocy_id": meal["recipe_id"],
                    })

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
                    db, meal["recipe_id"], fulfillment, recipe_total_nutrients, weight_per_serving, consume_date
                )

            except GrocyError as e:
                skipped_meals.append({
                    "meal_plan_id": meal["id"],
                    "recipe_name": f"Recipe #{meal.get('recipe_id', '?')}",
                    "reason": str(e),
                })
                continue

    # Commit all DB changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ConsumptionError(f"Failed to save consumption data: {str(e)}") from e

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
    db: Session, grocy_api: GrocyAPI, pos: Dict[str, Any]
) -> float:
    """Calculate the actual amount of a product from a recipe position,
    applying unit conversion if needed."""
    grocy_product_id = pos["product_id_effective"]
    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id)
    product_base = get_product_by_grocy_id(db, pos["product_id"])

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
                grocy_product_id, product_base_api["qu_id_stock"], product_api["qu_id_stock"]
            )

    return factor * pos["recipe_amount"]


def _save_consumed_product(
    db: Session, grocy_api: GrocyAPI,
    grocy_product_id: int, amount: float,
    consume_date, recipe_grocy_id: Optional[int],
    recipe_grocy_id_shadow: Optional[int] = None,
):
    """Save a single consumed product record to database."""
    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id)
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
        recipe_grocy_id=recipe_grocy_id,
        recipe_grocy_id_shadow=recipe_grocy_id_shadow,
    )
    db.add(consumed)


def _save_recipe_data(
    db: Session,
    original_recipe_grocy_id: int,
    fulfillment: Dict[str, Any],
    total_nutrients: Dict[str, float],
    weight_per_serving: Optional[float] = None,
    consume_date=None,
):
    """Save recipe consumption data to recipes_data table."""
    recipe = db.exec(
        select(Recipe).where(Recipe.grocy_id == original_recipe_grocy_id)
    ).first()
    if not recipe:
        return

    recipe_data = RecipeData(
        recipe_id=recipe.id,
        servings=1,
        price_per_serving=fulfillment.get("costs"),
        weight_per_serving=weight_per_serving,
        calories=round(total_nutrients.get("calories", 0), 2),
        carbohydrates=round(total_nutrients.get("carbohydrates", 0), 2),
        carbohydrates_of_sugars=round(total_nutrients.get("carbohydrates_of_sugars", 0), 2),
        proteins=round(total_nutrients.get("proteins", 0), 2),
        fats=round(total_nutrients.get("fats", 0), 2),
        fats_saturated=round(total_nutrients.get("fats_saturated", 0), 2),
        salt=round(total_nutrients.get("salt", 0), 2),
        fibers=round(total_nutrients.get("fibers", 0), 2),
        consumed_date=consume_date,
    )
    db.add(recipe_data)


def _build_product_preview(
    db: Session, grocy_api: GrocyAPI,
    grocy_product_id: int, amount: float,
) -> Optional[Dict[str, Any]]:
    """Build a product preview dict with nutritional info for dry-run."""
    product = get_product_by_grocy_id(db, grocy_id=grocy_product_id)
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


def _accumulate_nutrients(product_preview: Dict[str, Any], totals: Dict[str, float]):
    """Add product nutrients * quantity to running totals."""
    qty = product_preview["quantity"]
    for key in totals:
        value = product_preview.get(key)
        if value:
            totals[key] += value * qty


def _get_products_flat(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[int, Dict[str, Any]]:
    """
    Get products to consume from Grocy meal plan (flat aggregated dict).
    Used by check_products_availability.
    """
    products_to_consume = {}

    try:
        meal_plan = grocy_api.get_meal_plan(day=date_str, week=None)
    except GrocyError as e:
        raise ConsumptionError(f"Failed to fetch meal plan: {str(e)}") from e

    for meal in meal_plan:
        if meal["type"] == "note" or meal.get("done"):
            continue

        if meal["type"] == "recipe":
            recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
            resolved = grocy_api.get("/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={recipe_meal['id']}"]})

            for pos in resolved:
                if pos["product_id_effective"] not in products_to_consume:
                    products_to_consume[pos["product_id_effective"]] = {"amount": 0, "note": ""}

                recipe = grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")

                amount = _calc_recipe_product_amount(db, grocy_api, pos)

                products_to_consume[pos["product_id_effective"]]["amount"] += amount
                products_to_consume[pos["product_id_effective"]]["note"] += recipe["name"] + " | "
            continue

        # Regular product in meal plan
        if meal.get("product_id") not in products_to_consume:
            products_to_consume[meal["product_id"]] = {"amount": 0, "note": ""}

        products_to_consume[meal["product_id"]]["amount"] += meal.get("product_amount", 0)

    return products_to_consume
