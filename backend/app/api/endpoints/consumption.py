"""
Consumption endpoints - step-by-step meal plan consumption
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, desc, col

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.models.product import MealPlanConsumption
from app.models.recipe import Recipe
from app.models.product import ConsumedProduct, ProductData, NoteNutrients
from app.schemas.consumption import (
    ConsumptionCheckRequest,
    ConsumptionCheckResponse,
    ShoppingListRequest,
    ShoppingListResponse,
    DryRunRequest,
    DryRunResponse,
    ExecuteConsumptionRequest,
    ExecuteConsumptionResponse,
    MealPlanConsumptionHistoryResponse,
    MealPlanConsumptionHistoryItem,
    ConsumedProductsStatsResponse,
    DailyNutrientStats,
)
from app.services.consumption import (
    check_products_availability,
    create_shopping_list,
    dry_run_consumption,
    execute_consumption,
    ConsumptionError,
)
from app.services.grocy_api import GrocyAPI

router = APIRouter()


@router.post("/check", response_model=ConsumptionCheckResponse)
def check_availability(
    request: ConsumptionCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Step 1: Check if all products from meal plan are available in stock

    Returns:
        - status: "success" if all products available, "insufficient_stock" otherwise
        - products_to_consume: Dict of products planned for consumption
        - products_to_buy: Dict of products that need to be purchased
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        result = check_products_availability(db, grocy_api, request.date)
        return ConsumptionCheckResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConsumptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shopping-list", response_model=ShoppingListResponse)
def create_shopping_list_endpoint(
    request: ShoppingListRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Step 2 (optional): Create shopping list in Grocy for missing products

    Called when user confirms they want to create a shopping list
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        result = create_shopping_list(grocy_api, request.date, request.products_to_buy)
        return ShoppingListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dry-run", response_model=DryRunResponse)
def dry_run(
    request: DryRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Step 3: Preview what products will be consumed (dry run)

    Shows detailed information about products that will be consumed,
    including nutritional data and totals
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        result = dry_run_consumption(db, grocy_api, request.date)
        return DryRunResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConsumptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteConsumptionResponse)
def execute(
    request: ExecuteConsumptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Step 4: Execute consumption - actually consume products

    Consumes products in Grocy and saves consumption records to database
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        result = execute_consumption(db, grocy_api, request.date)
        return ExecuteConsumptionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConsumptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=MealPlanConsumptionHistoryResponse)
def get_consumption_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get meal plan consumption history
    """
    # Count total
    count_stmt = select(MealPlanConsumption)
    total = len(db.exec(count_stmt).all())

    # Fetch page
    stmt = (
        select(MealPlanConsumption)
        .order_by(desc(col(MealPlanConsumption.date)), desc(col(MealPlanConsumption.id)))
        .offset(skip)
        .limit(limit)
    )
    records = db.exec(stmt).all()

    # Resolve recipe names from local recipes table
    recipe_name_cache: dict[int, str] = {}
    items = []
    for r in records:
        if r.recipe_grocy_id not in recipe_name_cache:
            recipe = db.exec(
                select(Recipe).where(Recipe.grocy_id == r.recipe_grocy_id)
            ).first()
            recipe_name_cache[r.recipe_grocy_id] = recipe.name if recipe else f"Recipe #{r.recipe_grocy_id}"

        items.append(MealPlanConsumptionHistoryItem(
            id=r.id,
            date=str(r.date),
            meal_plan_id=r.meal_plan_id,
            recipe_grocy_id=r.recipe_grocy_id,
            recipe_name=recipe_name_cache[r.recipe_grocy_id],
            created_at=r.created_at.isoformat() if r.created_at else None,
        ))

    return MealPlanConsumptionHistoryResponse(items=items, total=total)


@router.get("/stats", response_model=ConsumedProductsStatsResponse)
def get_consumed_products_stats(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=60, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get consumed products statistics grouped by day with nutrient totals.
    Includes nutrients from meal plan notes (NoteNutrients table).
    """
    from sqlalchemy import func as sa_func, union

    # Collect distinct dates from both consumed_products and note_nutrients
    cp_dates = select(ConsumedProduct.date).distinct()
    nn_dates = select(NoteNutrients.date).distinct()
    all_dates_subq = union(cp_dates, nn_dates).subquery()
    all_dates_stmt = (
        select(all_dates_subq.c.date)
        .order_by(desc(all_dates_subq.c.date))
        .offset(skip)
        .limit(limit)
    )
    dates = [row for row in db.exec(all_dates_stmt).all()]

    total_stmt = select(sa_func.count()).select_from(
        select(all_dates_subq.c.date).distinct().subquery()
    )
    total = db.exec(total_stmt).one()

    days = []
    for d in dates:
        total_calories = 0.0
        total_carbohydrates = 0.0
        total_carbohydrates_of_sugars = 0.0
        total_proteins = 0.0
        total_fats = 0.0
        total_fats_saturated = 0.0
        total_salt = 0.0
        total_fibers = 0.0
        products_count = 0

        # Consumed products
        stmt = (
            select(ConsumedProduct, ProductData)
            .join(ProductData, ConsumedProduct.product_data_id == ProductData.id)
            .where(ConsumedProduct.date == d)
        )
        for consumed, product_data in db.exec(stmt).all():
            qty = consumed.quantity
            products_count += 1
            total_calories += (product_data.calories or 0) * qty
            total_carbohydrates += (product_data.carbohydrates or 0) * qty
            total_carbohydrates_of_sugars += (product_data.carbohydrates_of_sugars or 0) * qty
            total_proteins += (product_data.proteins or 0) * qty
            total_fats += (product_data.fats or 0) * qty
            total_fats_saturated += (product_data.fats_saturated or 0) * qty
            total_salt += (product_data.salt or 0) * qty
            total_fibers += (product_data.fibers or 0) * qty

        # Note nutrients for the same day
        note_stmt = select(NoteNutrients).where(NoteNutrients.date == d)
        for note in db.exec(note_stmt).all():
            total_calories += note.calories or 0
            total_carbohydrates += note.carbohydrates or 0
            total_carbohydrates_of_sugars += note.carbohydrates_of_sugars or 0
            total_proteins += note.proteins or 0
            total_fats += note.fats or 0
            total_fats_saturated += note.fats_saturated or 0
            total_salt += note.salt or 0
            total_fibers += note.fibers or 0

        days.append(DailyNutrientStats(
            date=str(d),
            total_calories=round(total_calories, 2),
            total_carbohydrates=round(total_carbohydrates, 2),
            total_carbohydrates_of_sugars=round(total_carbohydrates_of_sugars, 2),
            total_proteins=round(total_proteins, 2),
            total_fats=round(total_fats, 2),
            total_fats_saturated=round(total_fats_saturated, 2),
            total_salt=round(total_salt, 2),
            total_fibers=round(total_fibers, 2),
            products_count=products_count,
        ))

    return ConsumedProductsStatsResponse(days=days, total=total)
