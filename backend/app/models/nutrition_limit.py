from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class DailyNutritionLimit(SQLModel, table=True):
    __tablename__ = "daily_nutrition_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_nutrition_limits_user_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    date: date_type = Field(nullable=False, sa_type=Date())  # type: ignore[call-overload]
    calories_burned: float | None = Field(default=None, nullable=True)
    body_weight: float | None = Field(default=None, nullable=True)
    activity_level: str | None = Field(default=None, nullable=True)
    calories: float | None = Field(default=None, nullable=True)
    proteins: float | None = Field(default=None, nullable=True)
    carbohydrates: float | None = Field(default=None, nullable=True)
    carbohydrates_of_sugars: float | None = Field(default=None, nullable=True)
    fats: float | None = Field(default=None, nullable=True)
    fats_saturated: float | None = Field(default=None, nullable=True)
    salt: float | None = Field(default=None, nullable=True)
    fibers: float | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )
