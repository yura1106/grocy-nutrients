from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import Session, select

from app.core.auth import get_current_user, get_grocy_api
from app.db.base import get_db
from app.models.household import HouseholdUser
from app.models.user import User
from app.schemas.product import SingleProductSyncResponse, SyncResponse
from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError
from app.services.product import (
    ProductSyncError,
    sync_grocy_products,
    sync_single_grocy_product_detailed,
)

router = APIRouter()


@router.post("/grocy-products", response_model=SyncResponse)
def sync_products_from_grocy(
    offset: int = 0,
    limit: int = 50,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_household_id: int = Header(..., alias="X-Household-Id"),
) -> Any:
    """
    Synchronize products from Grocy to local database
    """
    try:
        result = sync_grocy_products(db, grocy_api, offset=offset, limit=limit)
        hu = db.exec(
            select(HouseholdUser).where(
                HouseholdUser.household_id == x_household_id,
                HouseholdUser.user_id == current_user.id,
            )
        ).first()
        if hu:
            hu.last_products_sync_at = datetime.now(UTC)
            db.add(hu)
            db.commit()
        return result
    except GrocyAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Grocy API key",
        )
    except GrocyRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error contacting Grocy: {exc}",
        )
    except GrocyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Grocy API error: {exc}",
        )
    except ProductSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during synchronization: {exc!s}",
        )


@router.post("/grocy-product/{grocy_product_id}", response_model=SingleProductSyncResponse)
def sync_single_product_from_grocy(
    grocy_product_id: int,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
) -> Any:
    """
    Synchronize a single product from Grocy to local database

    This endpoint:
    - Fetches a specific product from Grocy API by ID
    - Upserts the product in local database
    - Creates historical record for nutritional data if changed
    - Returns both Grocy data and local database data for comparison

    Requires user to have a valid Grocy API key configured.
    """
    try:
        result = sync_single_grocy_product_detailed(db, grocy_api, grocy_product_id)
        return result
    except GrocyAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Grocy API key",
        )
    except GrocyRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error contacting Grocy: {exc}",
        )
    except GrocyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Grocy API error: {exc}",
        )
    except ProductSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during synchronization: {exc!s}",
        )
