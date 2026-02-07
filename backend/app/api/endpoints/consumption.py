"""
Consumption endpoints - step-by-step meal plan consumption
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.consumption import (
    ConsumptionCheckRequest,
    ConsumptionCheckResponse,
    ShoppingListRequest,
    ShoppingListResponse,
    DryRunRequest,
    DryRunResponse,
    ExecuteConsumptionRequest,
    ExecuteConsumptionResponse,
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
