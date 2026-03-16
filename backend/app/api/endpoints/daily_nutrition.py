"""
API endpoints for daily nutrition import and listing
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.daily_nutrition import (
    DailyNutritionImportRequest,
    DailyNutritionImportResponse,
    DailyNutritionListResponse,
)
from app.services.daily_nutrition import (
    DailyNutritionError,
    get_daily_nutrition_list,
    import_daily_nutrition,
)

router = APIRouter()


@router.post(
    "/import",
    response_model=DailyNutritionImportResponse,
)
def import_nutrition(
    request: DailyNutritionImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
):
    """Import daily nutrition data from parsed CSV rows."""
    try:
        return import_daily_nutrition(
            db, request.rows, household_id=household_id, user_id=current_user.id
        )
    except DailyNutritionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=DailyNutritionListResponse,
)
def list_nutrition(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
):
    """Get paginated list of daily nutrition records."""
    try:
        return get_daily_nutrition_list(
            db, skip=skip, limit=limit, household_id=household_id, user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
