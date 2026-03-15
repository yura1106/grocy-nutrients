"""
Schemas for daily nutrition import endpoints
"""

from pydantic import BaseModel


class DailyNutritionRow(BaseModel):
    """Single day nutrition record"""

    day: str  # Format: YYYY-MM-DD
    calories: float
    proteins: float
    carbohydrates: float
    carbohydrates_of_sugars: float
    fats: float
    fats_saturated: float
    salt: float
    fibers: float


class DailyNutritionImportRequest(BaseModel):
    """Request to import multiple daily nutrition rows"""

    rows: list[DailyNutritionRow]


class DailyNutritionImportResponse(BaseModel):
    """Response after importing daily nutrition data"""

    status: str
    imported_count: int
    skipped_count: int
    message: str


class DailyNutritionRead(BaseModel):
    """Single daily nutrition record for reading"""

    id: int
    day: str
    calories: float
    proteins: float
    carbohydrates: float
    carbohydrates_of_sugars: float
    fats: float
    fats_saturated: float
    salt: float
    fibers: float

    model_config = {"from_attributes": True}


class DailyNutritionListResponse(BaseModel):
    """Paginated list of daily nutrition records"""

    records: list[DailyNutritionRead]
    total: int
    skip: int
    limit: int
