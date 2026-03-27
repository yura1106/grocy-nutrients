from datetime import date as date_type

from pydantic import BaseModel, Field


class NutrientLimitsPreviewRequest(BaseModel):
    calories_burned: float = Field(gt=0)
    body_weight: float = Field(gt=0, le=500)
    activity_level: str


class NutrientLimitsPreview(BaseModel):
    calories: float
    proteins: float
    carbohydrates: float
    carbohydrates_of_sugars: float
    fats: float
    fats_saturated: float
    salt: float
    fibers: float


class NutritionLimitCreate(BaseModel):
    date: date_type
    calories_burned: float | None = None
    body_weight: float | None = None
    activity_level: str | None = None
    calories: float | None = None
    proteins: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None


class NutritionLimitUpdate(BaseModel):
    calories_burned: float | None = None
    body_weight: float | None = None
    activity_level: str | None = None
    calories: float | None = None
    proteins: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None


class NutritionLimitRead(BaseModel):
    id: int
    date: date_type
    calories_burned: float | None
    body_weight: float | None
    activity_level: str | None
    calories: float | None
    proteins: float | None
    carbohydrates: float | None
    carbohydrates_of_sugars: float | None
    fats: float | None
    fats_saturated: float | None
    salt: float | None
    fibers: float | None

    model_config = {"from_attributes": True}


class NutritionLimitListResponse(BaseModel):
    items: list[NutritionLimitRead]
    total: int
