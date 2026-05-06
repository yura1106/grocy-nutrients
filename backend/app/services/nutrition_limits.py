# backend/app/services/nutrition_limits.py
from datetime import date as date_type

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from app.core.auth import AuthenticatedUser
from app.core.nutrient_calculator import NegativeCarbsError, calculate_nutrients
from app.models.nutrition_limit import DailyNutritionLimit
from app.models.user_health_profile import UserHealthProfile
from app.schemas.nutrition_limit import (
    NutrientLimitsPreview,
    NutrientLimitsPreviewRequest,
    NutritionLimitCreate,
    NutritionLimitListResponse,
    NutritionLimitRead,
    NutritionLimitUpdate,
)


def preview_limits(
    db: Session,
    user: AuthenticatedUser,
    request: NutrientLimitsPreviewRequest,
) -> NutrientLimitsPreview:
    """Calculate nutrient limits without saving. Reads goal + deficit from user profile."""
    profile = db.exec(
        select(UserHealthProfile).where(UserHealthProfile.user_id == user.id)
    ).first()
    goal = (profile.goal if profile else None) or "maintain"
    calorie_deficit_percent = profile.calorie_deficit_percent if profile else None
    try:
        nutrients = calculate_nutrients(
            calories_burned=request.calories_burned,
            body_weight=request.body_weight,
            activity_level=request.activity_level,
            goal=goal,
            calorie_deficit_percent=calorie_deficit_percent,
        )
    except NegativeCarbsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return NutrientLimitsPreview(**nutrients)


def get_today_limit(
    db: Session, user: AuthenticatedUser, today: date_type
) -> DailyNutritionLimit | None:
    return db.exec(
        select(DailyNutritionLimit).where(
            DailyNutritionLimit.user_id == user.id,
            DailyNutritionLimit.date == today,
        )
    ).first()


def get_limit_list(
    db: Session,
    user: AuthenticatedUser,
    skip: int,
    limit: int,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
) -> NutritionLimitListResponse:
    base = select(DailyNutritionLimit).where(DailyNutritionLimit.user_id == user.id)
    if date_from is not None:
        base = base.where(DailyNutritionLimit.date >= date_from)
    if date_to is not None:
        base = base.where(DailyNutritionLimit.date <= date_to)
    total = db.exec(select(func.count()).select_from(base.subquery())).one()
    items = db.exec(
        base.order_by(col(DailyNutritionLimit.date).desc()).offset(skip).limit(limit)
    ).all()
    return NutritionLimitListResponse(
        items=[NutritionLimitRead.model_validate(r) for r in items],
        total=total,
    )


def create_limit(
    db: Session, user: AuthenticatedUser, data: NutritionLimitCreate
) -> DailyNutritionLimit:
    record = DailyNutritionLimit(user_id=user.id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_limit(
    db: Session, user: AuthenticatedUser, record_id: int, data: NutritionLimitUpdate
) -> DailyNutritionLimit:
    record = db.get(DailyNutritionLimit, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_limit(db: Session, user: AuthenticatedUser, record_id: int) -> None:
    record = db.get(DailyNutritionLimit, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(record)
    db.commit()
