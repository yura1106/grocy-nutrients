from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.product import ProductsListResponse, ConsumeRequest, ConsumeResponse
from app.services.product import get_products_with_pagination, consume_daily_products
from app.services.grocy_api import GrocyAPI

router = APIRouter()


@router.get("", response_model=ProductsListResponse)
def get_products(
    skip: int = Query(default=0, ge=0, description="Number of products to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of products to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get all products with their latest nutritional data with pagination

    Requires authentication.
    """
    return get_products_with_pagination(db, skip=skip, limit=limit)


@router.post("/consume", response_model=ConsumeResponse)
def consume_products(
    request: ConsumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Process daily product consumption plan

    This endpoint accepts a date and processes the consumption plan for that day.
    The actual Grocy API logic should be implemented in the service layer.

    Requires authentication and Grocy API key.
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    # Initialize Grocy API client
    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        return consume_daily_products(db, grocy_api, request.date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process consumption: {str(e)}"
        )
