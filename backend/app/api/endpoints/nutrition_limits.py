# backend/app/api/endpoints/nutrition_limits.py
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import get_db
from app.schemas.nutrition_limit import (
    NutrientLimitsPreview,
    NutrientLimitsPreviewRequest,
    NutritionLimitCreate,
    NutritionLimitListResponse,
    NutritionLimitRead,
    NutritionLimitUpdate,
)
from app.services import nutrition_limits as svc

router = APIRouter()


@router.post("/preview", response_model=NutrientLimitsPreview)
def preview_limits(
    request: NutrientLimitsPreviewRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.preview_limits(db, current_user, request)


@router.get("", response_model=NutritionLimitListResponse)
def list_limits(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.get_limit_list(db, current_user, skip, limit, date_from, date_to)


@router.get("/today", response_model=NutritionLimitRead | None)
def get_today(
    today: date = Query(default_factory=date.today),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.get_today_limit(db, current_user, today)


@router.post("", response_model=NutritionLimitRead, status_code=status.HTTP_201_CREATED)
def create_limit(
    data: NutritionLimitCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.create_limit(db, current_user, data)


@router.put("/{record_id}", response_model=NutritionLimitRead)
def update_limit(
    record_id: int,
    data: NutritionLimitUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.update_limit(db, current_user, record_id, data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_limit(
    record_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    svc.delete_limit(db, current_user, record_id)
