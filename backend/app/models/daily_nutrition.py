from datetime import datetime
from datetime import date as date_type
from typing import Optional
from sqlmodel import Field, SQLModel, Column, DateTime
from sqlalchemy import Date
from sqlalchemy.sql import func


class DailyNutrition(SQLModel, table=True):
    """
    DailyNutrition model - stores aggregated daily nutrition totals
    Used for importing historical data from CSV files
    """
    __tablename__ = "daily_nutrition"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date_type = Field(nullable=False, unique=True, index=True, sa_type=Date())
    calories: float = Field(default=0.0, nullable=False)
    proteins: float = Field(default=0.0, nullable=False)
    carbohydrates: float = Field(default=0.0, nullable=False)
    carbohydrates_of_sugars: float = Field(default=0.0, nullable=False)
    fats: float = Field(default=0.0, nullable=False)
    fats_saturated: float = Field(default=0.0, nullable=False)
    salt: float = Field(default=0.0, nullable=False)
    fibers: float = Field(default=0.0, nullable=False)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
