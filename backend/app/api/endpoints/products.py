import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser, get_current_user, get_grocy_api
from app.db.base import get_db
from app.models.household import HouseholdUser
from app.models.product import Product
from app.schemas.product import (
    ConsumeRequest,
    ConsumeResponse,
    ProductDetailResponse,
    ProductsListResponse,
    SetProductFreshRequest,
    SetProductFreshResponse,
)
from app.services.grocy_api import GrocyAPI
from app.services.product import (
    ProductSyncError,
    consume_daily_products,
    get_product_detail,
    get_products_with_pagination,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ProductsListResponse)
def get_products(
    skip: int = Query(default=0, ge=0, description="Number of products to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of products to return"),
    search: str | None = Query(default=None, description="Search by name or Grocy ID"),
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
) -> Any:
    """
    Get all products with their latest nutritional data with pagination

    Requires authentication.
    """
    return get_products_with_pagination(
        db, skip=skip, limit=limit, search=search, household_id=household_id
    )


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


@router.patch("/{product_id}/fresh", response_model=SetProductFreshResponse)
def set_product_fresh(
    product_id: int,
    request: SetProductFreshRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
) -> Any:
    """
    Toggle a product's is_fresh flag.

    A "fresh" product (whole banana, apple, ...) has its sugars excluded from the
    tracked daily sugar total. Local-only flag — never synced to Grocy.

    Verifies active household membership (this is a write), then updates the
    product scoped to that household.
    """
    membership = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == current_user.id,
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this household.",
        )

    product = db.exec(
        select(Product).where(
            Product.id == product_id,
            Product.household_id == household_id,
        )
    ).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product.is_fresh = request.is_fresh
    db.add(product)
    db.commit()

    return SetProductFreshResponse(id=product.id, is_fresh=product.is_fresh)  # type: ignore[arg-type]


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
    except Exception:
        logger.exception("Failed to process consumption")
        raise HTTPException(status_code=500, detail="Failed to process consumption")
