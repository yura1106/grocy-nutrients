"""
Consumption service - handles meal plan consumption logic
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlmodel import Session

from app.models.product import Product, ProductData, ConsumedProduct
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.product import get_product_by_grocy_id, get_latest_product_data


class ConsumptionError(Exception):
    """Exception raised during consumption processing"""
    pass


def check_products_availability(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[str, Any]:
    """
    Check if all products from meal plan are available in stock

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Dict with availability status and products to buy if needed
    """
    # Parse date
    try:
        consume_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    # Get products to consume from meal plan
    products_to_consume = _get_products_from_meal_plan(db, grocy_api, date_str)

    # Check availability and build detailed product lists
    products_to_buy = {}
    products_to_buy_detailed = []
    products_to_consume_detailed = []

    for product_id, product_info in products_to_consume.items():
        if product_id is None:
            continue

        # Get product name from local DB or Grocy API
        product = get_product_by_grocy_id(db, grocy_id=product_id)
        product_name = product.name if product else f"Product #{product_id}"

        # If not in local DB, try to get from Grocy API
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

            # Add to consume list
            products_to_consume_detailed.append({
                "product_id": product_id,
                "name": product_name,
                "amount": product_info["amount"],
                "note": product_info["note"]
            })
        except GrocyError as e:
            print(f"Error checking product {product_id}: {str(e)}")
            continue

    # Return result
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

    Args:
        grocy_api: Initialized GrocyAPI instance
        date_str: Date string in YYYY-MM-DD format
        products_to_buy: Dict of products to buy {product_id: {amount, note}}

    Returns:
        Dict with shopping list creation status
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
    Dry run - show what products will be consumed without actually consuming them

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Dict with list of products that will be consumed
    """
    # Parse date
    try:
        consume_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    # Get products to consume from meal plan
    products_to_consume = _get_products_from_meal_plan(db, grocy_api, date_str)

    # Build detailed consumption preview
    consumption_preview = []
    total_calories = 0
    total_nutrients = {
        "carbohydrates": 0,
        "carbohydrates_of_sugars": 0,
        "proteins": 0,
        "fats": 0,
        "fats_saturated": 0,
        "salt": 0,
        "fibers": 0
    }

    for grocy_product_id, product_info in products_to_consume.items():
        if grocy_product_id is None:
            continue

        # Get product from local DB
        product = get_product_by_grocy_id(db, grocy_id=grocy_product_id)

        if product:
            latest_data = get_latest_product_data(db, product.id)

            product_preview = {
                "grocy_id": grocy_product_id,
                "product_id": product.id,
                "name": product.name,
                "quantity": product_info["amount"],
                "note": product_info["note"],
                "calories": latest_data.calories if latest_data else None,
                "carbohydrates": latest_data.carbohydrates if latest_data else None,
                "carbohydrates_of_sugars": latest_data.carbohydrates_of_sugars if latest_data else None,
                "proteins": latest_data.proteins if latest_data else None,
                "fats": latest_data.fats if latest_data else None,
                "fats_saturated": latest_data.fats_saturated if latest_data else None,
                "salt": latest_data.salt if latest_data else None,
                "fibers": latest_data.fibers if latest_data else None,
            }

            # Calculate totals
            if latest_data:
                qty = product_info["amount"]
                if latest_data.calories:
                    total_calories += latest_data.calories * qty
                if latest_data.carbohydrates:
                    total_nutrients["carbohydrates"] += latest_data.carbohydrates * qty
                if latest_data.carbohydrates_of_sugars:
                    total_nutrients["carbohydrates_of_sugars"] += latest_data.carbohydrates_of_sugars * qty
                if latest_data.proteins:
                    total_nutrients["proteins"] += latest_data.proteins * qty
                if latest_data.fats:
                    total_nutrients["fats"] += latest_data.fats * qty
                if latest_data.fats_saturated:
                    total_nutrients["fats_saturated"] += latest_data.fats_saturated * qty
                if latest_data.salt:
                    total_nutrients["salt"] += latest_data.salt * qty
                if latest_data.fibers:
                    total_nutrients["fibers"] += latest_data.fibers * qty

            consumption_preview.append(product_preview)
        else:
            # Product not in local DB
            consumption_preview.append({
                "grocy_id": grocy_product_id,
                "product_id": None,
                "name": "Unknown (not synced)",
                "quantity": product_info["amount"],
                "note": product_info["note"],
            })

    return {
        "status": "success",
        "date": date_str,
        "products": consumption_preview,
        "total_calories": round(total_calories, 2),
        "total_nutrients": {
            "carbohydrates": round(total_nutrients["carbohydrates"], 2),
            "carbohydrates_of_sugars": round(total_nutrients["carbohydrates_of_sugars"], 2),
            "proteins": round(total_nutrients["proteins"], 2),
            "fats": round(total_nutrients["fats"], 2),
            "fats_saturated": round(total_nutrients["fats_saturated"], 2),
            "salt": round(total_nutrients["salt"], 2),
            "fibers": round(total_nutrients["fibers"], 2),
        },
        "products_count": len(consumption_preview)
    }


def execute_consumption(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[str, Any]:
    """
    Execute consumption - actually consume products and save to database

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Dict with consumed products info
    """
    # Parse date
    try:
        consume_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    # Get products to consume from meal plan
    products_to_consume = _get_products_from_meal_plan(db, grocy_api, date_str)

    # TODO: Implement actual consumption logic in Grocy
    # Example:
    # for grocy_product_id, product_info in products_to_consume.items():
    #     grocy_api.consume_product(grocy_product_id, product_info["amount"])

    # Save consumed products to database
    consumed_products = []
    for grocy_product_id, product_info in products_to_consume.items():
        if grocy_product_id is None:
            continue

        # Get product from local DB
        product = get_product_by_grocy_id(db, grocy_id=grocy_product_id)

        if product:
            latest_data = get_latest_product_data(db, product.id)

            if latest_data:
                # Save consumed product
                consumed_product = ConsumedProduct(
                    product_data_id=latest_data.id,
                    date=consume_date,
                    quantity=product_info["amount"]
                )
                db.add(consumed_product)

                consumed_products.append({
                    "grocy_id": grocy_product_id,
                    "name": product.name,
                    "quantity": product_info["amount"],
                    "note": product_info["note"]
                })

    # Commit changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ConsumptionError(f"Failed to save consumed products: {str(e)}") from e

    return {
        "status": "success",
        "date": date_str,
        "consumed_products": consumed_products,
        "products_count": len(consumed_products),
        "message": f"Successfully consumed {len(consumed_products)} products"
    }


def _get_products_from_meal_plan(
    db: Session, grocy_api: GrocyAPI, date_str: str
) -> Dict[int, Dict[str, Any]]:
    """
    Get products to consume from Grocy meal plan

    Internal helper function
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
                factor = 1
                if pos["product_id_effective"] not in products_to_consume:
                    products_to_consume[pos["product_id_effective"]] = {"amount": 0, "note": ""}

                recipe = grocy_api.get(f"/objects/recipes/{meal['recipe_id']}")

                # Get products from local database instead of API
                product = get_product_by_grocy_id(db, pos["product_id_effective"])
                product_base = get_product_by_grocy_id(db, pos["product_id"])

                # Check if products exist and have qu_id_stock populated
                if product and product_base and product.qu_id_stock and product_base.qu_id_stock:
                    if product.qu_id_stock != product_base.qu_id_stock:
                        factor = grocy_api.get_unit_conversion_factor(
                            pos["product_id_effective"],
                            product_base.qu_id_stock,
                            product.qu_id_stock
                        )
                else:
                    # Fallback: if products not in DB or qu_id_stock is None, fetch from API
                    product_api = grocy_api.get_product(pos["product_id_effective"])
                    product_base_api = grocy_api.get_product(pos["product_id"])

                    if product_api["qu_id_stock"] != product_base_api["qu_id_stock"]:
                        factor = grocy_api.get_unit_conversion_factor(
                            pos["product_id_effective"],
                            product_base_api["qu_id_stock"],
                            product_api["qu_id_stock"]
                        )

                products_to_consume[pos["product_id_effective"]]["amount"] += factor * pos["recipe_amount"]
                products_to_consume[pos["product_id_effective"]]["note"] += recipe["name"] + " | "
            continue

        # Regular product in meal plan
        if meal.get("product_id") not in products_to_consume:
            products_to_consume[meal["product_id"]] = {"amount": 0, "note": ""}

        products_to_consume[meal["product_id"]]["amount"] += meal.get("product_amount", 0)

    return products_to_consume
