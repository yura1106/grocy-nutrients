"""
Consumption endpoints - step-by-step meal plan consumption
"""

from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, col, desc, select

from app.core.auth import get_current_user, get_grocy_api
from app.db.base import get_db
from app.models.product import (
    ConsumedProduct,
    MealPlanConsumption,
    NoteNutrients,
    Product,
    ProductData,
)
from app.models.recipe import Recipe
from app.schemas.consumption import (
    ConsumedDayDetailResponse,
    ConsumedProductDetailItem,
    ConsumedProductsStatsResponse,
    ConsumptionCheckRequest,
    ConsumptionCheckResponse,
    ConsumptionJobStatusResponse,
    DailyNutrientStats,
    DryRunRequest,
    DryRunResponse,
    ExecuteConsumptionJobResponse,
    ExecuteConsumptionRequest,
    ExecuteConsumptionResponse,
    MealPlanConsumptionHistoryItem,
    MealPlanConsumptionHistoryResponse,
    MealPlanConsumptionImportRequest,
    MealPlanConsumptionImportResponse,
    NoteDetailItem,
    ShoppingListRequest,
    ShoppingListResponse,
)
from app.services.consumption import (
    ConsumptionError,
    check_products_availability,
    create_shopping_list,
    dry_run_consumption,
)
from app.services.grocy_api import GrocyAPI
from app.tasks import celery as celery_app
from app.tasks.execute_consumption import execute_consumption_task

router = APIRouter()


@router.post("/check", response_model=ConsumptionCheckResponse)
def check_availability(
    request: ConsumptionCheckRequest,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
) -> Any:
    """
    Step 1: Check if all products from meal plan are available in stock

    Returns:
        - status: "success" if all products available, "insufficient_stock" otherwise
        - products_to_consume: Dict of products planned for consumption
        - products_to_buy: Dict of products that need to be purchased
    """
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
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    """
    Step 2 (optional): Create shopping list in Grocy for missing products

    Called when user confirms they want to create a shopping list
    """
    try:
        result = create_shopping_list(grocy_api, request.date, request.products_to_buy)
        return ShoppingListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dry-run", response_model=DryRunResponse)
def dry_run(
    request: DryRunRequest,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
) -> Any:
    """
    Step 3: Preview what products will be consumed (dry run)

    Shows detailed information about products that will be consumed,
    including nutritional data and totals
    """
    try:
        result = dry_run_consumption(db, grocy_api, request.date)
        return DryRunResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConsumptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteConsumptionJobResponse)
def execute(
    request: ExecuteConsumptionRequest,
    current_user=Depends(get_current_user),
    x_household_id: int = Header(..., alias="X-Household-Id"),
) -> Any:
    """
    Step 4: Enqueue consumption job — returns task_id immediately.
    Poll GET /consumption/job/{task_id} for progress and result.
    """
    task = execute_consumption_task.delay(current_user.id, x_household_id, request.date)
    return ExecuteConsumptionJobResponse(task_id=task.id, status="queued")


@router.get(
    "/job/{task_id}",
    response_model=ConsumptionJobStatusResponse,
    dependencies=[Depends(get_current_user)],
)
def get_job_status(task_id: str) -> Any:
    """
    Poll the status of a consumption background job.
    States: PENDING → PROGRESS → SUCCESS | FAILURE
    """
    result: AsyncResult = AsyncResult(task_id, app=celery_app)
    state = result.state

    if state == "PENDING":
        return ConsumptionJobStatusResponse(
            task_id=task_id, state="PENDING", step="Waiting in queue..."
        )

    if state == "PROGRESS":
        meta = result.info or {}
        return ConsumptionJobStatusResponse(
            task_id=task_id, state="PROGRESS", step=meta.get("step", "Processing...")
        )

    if state == "SUCCESS":
        payload = result.result or {}
        if payload.get("status") == "error":
            return ConsumptionJobStatusResponse(
                task_id=task_id, state="FAILURE", error=payload.get("error")
            )
        execution_result = ExecuteConsumptionResponse(**payload["result"])
        return ConsumptionJobStatusResponse(
            task_id=task_id, state="SUCCESS", result=execution_result
        )

    # FAILURE (exception raised)
    error_msg = str(result.info) if result.info else "Unknown error"
    return ConsumptionJobStatusResponse(task_id=task_id, state="FAILURE", error=error_msg)


@router.post(
    "/import-history",
    response_model=MealPlanConsumptionImportResponse,
    dependencies=[Depends(get_current_user)],
)
def import_consumption_history(
    request: MealPlanConsumptionImportRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    Import consumed_recipes.csv rows into meal_plan_consumptions table.
    Skips rows that already exist (same meal_plan_id).
    """
    from datetime import date as date_type_cls

    existing_meal_plan_ids = set(
        row for row in db.exec(select(MealPlanConsumption.meal_plan_id)).all()
    )

    imported = 0
    skipped = 0
    for row in request.rows:
        if row.meal_plan_id in existing_meal_plan_ids:
            skipped += 1
            continue
        try:
            day = date_type_cls.fromisoformat(row.day)
        except ValueError:
            skipped += 1
            continue
        db.add(
            MealPlanConsumption(
                date=day,
                meal_plan_id=row.meal_plan_id,
                recipe_grocy_id=row.recipe_id,
            )
        )
        existing_meal_plan_ids.add(row.meal_plan_id)
        imported += 1

    db.commit()
    return MealPlanConsumptionImportResponse(
        imported=imported,
        skipped=skipped,
        message=f"Imported {imported} records, skipped {skipped} duplicates.",
    )


@router.get(
    "/history",
    response_model=MealPlanConsumptionHistoryResponse,
    dependencies=[Depends(get_current_user)],
)
def get_consumption_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
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
            recipe = db.exec(select(Recipe).where(Recipe.grocy_id == r.recipe_grocy_id)).first()
            recipe_name_cache[r.recipe_grocy_id] = (
                recipe.name if recipe else f"Recipe #{r.recipe_grocy_id}"
            )

        items.append(
            MealPlanConsumptionHistoryItem(
                id=r.id,
                date=str(r.date),
                meal_plan_id=r.meal_plan_id,
                recipe_grocy_id=r.recipe_grocy_id,
                recipe_name=recipe_name_cache[r.recipe_grocy_id],
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )

    return MealPlanConsumptionHistoryResponse(items=items, total=total)


@router.get(
    "/stats",
    response_model=ConsumedProductsStatsResponse,
    dependencies=[Depends(get_current_user)],
)
def get_consumed_products_stats(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=60, ge=1, le=365),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get consumed products statistics grouped by day with nutrient totals.
    Includes nutrients from meal plan notes (NoteNutrients table).
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy import union

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

        days.append(
            DailyNutrientStats(
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
            )
        )

    return ConsumedProductsStatsResponse(days=days, total=total)


@router.get(
    "/stats/{date}",
    response_model=ConsumedDayDetailResponse,
    dependencies=[Depends(get_current_user)],
)
def get_consumed_day_detail(
    date: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get detailed consumption breakdown for a single day:
    all consumed products with per-product nutrient totals + note entries.
    """
    from datetime import date as date_type_cls

    try:
        day = date_type_cls.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

    # Consumed products joined with product data and product name
    stmt = (
        select(ConsumedProduct, ProductData, Product)
        .join(ProductData, ConsumedProduct.product_data_id == ProductData.id)
        .join(Product, ProductData.product_id == Product.id)
        .where(ConsumedProduct.date == day)
        .order_by(ConsumedProduct.id)
    )

    products = []
    total_calories = 0.0
    total_carbohydrates = 0.0
    total_carbohydrates_of_sugars = 0.0
    total_proteins = 0.0
    total_fats = 0.0
    total_fats_saturated = 0.0
    total_salt = 0.0
    total_fibers = 0.0

    for consumed, pd, product in db.exec(stmt).all():
        qty = consumed.quantity
        tc = round((pd.calories or 0) * qty, 2)
        tcarb = round((pd.carbohydrates or 0) * qty, 2)
        tsugar = round((pd.carbohydrates_of_sugars or 0) * qty, 2)
        tprot = round((pd.proteins or 0) * qty, 2)
        tfat = round((pd.fats or 0) * qty, 2)
        tsfat = round((pd.fats_saturated or 0) * qty, 2)
        tsalt = round((pd.salt or 0) * qty, 2)
        tfiber = round((pd.fibers or 0) * qty, 2)

        total_calories += tc
        total_carbohydrates += tcarb
        total_carbohydrates_of_sugars += tsugar
        total_proteins += tprot
        total_fats += tfat
        total_fats_saturated += tsfat
        total_salt += tsalt
        total_fibers += tfiber

        products.append(
            ConsumedProductDetailItem(
                id=consumed.id,
                product_name=product.name,
                quantity=round(qty, 2),
                recipe_grocy_id=consumed.recipe_grocy_id,
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

    # Note nutrients
    note_stmt = select(NoteNutrients).where(NoteNutrients.date == day).order_by(NoteNutrients.id)
    notes = []
    for note in db.exec(note_stmt).all():
        total_calories += note.calories or 0
        total_carbohydrates += note.carbohydrates or 0
        total_carbohydrates_of_sugars += note.carbohydrates_of_sugars or 0
        total_proteins += note.proteins or 0
        total_fats += note.fats or 0
        total_fats_saturated += note.fats_saturated or 0
        total_salt += note.salt or 0
        total_fibers += note.fibers or 0
        notes.append(
            NoteDetailItem(
                id=note.id,
                note=note.note,
                calories=note.calories,
                proteins=note.proteins,
                carbohydrates=note.carbohydrates,
                carbohydrates_of_sugars=note.carbohydrates_of_sugars,
                fats=note.fats,
                fats_saturated=note.fats_saturated,
                salt=note.salt,
                fibers=note.fibers,
            )
        )

    return ConsumedDayDetailResponse(
        date=date,
        products=products,
        notes=notes,
        total_calories=round(total_calories, 2),
        total_carbohydrates=round(total_carbohydrates, 2),
        total_carbohydrates_of_sugars=round(total_carbohydrates_of_sugars, 2),
        total_proteins=round(total_proteins, 2),
        total_fats=round(total_fats, 2),
        total_fats_saturated=round(total_fats_saturated, 2),
        total_salt=round(total_salt, 2),
        total_fibers=round(total_fibers, 2),
    )
