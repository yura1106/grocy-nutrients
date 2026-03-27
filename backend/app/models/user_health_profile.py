from datetime import datetime

from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class UserHealthProfile(SQLModel, table=True):
    __tablename__ = "user_health_profiles"

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", unique=True, nullable=False, index=True)

    # Body measurements
    height: float | None = Field(default=None, nullable=True)
    weight: float | None = Field(default=None, nullable=True)
    activity_level: str | None = Field(default=None, nullable=True)
    goal: str | None = Field(default=None, nullable=True)

    # Daily nutrient limits
    daily_calories: float | None = Field(default=None, nullable=True)
    daily_proteins: float | None = Field(default=None, nullable=True)
    daily_fats: float | None = Field(default=None, nullable=True)
    daily_fats_saturated: float | None = Field(default=None, nullable=True)
    daily_carbohydrates: float | None = Field(default=None, nullable=True)
    daily_carbohydrates_of_sugars: float | None = Field(default=None, nullable=True)
    daily_salt: float | None = Field(default=None, nullable=True)
    daily_fibers: float | None = Field(default=None, nullable=True)
    calorie_deficit_percent: float | None = Field(default=None, nullable=True)

    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
