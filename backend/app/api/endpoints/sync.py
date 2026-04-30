import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser, get_current_user, get_grocy_api
from app.db.base import get_db
from app.models.household import HouseholdUser
from app.schemas.product import SingleProductSyncResponse, SyncResponse
from app.services.grocy_api import GrocyAPI, GrocyAuthError, GrocyError, GrocyRequestError
from app.services.product import (
    ProductSyncError,
    sync_grocy_products,
    sync_single_grocy_product_detailed,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/grocy-products", response_model=SyncResponse)
def sync_products_from_grocy(
    offset: int = 0,
    limit: int = 50,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
    household_id: int = Query(...),
) -> Any:
    """
    Synchronize products from Grocy to local database
    """
    try:
        result = sync_grocy_products(
            db, grocy_api, offset=offset, limit=limit, household_id=household_id
        )
        hu = db.exec(
            select(HouseholdUser).where(
                HouseholdUser.household_id == household_id,
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
        logger.error("Grocy request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error contacting Grocy server",
        )
    except GrocyError as exc:
        logger.error("Grocy API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Grocy API error",
        )
    except ProductSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected sync error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during synchronization",
        )


@router.post("/grocy-product/{grocy_product_id}", response_model=SingleProductSyncResponse)
def sync_single_product_from_grocy(
    grocy_product_id: int,
    grocy_api: GrocyAPI = Depends(get_grocy_api),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
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
        result = sync_single_grocy_product_detailed(
            db, grocy_api, grocy_product_id, household_id=household_id
        )
        return result
    except GrocyAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Grocy API key",
        )
    except GrocyRequestError as exc:
        logger.error("Grocy request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error contacting Grocy server",
        )
    except GrocyError as exc:
        logger.error("Grocy API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Grocy API error",
        )
    except ProductSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected sync error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during synchronization",
        )
