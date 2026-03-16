from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class DailyNutrition(SQLModel, table=True):
    """
    DailyNutrition model - stores aggregated daily nutrition totals
    Used for importing historical data from CSV files
    """

    __tablename__ = "daily_nutrition"

    id: int | None = Field(default=None, primary_key=True)
    date: date_type = Field(nullable=False, unique=True, index=True, sa_type=Date())
    household_id: int | None = Field(
        default=None, foreign_key="households.id", nullable=True, index=True
    )
    user_id: int | None = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    calories: float = Field(default=0.0, nullable=False)
    proteins: float = Field(default=0.0, nullable=False)
    carbohydrates: float = Field(default=0.0, nullable=False)
    carbohydrates_of_sugars: float = Field(default=0.0, nullable=False)
    fats: float = Field(default=0.0, nullable=False)
    fats_saturated: float = Field(default=0.0, nullable=False)
    salt: float = Field(default=0.0, nullable=False)
    fibers: float = Field(default=0.0, nullable=False)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
