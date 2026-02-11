from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.product import SyncResponse, SingleProductSyncResponse
from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError
from app.services.product import sync_grocy_products, sync_single_grocy_product_detailed, ProductSyncError

router = APIRouter()


@router.post("/grocy-products", response_model=SyncResponse)
def sync_products_from_grocy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Synchronize products from Grocy to local database

    This endpoint:
    - Fetches all products from Grocy API
    - Upserts products in local database
    - Creates historical records for nutritional data changes

    Requires user to have a valid Grocy API key configured.
    """
    # Verify user has Grocy API key
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grocy API key is not set for this user",
        )

    # Initialize Grocy API client
    grocy_api = GrocyAPI(current_user.grocy_api_key)

    # Perform synchronization
    try:
        result = sync_grocy_products(db, grocy_api)
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
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during synchronization: {str(exc)}",
        )


@router.post("/grocy-product/{grocy_product_id}", response_model=SingleProductSyncResponse)
def sync_single_product_from_grocy(
    grocy_product_id: int,
    current_user: User = Depends(get_current_user),
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
    # Verify user has Grocy API key
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grocy API key is not set for this user",
        )

    # Initialize Grocy API client
    grocy_api = GrocyAPI(current_user.grocy_api_key)

    # Perform synchronization
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
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during synchronization: {str(exc)}",
        )
