"""
Service for daily nutrition import and retrieval
"""

from datetime import date

from sqlmodel import Session, func, select

from app.models.daily_nutrition import DailyNutrition
from app.schemas.daily_nutrition import (
    DailyNutritionImportResponse,
    DailyNutritionListResponse,
    DailyNutritionRead,
    DailyNutritionRow,
)


class DailyNutritionError(Exception):
    pass


def import_daily_nutrition(
    db: Session, rows: list[DailyNutritionRow]
) -> DailyNutritionImportResponse:
    """Import daily nutrition rows, skipping dates that already exist."""
    imported_count = 0
    skipped_count = 0

    for row in rows:
        parsed_date = date.fromisoformat(row.day)

        existing = db.exec(
            select(DailyNutrition).where(DailyNutrition.date == parsed_date)
        ).first()

        if existing:
            skipped_count += 1
            continue

        record = DailyNutrition(
            date=parsed_date,
            calories=row.calories,
            proteins=row.proteins,
            carbohydrates=row.carbohydrates,
            carbohydrates_of_sugars=row.carbohydrates_of_sugars,
            fats=row.fats,
            fats_saturated=row.fats_saturated,
            salt=row.salt,
            fibers=row.fibers,
        )
        db.add(record)
        imported_count += 1

    db.commit()

    return DailyNutritionImportResponse(
        status="success",
        imported_count=imported_count,
        skipped_count=skipped_count,
        message=f"Imported {imported_count} records, skipped {skipped_count} duplicates.",
    )


def get_daily_nutrition_list(
    db: Session, skip: int = 0, limit: int = 50
) -> DailyNutritionListResponse:
    """Get paginated list of daily nutrition records ordered by date desc."""
    total = db.exec(select(func.count()).select_from(DailyNutrition)).one()

    records = db.exec(
        select(DailyNutrition).order_by(DailyNutrition.date.desc()).offset(skip).limit(limit)
    ).all()

    return DailyNutritionListResponse(
        records=[
            DailyNutritionRead(
                id=r.id,
                day=r.date.isoformat(),
                calories=r.calories,
                proteins=r.proteins,
                carbohydrates=r.carbohydrates,
                carbohydrates_of_sugars=r.carbohydrates_of_sugars,
                fats=r.fats,
                fats_saturated=r.fats_saturated,
                salt=r.salt,
                fibers=r.fibers,
            )
            for r in records
        ],
        total=total,
        skip=skip,
        limit=limit,
    )
