from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.auth import get_current_user, get_grocy_api
from app.db.base import get_db
from app.schemas.product import (
    ConsumeRequest,
    ConsumeResponse,
    ProductDetailResponse,
    ProductsListResponse,
)
from app.services.grocy_api import GrocyAPI
from app.services.product import (
    ProductSyncError,
    consume_daily_products,
    get_product_detail,
    get_products_with_pagination,
)

router = APIRouter()


@router.get("", response_model=ProductsListResponse)
def get_products(
    skip: int = Query(default=0, ge=0, description="Number of products to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of products to return"),
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
) -> Any:
    """
    Get all products with their latest nutritional data with pagination

    Requires authentication.
    """
    return get_products_with_pagination(db, skip=skip, limit=limit, household_id=household_id)


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
)
def get_product(
    product_id: int,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
) -> Any:
    """Get product details with data history"""
    try:
        return get_product_detail(db, product_id, household_id=household_id)
    except ProductSyncError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/consume", response_model=ConsumeResponse)
def consume_products(
    request: ConsumeRequest,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
) -> Any:
    """
    Process daily product consumption plan

    This endpoint accepts a date and processes the consumption plan for that day.
    The actual Grocy API logic should be implemented in the service layer.

    Requires authentication and Grocy API key.
    """
    try:
        return consume_daily_products(db, grocy_api, request.date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process consumption: {e!s}")
