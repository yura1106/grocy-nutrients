"""Meal plan endpoints — local creation + async Grocy sync."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser, get_current_user, get_grocy_api
from app.db.base import get_db
from app.models.product import Product
from app.schemas.meal_plan import (
    MealPlanBatchCreateRequest,
    MealPlanBatchCreateResponse,
    MealPlanDailyTotals,
    MealPlanJobStatusResponse,
    MealPlanLineEdit,
    MealPlanLineRead,
    MealPlanMissingItem,
    MealPlanRetryResponse,
    MealPlanSection,
    MealPlanSectionsResponse,
    MealPlanUnit,
    MealPlanUnitsResponse,
)
from app.services.grocy_api import GrocyAPI, GrocyError
from app.services.meal_plan import (
    compute_daily_totals,
    create_lines,
    delete_local_failed,
    delete_synced_line,
    enrich_lines,
    fetch_lines_in_range,
    get_or_load_sections,
    get_or_load_units_for_product,
    read_job_state,
    retry_line,
    submit_batch,
    update_line_amount,
)

router = APIRouter()


@router.post("/lines", response_model=MealPlanBatchCreateResponse)
def create_lines_endpoint(
    body: MealPlanBatchCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    """Insert N lines locally and enqueue the Grocy batch task."""
    rows = create_lines(
        session,
        household_id=household_id,
        user_id=current_user.id,
        lines=body.lines,
        grocy_api=grocy_api,
    )
    line_ids = [int(r.id) for r in rows if r.id is not None]
    task_id = submit_batch(
        session,
        household_id=household_id,
        user_id=current_user.id,
        line_ids=line_ids,
    )
    return MealPlanBatchCreateResponse(task_id=task_id, line_ids=line_ids)


@router.get("/lines", response_model=list[MealPlanLineRead])
def list_lines(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date",
        )
    rows = fetch_lines_in_range(
        session,
        household_id=household_id,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return enrich_lines(session, household_id=household_id, rows=rows, grocy_api=grocy_api)


@router.post("/lines/{line_id}/retry", response_model=MealPlanRetryResponse)
def retry_endpoint(
    line_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    row = retry_line(
        session,
        household_id=household_id,
        line_id=line_id,
        user_id=current_user.id,
        grocy_api=grocy_api,
    )
    enriched = enrich_lines(session, household_id=household_id, rows=[row], grocy_api=grocy_api)
    return MealPlanRetryResponse(line=enriched[0])


@router.delete("/lines/{line_id}/local", status_code=204)
def delete_local_endpoint(
    line_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    _: GrocyAPI = Depends(get_grocy_api),
) -> None:
    delete_local_failed(
        session,
        household_id=household_id,
        user_id=current_user.id,
        line_id=line_id,
    )


@router.patch("/lines/{line_id}", response_model=MealPlanLineRead)
def edit_line_endpoint(
    line_id: int,
    body: MealPlanLineEdit,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    row = update_line_amount(
        session,
        household_id=household_id,
        user_id=current_user.id,
        line_id=line_id,
        grocy_api=grocy_api,
        product_amount=body.product_amount,
        product_amount_stock=body.product_amount_stock,
        recipe_servings=body.recipe_servings,
    )
    enriched = enrich_lines(session, household_id=household_id, rows=[row], grocy_api=grocy_api)
    return enriched[0]


@router.delete("/lines/{line_id}", status_code=204)
def delete_synced_endpoint(
    line_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> None:
    delete_synced_line(
        session,
        household_id=household_id,
        user_id=current_user.id,
        line_id=line_id,
        grocy_api=grocy_api,
    )


@router.get("/job/{task_id}", response_model=MealPlanJobStatusResponse)
def job_status_endpoint(
    task_id: str,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> Any:
    state = read_job_state(task_id)
    if state is None:
        return MealPlanJobStatusResponse(
            task_id=task_id, state="PENDING", current=0, total=0, errors=[]
        )
    return MealPlanJobStatusResponse(**state)


@router.get("/sections", response_model=MealPlanSectionsResponse)
def sections_endpoint(
    _current_user: AuthenticatedUser = Depends(get_current_user),
    household_id: int = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    try:
        raw = get_or_load_sections(household_id, grocy_api)
    except GrocyError as g_err:
        raise HTTPException(status_code=502, detail=str(g_err)) from g_err
    return MealPlanSectionsResponse(sections=[MealPlanSection(**s) for s in raw])


@router.get("/units", response_model=MealPlanUnitsResponse)
def units_endpoint(
    _current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    product_grocy_id: int = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    exists = session.exec(
        select(Product.id).where(
            Product.grocy_id == product_grocy_id,
            Product.household_id == household_id,
        )
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Product not found in this household")

    try:
        payload = get_or_load_units_for_product(household_id, product_grocy_id, grocy_api)
    except GrocyError as g_err:
        raise HTTPException(status_code=502, detail=str(g_err)) from g_err
    return MealPlanUnitsResponse(
        units=[MealPlanUnit(**u) for u in payload["units"]],
        stock_to_grams_ml=payload.get("stock_to_grams_ml"),
    )


@router.get("/daily-totals", response_model=MealPlanDailyTotals)
def daily_totals_endpoint(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    household_id: int = Query(...),
    day: date = Query(...),
    grocy_api: GrocyAPI = Depends(get_grocy_api),
) -> Any:
    try:
        result = compute_daily_totals(
            session,
            household_id=household_id,
            user_id=current_user.id,
            day=day,
            grocy_api=grocy_api,
        )
    except GrocyError as g_err:
        raise HTTPException(status_code=502, detail=str(g_err)) from g_err
    return MealPlanDailyTotals(
        kcal=result["kcal"],
        protein=result["protein"],
        carbs=result["carbs"],
        sugars=result["sugars"],
        fat=result["fat"],
        sat_fat=result["sat_fat"],
        fibers=result["fibers"],
        missing_items=[MealPlanMissingItem(**m) for m in result["missing_items"]],
    )
