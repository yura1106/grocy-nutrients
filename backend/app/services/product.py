from datetime import datetime

from sqlalchemy import desc
from sqlmodel import Session, col, func, or_, select

from app.models.product import Product, ProductData
from app.schemas.product import (
    ConsumeResponse,
    GrocyProductResponse,
    ProductDetailResponse,
    ProductHistoryItem,
    ProductNutrients,
    ProductsListResponse,
    ProductWithData,
    SyncResponse,
)
from app.services.grocy_api import GrocyAPI, GrocyError


class ProductSyncError(Exception):
    """Exception raised during product synchronization"""

    pass


def get_product_by_grocy_id(
    db: Session,
    grocy_id: int,
    household_id: int | None = None,
) -> Product | None:
    """Get product by Grocy ID, optionally scoped to a household"""
    statement = select(Product).where(Product.grocy_id == grocy_id)
    if household_id is not None:
        statement = statement.where(Product.household_id == household_id)
    return db.exec(statement).first()


def get_latest_product_data(db: Session, product_id: int) -> ProductData | None:
    """Get the latest ProductData record for a given product"""
    statement = (
        select(ProductData)
        .where(ProductData.product_id == product_id)
        .order_by(desc(ProductData.created_at))  # type: ignore[arg-type]
        .limit(1)
    )
    return db.exec(statement).first()


def get_products_with_pagination(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    household_id: int | None = None,
) -> ProductsListResponse:
    """
    Get all products with their latest nutritional data with pagination

    Args:
        db: Database session
        skip: Number of products to skip (for pagination)
        limit: Maximum number of products to return
        search: Optional search query to filter by name or Grocy ID

    Returns:
        ProductsListResponse with products list and pagination info
    """
    # Base query
    base_query = select(Product)
    if household_id is not None:
        base_query = base_query.where(Product.household_id == household_id)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        try:
            grocy_id = int(search)
            base_query = base_query.where(
                or_(Product.grocy_id == grocy_id, col(Product.name).ilike(search_term))
            )
        except ValueError:
            base_query = base_query.where(col(Product.name).ilike(search_term))

    # Get total count with filters
    total_statement = select(func.count()).select_from(base_query.subquery())
    total = db.exec(total_statement).one()

    # Get products with pagination
    products_statement = base_query.order_by(desc(Product.created_at)).offset(skip).limit(limit)  # type: ignore[arg-type]
    products = db.exec(products_statement).all()

    # Build response with latest product data
    products_with_data = []
    for product in products:
        latest_data = get_latest_product_data(db, product.id)  # type: ignore[arg-type]

        product_with_data = ProductWithData(
            id=product.id,  # type: ignore[arg-type]
            grocy_id=product.grocy_id,
            name=product.name,
            active=product.active,
            product_group_id=product.product_group_id,
            created_at=product.created_at.isoformat() if product.created_at else None,  # type: ignore[arg-type]
            calories=latest_data.calories if latest_data else None,
            carbohydrates=latest_data.carbohydrates if latest_data else None,
            carbohydrates_of_sugars=latest_data.carbohydrates_of_sugars if latest_data else None,
            proteins=latest_data.proteins if latest_data else None,
            fats=latest_data.fats if latest_data else None,
            fats_saturated=latest_data.fats_saturated if latest_data else None,
            salt=latest_data.salt if latest_data else None,
            fibers=latest_data.fibers if latest_data else None,
            data_created_at=latest_data.created_at.isoformat()
            if latest_data and latest_data.created_at
            else None,
        )
        products_with_data.append(product_with_data)

    return ProductsListResponse(
        products=products_with_data,
        total=total,
        skip=skip,
        limit=limit,
    )


def get_product_detail(
    db: Session, product_id: int, household_id: int | None = None
) -> ProductDetailResponse:
    """
    Get product details with full data history

    Args:
        db: Database session
        product_id: Local product ID

    Returns:
        ProductDetailResponse with product info and history

    Raises:
        ProductSyncError: If product not found
    """
    product = db.get(Product, product_id)
    if not product:
        raise ProductSyncError(f"Product with ID {product_id} not found")
    if household_id is not None and product.household_id != household_id:
        raise ProductSyncError(f"Product with ID {product_id} not found")

    statement = (
        select(ProductData)
        .where(ProductData.product_id == product_id)
        .order_by(desc(ProductData.created_at))  # type: ignore[arg-type]
    )
    data_list = db.exec(statement).all()

    history = [
        ProductHistoryItem(
            id=data.id,  # type: ignore[arg-type]
            calories=data.calories,
            carbohydrates=data.carbohydrates,
            carbohydrates_of_sugars=data.carbohydrates_of_sugars,
            proteins=data.proteins,
            fats=data.fats,
            fats_saturated=data.fats_saturated,
            salt=data.salt,
            fibers=data.fibers,
            created_at=data.created_at.isoformat() if data.created_at else "",
        )
        for data in data_list
    ]

    return ProductDetailResponse(
        id=product.id,  # type: ignore[arg-type]
        grocy_id=product.grocy_id,
        name=product.name,
        active=product.active,
        product_group_id=product.product_group_id,
        qu_id_stock=product.qu_id_stock,
        created_at=product.created_at.isoformat() if product.created_at else "",
        history=history,
        total_history=len(history),
    )


def upsert_product(
    db: Session,
    grocy_product: GrocyProductResponse,
    household_id: int | None = None,
) -> Product:
    """
    Insert or update a product in the database
    Returns the product (either existing or newly created)
    """
    # Try to find existing product by grocy_id + household_id
    statement = select(Product).where(Product.grocy_id == grocy_product.id)
    if household_id is not None:
        statement = statement.where(Product.household_id == household_id)
    existing_product = db.exec(statement).first()

    if existing_product:
        # Update existing product
        existing_product.name = grocy_product.name
        existing_product.active = grocy_product.is_active()
        existing_product.product_group_id = grocy_product.product_group_id
        existing_product.qu_id_stock = grocy_product.qu_id_stock
        db.add(existing_product)
        return existing_product
    else:
        # Create new product
        new_product = Product(
            grocy_id=grocy_product.id,
            name=grocy_product.name,
            active=grocy_product.is_active(),
            product_group_id=grocy_product.product_group_id,
            qu_id_stock=grocy_product.qu_id_stock,
            household_id=household_id,
        )
        db.add(new_product)
        db.flush()  # To get the ID
        return new_product


def create_product_data_if_changed(
    db: Session,
    product_id: int,
    nutrients: ProductNutrients,
) -> bool:
    """
    Create a new ProductData record if nutrients have changed
    Returns True if a new record was created, False otherwise
    """
    # Get latest product data
    latest_data = get_latest_product_data(db, product_id)

    # If no history exists, create first record
    if not latest_data:
        new_data = ProductData(
            product_id=product_id,
            calories=nutrients.calories,
            carbohydrates=nutrients.carbohydrates,
            carbohydrates_of_sugars=nutrients.carbohydrates_of_sugars,
            proteins=nutrients.proteins,
            fats=nutrients.fats,
            fats_saturated=nutrients.fats_saturated,
            salt=nutrients.salt,
            fibers=nutrients.fibers,
        )
        db.add(new_data)
        return True

    # Compare with latest data
    latest_nutrients = ProductNutrients(
        calories=latest_data.calories,
        carbohydrates=latest_data.carbohydrates,
        carbohydrates_of_sugars=latest_data.carbohydrates_of_sugars,
        proteins=latest_data.proteins,
        fats=latest_data.fats,
        fats_saturated=latest_data.fats_saturated,
        salt=latest_data.salt,
        fibers=latest_data.fibers,
    )

    # If data has changed, create new record
    if nutrients.has_changes(latest_nutrients):
        new_data = ProductData(
            product_id=product_id,
            calories=nutrients.calories,
            carbohydrates=nutrients.carbohydrates,
            carbohydrates_of_sugars=nutrients.carbohydrates_of_sugars,
            proteins=nutrients.proteins,
            fats=nutrients.fats,
            fats_saturated=nutrients.fats_saturated,
            salt=nutrients.salt,
            fibers=nutrients.fibers,
        )
        db.add(new_data)
        return True

    return False


def sync_grocy_products(
    db: Session,
    grocy_api: GrocyAPI,
    offset: int = 0,
    limit: int = 50,
    household_id: int | None = None,
) -> SyncResponse:
    """
    Synchronize products from Grocy API to local database in chunks.

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        offset: Number of products to skip
        limit: Maximum number of products to process in this chunk

    Returns:
        SyncResponse with statistics and pagination info

    Raises:
        ProductSyncError: If synchronization fails
    """
    try:
        # Fetch all products from Grocy
        products_data = grocy_api.get("/objects/products")
    except GrocyError as e:
        raise ProductSyncError(f"Failed to fetch products from Grocy: {e!s}") from e

    if not isinstance(products_data, list):
        raise ProductSyncError("Unexpected response format from Grocy API")

    total = len(products_data)
    chunk = products_data[offset : offset + limit]

    stats = {
        "processed": 0,
        "updated": 0,
        "new_history_records": 0,
    }

    # Process chunk
    for product_raw in chunk:
        try:
            grocy_product = GrocyProductResponse(**product_raw)
            product = upsert_product(db, grocy_product, household_id=household_id)
            stats["updated"] += 1

            userfields = grocy_product.get_userfields()
            nutrients = ProductNutrients.from_grocy_product(grocy_product, userfields, grocy_api)

            if create_product_data_if_changed(db, product.id, nutrients):  # type: ignore[arg-type]
                stats["new_history_records"] += 1

            stats["processed"] += 1

        except Exception as e:
            print(f"Error processing product {product_raw.get('id', 'unknown')}: {e!s}")
            continue

    # Commit this chunk
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ProductSyncError(f"Failed to commit changes to database: {e!s}") from e

    return SyncResponse(
        status="success",
        processed=stats["processed"],
        updated=stats["updated"],
        new_history_records=stats["new_history_records"],
        total=total,
        has_more=(offset + limit) < total,
    )


def sync_single_grocy_product(
    db: Session,
    grocy_api: GrocyAPI,
    grocy_product_id: int,
    household_id: int | None = None,
) -> SyncResponse:
    """
    Synchronize a single product from Grocy API to local database

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        grocy_product_id: Grocy product ID to sync

    Returns:
        SyncResponse with statistics

    Raises:
        ProductSyncError: If synchronization fails
    """
    try:
        # Fetch single product from Grocy
        product_data = grocy_api.get(f"/objects/products/{grocy_product_id}")
    except GrocyError as e:
        raise ProductSyncError(
            f"Failed to fetch product {grocy_product_id} from Grocy: {e!s}"
        ) from e

    stats = {
        "processed": 0,
        "updated": 0,
        "new_history_records": 0,
    }

    try:
        # Parse product data
        grocy_product = GrocyProductResponse(**product_data)

        # Upsert product
        product = upsert_product(db, grocy_product, household_id=household_id)
        stats["updated"] += 1

        # Ensure product has an ID
        if not product.id:
            raise ProductSyncError("Product was created but has no ID")

        # Parse nutrients
        userfields = grocy_product.get_userfields()
        nutrients = ProductNutrients.from_grocy_product(grocy_product, userfields, grocy_api)

        # Create product data history if changed
        if create_product_data_if_changed(db, product.id, nutrients):
            stats["new_history_records"] += 1

        stats["processed"] += 1

    except Exception as e:
        raise ProductSyncError(f"Error processing product {grocy_product_id}: {e!s}") from e

    # Commit changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ProductSyncError(f"Failed to commit changes to database: {e!s}") from e

    return SyncResponse(
        status="success",
        processed=stats["processed"],
        updated=stats["updated"],
        new_history_records=stats["new_history_records"],
    )


def update_grocy_product_nutrients(
    db: Session,
    grocy_api: GrocyAPI,
    linked_product_id: int,
    recipe_total_nutrients: dict[str, float],
    desired_servings: int,
    household_id: int | None = None,
) -> None:
    """Update linked product nutrients in Grocy and sync back to local DB."""
    linked_product = grocy_api.get_product(linked_product_id)
    factor = grocy_api.get_conversion_factor_safe(
        linked_product["id"],
        linked_product["qu_id_stock"],
        grocy_api.gram_ml_units,
    )

    nutrient_fields = {
        "proteins": "nutrients_proteins",
        "carbohydrates": "nutrients_carbohydrates",
        "carbohydrates_of_sugars": "nutrients_carbohydrates_of_sugars",
        "fats": "nutrients_fats",
        "fats_saturated": "nutrients_fats_saturated",
        "salt": "nutrients_salt",
        "fibers": "nutrients_fibers",
    }

    for nutrient, value in recipe_total_nutrients.items():
        per_serving = value / desired_servings
        if nutrient == "calories":
            grocy_api.put(
                f"/objects/products/{linked_product['id']}",
                data={"calories": str(round(per_serving, 4))},
            )
        elif nutrient in nutrient_fields:
            grocy_api.put(
                f"/userfields/products/{linked_product['id']}",
                data={nutrient_fields[nutrient]: str(round(per_serving / factor, 4))},
            )

    sync_single_grocy_product(db, grocy_api, linked_product_id, household_id=household_id)


def sync_single_grocy_product_detailed(
    db: Session,
    grocy_api: GrocyAPI,
    grocy_product_id: int,
    household_id: int | None = None,
):
    """
    Synchronize a single product from Grocy API to local database with detailed response

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        grocy_product_id: Grocy product ID to sync

    Returns:
        SingleProductSyncResponse with detailed data from Grocy and local DB

    Raises:
        ProductSyncError: If synchronization fails
    """
    from app.schemas.product import ProductSyncData, SingleProductSyncResponse

    try:
        # Fetch single product from Grocy
        product_data = grocy_api.get(f"/objects/products/{grocy_product_id}")
    except GrocyError as e:
        raise ProductSyncError(
            f"Failed to fetch product {grocy_product_id} from Grocy: {e!s}"
        ) from e

    stats = {
        "processed": 0,
        "updated": 0,
        "new_history_records": 0,
    }

    try:
        # Parse product data
        grocy_product = GrocyProductResponse(**product_data)

        # Upsert product
        product = upsert_product(db, grocy_product, household_id=household_id)
        stats["updated"] += 1

        # Ensure product has an ID
        if not product.id:
            raise ProductSyncError("Product was created but has no ID")

        # Parse nutrients
        userfields = grocy_product.get_userfields()
        nutrients = ProductNutrients.from_grocy_product(grocy_product, userfields, grocy_api)

        # Create product data history if changed
        if create_product_data_if_changed(db, product.id, nutrients):
            stats["new_history_records"] += 1

        stats["processed"] += 1

    except Exception as e:
        raise ProductSyncError(f"Error processing product {grocy_product_id}: {e!s}") from e

    # Commit changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ProductSyncError(f"Failed to commit changes to database: {e!s}") from e

    # Get latest product data from DB after commit
    latest_product_data = get_latest_product_data(db, product.id)
    latest_data_dict = None
    if latest_product_data:
        latest_data_dict = {
            "calories": latest_product_data.calories,
            "carbohydrates": latest_product_data.carbohydrates,
            "carbohydrates_of_sugars": latest_product_data.carbohydrates_of_sugars,
            "proteins": latest_product_data.proteins,
            "fats": latest_product_data.fats,
            "fats_saturated": latest_product_data.fats_saturated,
            "salt": latest_product_data.salt,
            "fibers": latest_product_data.fibers,
            "created_at": latest_product_data.created_at.isoformat()
            if latest_product_data.created_at
            else None,
        }

    # Build local data response
    local_data = ProductSyncData(
        id=product.id,
        grocy_id=product.grocy_id,
        name=product.name,
        active=product.active,
        product_group_id=product.product_group_id,
        qu_id_stock=product.qu_id_stock,
        created_at=product.created_at.isoformat() if product.created_at else "",
        latest_data=latest_data_dict,
    )

    return SingleProductSyncResponse(
        status="success",
        processed=stats["processed"],
        updated=stats["updated"],
        new_history_records=stats["new_history_records"],
        grocy_data=product_data,  # Raw data from Grocy API
        local_data=local_data,  # Data from local DB
    )


def consume_daily_products(db: Session, grocy_api: GrocyAPI, date_str: str) -> ConsumeResponse:
    """
    Process daily product consumption plan

    This is a stub function - the actual Grocy API logic should be implemented here

    Args:
        db: Database session
        grocy_api: Initialized GrocyAPI instance
        date_str: Date string in YYYY-MM-DD format

    Returns:
        ConsumeResponse with custom data from Grocy processing
    """
    # Parse date
    try:
        datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    # TODO: Add your Grocy API logic here
    # Example:
    # 1. Fetch daily consumption plan from Grocy
    # 2. Process products
    # 3. Store consumed products in database

    products_to_consume = {}
    meal_plan = grocy_api.get_meal_plan(start_date=date_str)
    for meal in meal_plan:
        if meal["type"] == "note" or meal["done"]:
            continue

        if meal["type"] == "recipe":
            recipe_meal = grocy_api.get_meal_plan_recipe(meal["day"], meal["id"])
            resolved = grocy_api.get(
                "/objects/recipes_pos_resolved",
                {"query[]": ["recipe_id=" + str(recipe_meal["id"])]},
            )
            for pos in resolved:
                factor = 1
                if pos["product_id_effective"] not in products_to_consume:
                    products_to_consume[pos["product_id_effective"]] = {
                        "amount": 0,
                        "note": "",
                    }

                recipe = grocy_api.get("/objects/recipes/" + str(meal["recipe_id"]))
                product = grocy_api.get_product(pos["product_id_effective"])
                product_base = grocy_api.get_product(pos["product_id"])
                if product["qu_id_stock"] != product_base["qu_id_stock"]:
                    factor = grocy_api.get_unit_conversion_factor(
                        pos["product_id_effective"],
                        product_base["qu_id_stock"],
                        product["qu_id_stock"],
                    )
                products_to_consume[pos["product_id_effective"]]["amount"] += (
                    factor * pos["recipe_amount"]
                )
                products_to_consume[pos["product_id_effective"]]["note"] += recipe["name"] + " | "
            continue

        if meal["product_id"] not in products_to_consume:
            products_to_consume[meal["product_id"]] = {"amount": 0, "note": ""}
        product = get_product_by_grocy_id(db, meal["product_id"])
        if product:
            print(product.name)
        products_to_consume[meal["product_id"]]["amount"] += meal["product_amount"]

    products_to_buy = {}
    for product_id, planned_amount in products_to_consume.items():
        if product_id is None:
            continue
        data = grocy_api.get("/stock/products/" + str(product_id))
        if planned_amount["amount"] > data["stock_amount_aggregated"]:
            products_to_buy[product_id] = {
                "amount": round(planned_amount["amount"] - data["stock_amount_aggregated"], 2),
                "note": planned_amount["note"],
            }

    # print('------------------------------------')
    # for product_id, amount_to_buy in products_to_buy.items():
    #     print(get_product_by_grocy_id(db, product_id), "amount_to_buy", amount_to_buy, ": ")

    # if len(products_to_buy) > 0 and input("Create shopping list?") == "yes":
    #     grocy_api.create_shopping_list(date, week, products_to_buy)

    # Stub response - replace with actual data from Grocy processing
    stub_data = {
        "products_to_consume": products_to_consume,
        "products_to_buy": products_to_buy,
        "message": "This is a stub response. Implement your Grocy logic here.",
        "consumed_products": [],
        "total_calories": 0,
        "total_nutrients": {"proteins": 0, "fats": 0, "carbohydrates": 0},
    }

    # Example of saving consumed product (uncomment when implementing):
    # consumed_product = ConsumedProduct(
    #     product_data_id=some_product_data_id,
    #     date=consume_date,
    #     quantity=1.0  # Amount consumed
    # )
    # db.add(consumed_product)
    # db.commit()

    return ConsumeResponse(status="success", date=date_str, data=stub_data)
