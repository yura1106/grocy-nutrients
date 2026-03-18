from sqlalchemy import nullslast
from sqlmodel import Session, col, desc, func, or_, select

from app.models.recipe import Recipe, RecipeConsumedProduct, RecipeData
from app.schemas.recipe import (
    MissingNutrients,
    RecipeCalculateResponse,
    RecipeConsumedProductItem,
    RecipeConsumedProductsResponse,
    RecipeConsumeResponse,
    RecipeDataSaveResponse,
    RecipeDetailResponse,
    RecipeFulfillment,
    RecipeHistoryItem,
    RecipeIngredient,
    RecipeNutrients,
    RecipesListResponse,
    RecipesSyncAllResponse,
    RecipeSyncResponse,
    RecipeWithData,
)
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.product import (
    get_latest_product_data,
    get_product_by_grocy_id,
    update_grocy_product_nutrients,
)


class RecipeCalculationError(Exception):
    """Exception raised during recipe calculation"""

    pass


# Unit IDs from the original script
GRAM_UNIT_ID = 82
ML_UNIT_ID = 85
PORTION_UNIT_ID = 103


def calculate_recipe_nutrients(
    db: Session,
    grocy_api: GrocyAPI,
    recipe_id: int,
    include_missing: bool = True,
    household_id: int | None = None,
) -> RecipeCalculateResponse:
    """
    Calculate nutrients for a recipe based on its ingredients

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        recipe_id: Recipe ID to calculate
        include_missing: Whether to include missing nutrients data

    Returns:
        RecipeCalculateResponse with all recipe data

    Raises:
        RecipeCalculationError: If calculation fails
    """
    try:
        # Fetch recipe info
        recipe_data = grocy_api.get("/objects/recipes", {"query[]": [f"id={recipe_id}"]})
        if not recipe_data or len(recipe_data) == 0:
            raise RecipeCalculationError(f"Recipe {recipe_id} not found")

        recipe_info = recipe_data[0]

        # Initialize nutrient tracking
        nutrients = RecipeNutrients(
            calories=0,
            proteins=0,
            carbohydrates=0,
            carbohydrates_of_sugars=0,
            fats=0,
            fats_saturated=0,
            salt=0,
            fibers=0,
        )

        missing_nutrients = MissingNutrients() if include_missing else None
        ingredients: list[RecipeIngredient] = []

        # Process nested recipes first
        nested_recipes = grocy_api.get(
            "/objects/recipes_nestings", {"query[]": [f"recipe_id={recipe_id}"]}
        )
        for nested_recipe in nested_recipes:
            _process_recipe(
                grocy_api,
                db,
                str(nested_recipe["includes_recipe_id"]),
                nutrients,
                missing_nutrients,
                ingredients,
                household_id=household_id,
            )

        # Process main recipe
        _process_recipe(
            grocy_api,
            db,
            str(recipe_id),
            nutrients,
            missing_nutrients,
            ingredients,
            household_id=household_id,
        )

        # Get fulfillment data
        fulfillment_data = grocy_api.get(f"/recipes/{recipe_id}/fulfillment")
        fulfillment = RecipeFulfillment(**fulfillment_data)

        # Check if recipe has associated product
        has_product = recipe_info.get("product_id") is not None
        per_serving_nutrients = None
        weight_per_serving = None
        product_conversion_factor = None
        product_conversion_unit = None
        product_qu_id_stock = None
        product_conversion_target_qu_id = None

        if has_product:
            recipe_product_id = recipe_info["product_id"]
            recipe_product = grocy_api.get_product(recipe_product_id)
            product_qu_id_stock = recipe_product["qu_id_stock"]
            if product_qu_id_stock != GRAM_UNIT_ID and product_qu_id_stock != ML_UNIT_ID:
                factor_val, unit_id = grocy_api.get_conversion_factor_with_unit(
                    str(recipe_product_id),
                    product_qu_id_stock,
                    (GRAM_UNIT_ID, ML_UNIT_ID),
                )
                if factor_val is not None:
                    product_conversion_factor = factor_val
                    product_conversion_unit = "g" if unit_id == GRAM_UNIT_ID else "ml"
                    product_conversion_target_qu_id = unit_id
                    weight_per_serving = factor_val

        if has_product and recipe_info.get("desired_servings"):
            desired_servings = int(recipe_info["desired_servings"])
            per_serving_nutrients = RecipeNutrients(
                calories=nutrients.calories / desired_servings,
                proteins=nutrients.proteins / desired_servings,
                carbohydrates=nutrients.carbohydrates / desired_servings,
                carbohydrates_of_sugars=nutrients.carbohydrates_of_sugars / desired_servings,
                fats=nutrients.fats / desired_servings,
                fats_saturated=nutrients.fats_saturated / desired_servings,
                salt=nutrients.salt / desired_servings,
                fibers=nutrients.fibers / desired_servings,
            )

        # Determine message based on status
        can_consume = fulfillment.missing_products_count == 0
        if not has_product:
            message = "Recipe has no associated product. Nutrients calculated but cannot be saved."
        elif not can_consume:
            message = (
                f"Missing {fulfillment.missing_products_count} products. Cannot consume recipe."
            )
        else:
            message = "Recipe can be consumed!"

        # Build product URL if exists
        product_url = None
        if has_product:
            product_url = f"{grocy_api.get_base_url()}/product/{recipe_info['product_id']}"

        return RecipeCalculateResponse(
            status="success",
            recipe_id=recipe_id,
            recipe_name=recipe_info.get("name", f"Recipe {recipe_id}"),
            has_product=has_product,
            product_id=recipe_info.get("product_id"),
            product_url=product_url,
            desired_servings=recipe_info.get("desired_servings"),
            weight_per_serving=weight_per_serving,
            product_conversion_factor=product_conversion_factor,
            product_conversion_unit=product_conversion_unit,
            product_qu_id_stock=product_qu_id_stock,
            product_conversion_target_qu_id=product_conversion_target_qu_id,
            ingredients=ingredients,
            total_nutrients=nutrients,
            per_serving_nutrients=per_serving_nutrients,
            fulfillment=fulfillment,
            missing_nutrients=missing_nutrients,
            can_consume=can_consume,
            message=message,
        )

    except GrocyError as e:
        raise RecipeCalculationError(f"Grocy API error: {e!s}") from e
    except Exception as e:
        raise RecipeCalculationError(f"Calculation error: {e!s}") from e


def _process_recipe(
    grocy_api: GrocyAPI,
    db: Session,
    recipe_id: str,
    nutrients: RecipeNutrients,
    missing_nutrients: MissingNutrients | None,
    ingredients: list[RecipeIngredient],
    household_id: int | None = None,
) -> None:
    """
    Process a single recipe and update nutrients

    This is based on the process_recipe function from recipe_nutrients.py
    """
    resolved = grocy_api.get(
        "/objects/recipes_pos_resolved", {"query[]": [f"recipe_id={recipe_id}"]}
    )

    for pos in resolved:
        product_id = pos["product_id"]
        product_id_effective = pos["product_id_effective"]

        # Get product from local DB for basic info (name, qu_id_stock)
        local_product = get_product_by_grocy_id(
            db, product_id_effective, household_id=household_id
        )

        # Add to ingredients list using local DB data
        ingredients.append(
            RecipeIngredient(
                product_id=product_id,
                product_id_effective=product_id_effective,
                name=local_product.name if local_product else f"Product #{product_id_effective}",
                amount=pos["recipe_amount"],
                unit=None,  # Could fetch unit name if needed
            )
        )

        # Get qu_id_stock for both base and effective products
        local_product_base = get_product_by_grocy_id(db, product_id, household_id=household_id)
        if local_product and local_product.qu_id_stock is not None:
            qu_id_stock = local_product.qu_id_stock
        else:
            # Fallback to API if not in local DB
            grocy_product = grocy_api.get_product(product_id_effective)
            qu_id_stock = grocy_product["qu_id_stock"]

        if local_product_base and local_product_base.qu_id_stock is not None:
            qu_id_stock_base = local_product_base.qu_id_stock
        else:
            grocy_product_base = grocy_api.get_product(product_id)
            qu_id_stock_base = grocy_product_base["qu_id_stock"]

        # Step 1: convert from base stock unit to effective stock unit (if they differ)
        factor = 1
        if qu_id_stock != qu_id_stock_base:
            factor = grocy_api.get_unit_conversion_factor(
                product_id_effective, qu_id_stock_base, qu_id_stock
            )

        # Step 2: convert from effective stock unit to grams/ml
        amount_in_stock_units = pos["recipe_amount"] * factor
        grams_factor = grocy_api.get_conversion_factor_safe(
            product_id_effective, qu_id_stock, (GRAM_UNIT_ID, ML_UNIT_ID)
        )

        _increase_nutrients_from_product(
            db,
            nutrients,
            missing_nutrients,
            product_id_effective,
            local_product.name if local_product else f"Product #{product_id_effective}",
            qu_id_stock,
            amount_in_stock_units * grams_factor,
            household_id=household_id,
        )


def _increase_nutrients_from_product(
    db: Session,
    nutrients: RecipeNutrients,
    missing_nutrients: MissingNutrients | None,
    product_id: int,
    product_name: str,
    qu_id_stock: int,
    amount: float,
    household_id: int | None = None,
) -> None:
    """
    Add product nutrients to total

    This is based on the increaseNutrientsFromProduct function from recipe_nutrients.py
    """
    product_id_str = str(product_id)

    # Get calories from local DB (always stored per gram)
    local_product = get_product_by_grocy_id(db, product_id, household_id=household_id)
    local_data = (
        get_latest_product_data(db, local_product.id)
        if local_product and local_product.id
        else None
    )
    if not local_data:
        # No local data — mark all nutrients as missing
        if missing_nutrients and qu_id_stock != PORTION_UNIT_ID:
            for field in [
                "calories",
                "proteins",
                "carbohydrates",
                "carbohydrates_of_sugars",
                "fats",
                "fats_saturated",
                "salt",
                "fibers",
            ]:
                getattr(missing_nutrients, field).append(f"{product_id_str}. {product_name}")
        return

    # All nutrient fields in local DB are stored per gram
    nutrient_fields = [
        "calories",
        "proteins",
        "carbohydrates",
        "carbohydrates_of_sugars",
        "fats",
        "fats_saturated",
        "salt",
        "fibers",
    ]

    for field in nutrient_fields:
        value = float(getattr(local_data, field) or 0)

        if value == 0 and missing_nutrients and qu_id_stock != PORTION_UNIT_ID:
            getattr(missing_nutrients, field).append(f"{product_id_str}. {product_name}")

        current_value = getattr(nutrients, field)
        setattr(nutrients, field, round(current_value + (value * amount), 2))


def consume_recipe(
    db: Session,
    grocy_api: GrocyAPI,
    recipe_id: int,
    servings: int | None = None,
    price_per_serving: float | None = None,
    weight_per_serving: float | None = None,
    per_serving_nutrients: RecipeNutrients | None = None,
    household_id: int | None = None,
    user_id: int | None = None,
) -> RecipeConsumeResponse:
    """
    Consume a recipe in Grocy and optionally save consumption data

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        recipe_id: Recipe ID to consume
        servings: Number of servings (optional, for saving data)
        price_per_serving: Price per serving (optional, for saving data)
        per_serving_nutrients: Nutrients per serving (optional, for saving data)

    Returns:
        RecipeConsumeResponse

    Raises:
        RecipeCalculationError: If consumption fails
    """
    try:
        # First check if recipe can be consumed
        fulfillment_data = grocy_api.get(f"/recipes/{recipe_id}/fulfillment")

        if fulfillment_data["missing_products_count"] > 0:
            return RecipeConsumeResponse(
                status="error",
                recipe_id=recipe_id,
                message=f"Cannot consume: {fulfillment_data['missing_products_count']} products missing",
                consumed=False,
            )

        # Capture max stock_log id before consuming (to distinguish new entries)
        max_log_id = 0
        try:
            latest_log = grocy_api.get(
                "/objects/stock_log",
                {"order": "id:desc", "limit": 1},
            )
            if latest_log:
                max_log_id = latest_log[0].get("id", 0)
        except GrocyError:
            pass

        # Consume the recipe in Grocy
        grocy_api.post(f"/recipes/{recipe_id}/consume")

        # Read stock_log to get actual consumed products
        consumed_products_data: list[dict] = []
        try:
            stock_log = (
                grocy_api.get(
                    "/objects/stock_log",
                    {"query[]": [f"recipe_id={recipe_id}", "transaction_type=consume"]},
                )
                or []
            )
            for log_entry in stock_log:
                if log_entry.get("id", 0) <= max_log_id:
                    continue
                grocy_product_id = log_entry.get("product_id")
                amount = abs(float(log_entry.get("amount", 0)))
                price_per_unit = float(log_entry.get("price", 0))
                entry_cost = round(amount * price_per_unit, 4) if price_per_unit else None

                product = get_product_by_grocy_id(
                    db, grocy_id=grocy_product_id, household_id=household_id
                )
                if not product:
                    continue
                qty = amount * grocy_api.get_conversion_factor_safe(
                    grocy_product_id, product.qu_id_stock, (GRAM_UNIT_ID, ML_UNIT_ID)
                )
                latest_data = get_latest_product_data(db, product.id)
                if latest_data:
                    consumed_products_data.append(
                        {
                            "product_data_id": latest_data.id,
                            "quantity": qty,
                            "cost": entry_cost,
                        }
                    )
        except GrocyError:
            pass

        # Update linked product nutrients in Grocy if nutrients are provided
        if per_serving_nutrients is not None and servings is not None and servings > 0:
            recipe_data = grocy_api.get("/objects/recipes", {"query[]": [f"id={recipe_id}"]})
            if (
                recipe_data
                and recipe_data[0].get("product_id")
                and recipe_data[0].get("desired_servings")
            ):
                linked_product_id = recipe_data[0]["product_id"]
                desired_servings = int(recipe_data[0]["desired_servings"])
                total_nutrients = {
                    field: getattr(per_serving_nutrients, field) * servings
                    for field in [
                        "calories",
                        "proteins",
                        "carbohydrates",
                        "carbohydrates_of_sugars",
                        "fats",
                        "fats_saturated",
                        "salt",
                        "fibers",
                    ]
                }
                try:
                    update_grocy_product_nutrients(
                        db,
                        grocy_api,
                        linked_product_id,
                        total_nutrients,
                        desired_servings,
                        household_id=household_id,
                    )
                except GrocyError as e:
                    print(
                        f"Warning: Failed to update product {linked_product_id} nutrients: {e!s}"
                    )

        # Save consumption data to local DB if provided
        if servings is not None and per_serving_nutrients is not None:
            try:
                save_recipe_consumption_data(
                    db=db,
                    grocy_recipe_id=recipe_id,
                    servings=servings,
                    price_per_serving=price_per_serving,
                    weight_per_serving=weight_per_serving,
                    per_serving_nutrients=per_serving_nutrients,
                    user_id=user_id,
                    household_id=household_id,
                    consumed_products_data=consumed_products_data or None,
                )
            except Exception as e:
                # Log error but don't fail the consumption
                print(f"Warning: Failed to save recipe consumption data: {e!s}")

        return RecipeConsumeResponse(
            status="success",
            recipe_id=recipe_id,
            message="Recipe consumed successfully!",
            consumed=True,
        )

    except GrocyError as e:
        raise RecipeCalculationError(f"Failed to consume recipe: {e!s}") from e
    except Exception as e:
        raise RecipeCalculationError(f"Consumption error: {e!s}") from e


# ===== Local Recipe Storage Functions =====


def get_recipe_by_grocy_id(
    db: Session,
    grocy_id: int,
    household_id: int | None = None,
) -> Recipe | None:
    """Get recipe by Grocy ID from local DB, optionally scoped to a household"""
    statement = select(Recipe).where(Recipe.grocy_id == grocy_id)
    if household_id is not None:
        statement = statement.where(Recipe.household_id == household_id)
    return db.exec(statement).first()


def get_latest_recipe_data(db: Session, recipe_id: int) -> RecipeData | None:
    """Get the latest RecipeData record for a given recipe"""
    statement = (
        select(RecipeData)
        .where(RecipeData.recipe_id == recipe_id)
        .order_by(desc(RecipeData.consumed_at))
        .limit(1)
    )
    return db.exec(statement).first()


def get_recipes_with_pagination(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    household_id: int | None = None,
    sort_by: str = "created_at",
) -> RecipesListResponse:
    """
    Get all recipes with their latest consumption data with pagination

    Args:
        db: Database session
        skip: Number of recipes to skip (for pagination)
        limit: Maximum number of recipes to return
        search: Optional search query to filter by grocy_id or name

    Returns:
        RecipesListResponse with recipes list and pagination info
    """
    # Base query
    base_query = select(Recipe)
    if household_id is not None:
        base_query = base_query.where(Recipe.household_id == household_id)

    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        # Try to parse as integer for grocy_id search
        try:
            grocy_id = int(search)
            base_query = base_query.where(
                or_(Recipe.grocy_id == grocy_id, col(Recipe.name).ilike(search_term))
            )
        except ValueError:
            # If not a number, search only by name
            base_query = base_query.where(col(Recipe.name).ilike(search_term))

    # Get total count with filters
    total_statement = select(func.count()).select_from(base_query.subquery())
    total = db.exec(total_statement).one()

    # Get recipes with pagination
    if sort_by == "latest_consumed":
        # Left join with max consumed_at per recipe, sort by it (nulls last)
        latest_sub = (
            select(
                RecipeData.recipe_id,
                func.max(RecipeData.consumed_at).label("max_consumed_at"),
            )
            .group_by(RecipeData.recipe_id)
            .subquery()
        )
        recipes_statement = (
            base_query.outerjoin(latest_sub, Recipe.id == latest_sub.c.recipe_id)
            .order_by(nullslast(desc(latest_sub.c.max_consumed_at)))
            .offset(skip)
            .limit(limit)
        )
    else:
        recipes_statement = base_query.order_by(desc(Recipe.created_at)).offset(skip).limit(limit)
    recipes = db.exec(recipes_statement).all()

    # Build response with latest recipe data
    recipes_with_data = []
    for recipe in recipes:
        latest_data = get_latest_recipe_data(db, recipe.id)

        recipe_with_data = RecipeWithData(
            id=recipe.id,
            grocy_id=recipe.grocy_id,
            name=recipe.name,
            created_at=recipe.created_at.isoformat() if recipe.created_at else None,
            latest_servings=latest_data.servings if latest_data else None,
            latest_price_per_serving=latest_data.price_per_serving if latest_data else None,
            latest_weight_per_serving=latest_data.weight_per_serving if latest_data else None,
            latest_calories=latest_data.calories if latest_data else None,
            latest_proteins=latest_data.proteins if latest_data else None,
            latest_carbohydrates=latest_data.carbohydrates if latest_data else None,
            latest_fats=latest_data.fats if latest_data else None,
            latest_consumed_at=latest_data.consumed_at.isoformat()
            if latest_data and latest_data.consumed_at
            else None,
        )
        recipes_with_data.append(recipe_with_data)

    return RecipesListResponse(
        recipes=recipes_with_data,
        total=total,
        skip=skip,
        limit=limit,
    )


def sync_recipe_from_grocy(
    db: Session,
    grocy_api: GrocyAPI,
    grocy_recipe_id: int,
    household_id: int | None = None,
) -> RecipeSyncResponse:
    """
    Sync a single recipe from Grocy to local database

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        grocy_recipe_id: Grocy recipe ID to sync

    Returns:
        RecipeSyncResponse

    Raises:
        RecipeCalculationError: If sync fails
    """
    try:
        # Fetch recipe from Grocy
        recipe_data = grocy_api.get("/objects/recipes", {"query[]": [f"id={grocy_recipe_id}"]})

        if not recipe_data or len(recipe_data) == 0:
            raise RecipeCalculationError(f"Recipe {grocy_recipe_id} not found in Grocy")

        recipe_info = recipe_data[0]

        # Check if recipe already exists in local DB
        existing_recipe = get_recipe_by_grocy_id(db, grocy_recipe_id, household_id=household_id)

        if existing_recipe:
            # Update existing recipe
            existing_recipe.name = recipe_info.get("name", f"Recipe {grocy_recipe_id}")
            db.add(existing_recipe)
            db.commit()
            db.refresh(existing_recipe)

            return RecipeSyncResponse(
                status="success",
                recipe_id=existing_recipe.id,
                recipe_name=existing_recipe.name,
                message=f"Recipe '{existing_recipe.name}' updated",
            )
        else:
            # Create new recipe
            new_recipe = Recipe(
                grocy_id=grocy_recipe_id,
                name=recipe_info.get("name", f"Recipe {grocy_recipe_id}"),
                household_id=household_id,
            )
            db.add(new_recipe)
            db.commit()
            db.refresh(new_recipe)

            return RecipeSyncResponse(
                status="success",
                recipe_id=new_recipe.id,
                recipe_name=new_recipe.name,
                message=f"Recipe '{new_recipe.name}' synced successfully",
            )

    except GrocyError as e:
        raise RecipeCalculationError(f"Failed to fetch recipe from Grocy: {e!s}") from e
    except Exception as e:
        db.rollback()
        raise RecipeCalculationError(f"Sync error: {e!s}") from e


def sync_all_recipes_from_grocy(
    db: Session, grocy_api: GrocyAPI, household_id: int | None = None
) -> RecipesSyncAllResponse:
    """
    Sync all recipes from Grocy to local database

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance

    Returns:
        RecipesSyncAllResponse with statistics
    """
    stats = {
        "processed": 0,
        "synced": 0,
        "errors": 0,
    }

    try:
        # Fetch all recipes from Grocy
        recipes_data = grocy_api.get("/objects/recipes", {"query[]": ["id>0"]})

        if not isinstance(recipes_data, list):
            raise RecipeCalculationError("Unexpected response format from Grocy API")

        for recipe_raw in recipes_data:
            try:
                grocy_recipe_id = recipe_raw.get("id")
                recipe_name = recipe_raw.get("name", f"Recipe {grocy_recipe_id}")

                # Check if recipe already exists
                existing_recipe = get_recipe_by_grocy_id(
                    db, grocy_recipe_id, household_id=household_id
                )

                if existing_recipe:
                    # Update existing recipe
                    existing_recipe.name = recipe_name
                    db.add(existing_recipe)
                else:
                    # Create new recipe
                    new_recipe = Recipe(
                        grocy_id=grocy_recipe_id, name=recipe_name, household_id=household_id
                    )
                    db.add(new_recipe)

                stats["synced"] += 1
                stats["processed"] += 1

            except Exception as e:
                print(f"Error processing recipe {recipe_raw.get('id', 'unknown')}: {e!s}")
                stats["errors"] += 1
                stats["processed"] += 1
                continue

        # Commit all changes
        db.commit()

        return RecipesSyncAllResponse(
            status="success",
            processed=stats["processed"],
            synced=stats["synced"],
            errors=stats["errors"],
            message=f"Synced {stats['synced']} recipes ({stats['errors']} errors)",
        )

    except GrocyError as e:
        db.rollback()
        raise RecipeCalculationError(f"Failed to fetch recipes from Grocy: {e!s}") from e
    except Exception as e:
        db.rollback()
        raise RecipeCalculationError(f"Sync error: {e!s}") from e


def save_recipe_consumption_data(
    db: Session,
    grocy_recipe_id: int,
    servings: int,
    price_per_serving: float | None,
    per_serving_nutrients: RecipeNutrients,
    weight_per_serving: float | None = None,
    user_id: int | None = None,
    household_id: int | None = None,
    consumed_products_data: list[dict] | None = None,
) -> RecipeDataSaveResponse:
    """
    Save recipe consumption data to local database

    Args:
        db: Database session
        grocy_recipe_id: Grocy recipe ID
        servings: Number of servings
        price_per_serving: Price per serving
        per_serving_nutrients: Nutrients per serving

    Returns:
        RecipeDataSaveResponse

    Raises:
        RecipeCalculationError: If save fails
    """
    try:
        # Get or create recipe in local DB
        recipe = get_recipe_by_grocy_id(db, grocy_recipe_id, household_id=household_id)

        if not recipe:
            raise RecipeCalculationError(
                f"Recipe {grocy_recipe_id} not found in local database. "
                "Please sync the recipe first."
            )

        # Calculate weight_per_serving from consumed products if not provided
        if weight_per_serving is None and consumed_products_data:
            total_weight = sum(item["quantity"] for item in consumed_products_data)
            if total_weight > 0:
                weight_per_serving = round(total_weight / servings, 2)

        # Create new recipe data record
        recipe_data = RecipeData(
            recipe_id=recipe.id,
            servings=servings,
            price_per_serving=price_per_serving,
            weight_per_serving=weight_per_serving,
            user_id=user_id,
            calories=per_serving_nutrients.calories,
            carbohydrates=per_serving_nutrients.carbohydrates,
            carbohydrates_of_sugars=per_serving_nutrients.carbohydrates_of_sugars,
            proteins=per_serving_nutrients.proteins,
            fats=per_serving_nutrients.fats,
            fats_saturated=per_serving_nutrients.fats_saturated,
            salt=per_serving_nutrients.salt,
            fibers=per_serving_nutrients.fibers,
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

        db.commit()
        db.refresh(recipe_data)

        return RecipeDataSaveResponse(
            status="success",
            recipe_data_id=recipe_data.id,
            message=f"Recipe consumption data saved for '{recipe.name}'",
        )

    except Exception as e:
        db.rollback()
        raise RecipeCalculationError(f"Failed to save recipe data: {e!s}") from e


def get_recipe_detail(
    db: Session, recipe_id: int, household_id: int | None = None, user_id: int | None = None
) -> RecipeDetailResponse:
    """
    Get recipe details with consumption history

    Args:
        db: Database session
        recipe_id: Recipe ID (local DB ID, not Grocy ID)

    Returns:
        RecipeDetailResponse with recipe data and history

    Raises:
        RecipeCalculationError: If recipe not found
    """
    # Get recipe
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise RecipeCalculationError(f"Recipe with ID {recipe_id} not found")
    if household_id is not None and recipe.household_id != household_id:
        raise RecipeCalculationError(f"Recipe with ID {recipe_id} not found")

    # Get consumption history for this user, ordered by date descending
    statement = select(RecipeData).where(RecipeData.recipe_id == recipe_id)
    if user_id is not None:
        statement = statement.where(RecipeData.user_id == user_id)
    statement = statement.order_by(desc(RecipeData.consumed_at))
    recipe_data_list = db.exec(statement).all()

    # Find which recipe_data IDs have consumed products
    recipe_data_ids = [data.id for data in recipe_data_list]
    ids_with_products: set[int] = set()
    if recipe_data_ids:
        has_products_stmt = (
            select(RecipeConsumedProduct.recipe_data_id)
            .where(col(RecipeConsumedProduct.recipe_data_id).in_(recipe_data_ids))
            .distinct()
        )
        ids_with_products = set(db.exec(has_products_stmt).all())

    # Convert to history items
    history = [
        RecipeHistoryItem(
            id=data.id,
            servings=data.servings,
            price_per_serving=data.price_per_serving,
            weight_per_serving=data.weight_per_serving,
            calories=data.calories,
            proteins=data.proteins,
            carbohydrates=data.carbohydrates,
            carbohydrates_of_sugars=data.carbohydrates_of_sugars,
            fats=data.fats,
            fats_saturated=data.fats_saturated,
            salt=data.salt,
            fibers=data.fibers,
            consumed_at=data.consumed_at.isoformat() if data.consumed_at else "",
            consumed_date=str(data.consumed_date) if data.consumed_date else None,
            has_products=data.id in ids_with_products,
        )
        for data in recipe_data_list
    ]

    return RecipeDetailResponse(
        id=recipe.id,
        grocy_id=recipe.grocy_id,
        name=recipe.name,
        created_at=recipe.created_at.isoformat() if recipe.created_at else "",
        history=history,
        total_history=len(history),
    )


def get_recipe_consumed_products(
    db: Session,
    recipe_data_id: int,
    household_id: int | None = None,
) -> RecipeConsumedProductsResponse:
    """Get products consumed in a specific recipe consumption."""
    from app.models.product import Product, ProductData

    # Verify recipe_data exists and belongs to household
    recipe_data = db.get(RecipeData, recipe_data_id)
    if not recipe_data:
        raise RecipeCalculationError(f"RecipeData with ID {recipe_data_id} not found")
    if household_id is not None:
        recipe = db.get(Recipe, recipe_data.recipe_id)
        if not recipe or recipe.household_id != household_id:
            raise RecipeCalculationError(f"RecipeData with ID {recipe_data_id} not found")

    # Get consumed products with product info
    stmt = (
        select(RecipeConsumedProduct, ProductData, Product)
        .join(ProductData, RecipeConsumedProduct.product_data_id == ProductData.id)
        .join(Product, ProductData.product_id == Product.id)
        .where(RecipeConsumedProduct.recipe_data_id == recipe_data_id)
        .order_by(RecipeConsumedProduct.id)
    )

    products = []
    total_cost = None
    for rcp, pd, product in db.exec(stmt).all():
        qty = rcp.quantity
        tc = round((pd.calories or 0) * qty, 2)
        tcarb = round((pd.carbohydrates or 0) * qty, 2)
        tsugar = round((pd.carbohydrates_of_sugars or 0) * qty, 2)
        tprot = round((pd.proteins or 0) * qty, 2)
        tfat = round((pd.fats or 0) * qty, 2)
        tsfat = round((pd.fats_saturated or 0) * qty, 2)
        tsalt = round((pd.salt or 0) * qty, 2)
        tfiber = round((pd.fibers or 0) * qty, 2)

        if rcp.cost is not None:
            if total_cost is None:
                total_cost = 0.0
            total_cost += rcp.cost

        products.append(
            RecipeConsumedProductItem(
                id=rcp.id,
                product_name=product.name,
                quantity=round(qty, 2),
                cost=rcp.cost,
                calories=pd.calories,
                carbohydrates=pd.carbohydrates,
                carbohydrates_of_sugars=pd.carbohydrates_of_sugars,
                proteins=pd.proteins,
                fats=pd.fats,
                fats_saturated=pd.fats_saturated,
                salt=pd.salt,
                fibers=pd.fibers,
                total_calories=tc,
                total_carbohydrates=tcarb,
                total_carbohydrates_of_sugars=tsugar,
                total_proteins=tprot,
                total_fats=tfat,
                total_fats_saturated=tsfat,
                total_salt=tsalt,
                total_fibers=tfiber,
            )
        )

    return RecipeConsumedProductsResponse(
        recipe_data_id=recipe_data_id,
        products=products,
        total_cost=round(total_cost, 2) if total_cost is not None else None,
    )
