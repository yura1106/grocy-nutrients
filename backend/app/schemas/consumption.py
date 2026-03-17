"""
Schemas for consumption endpoints
"""

from typing import Any

from pydantic import BaseModel


class ConsumptionCheckRequest(BaseModel):
    """Request schema for checking product availability"""

    date: str  # Format: YYYY-MM-DD


class ProductToBuy(BaseModel):
    """Schema for product that needs to be purchased"""

    product_id: int
    amount: float
    note: str


class ProductDetail(BaseModel):
    """Schema for detailed product information"""

    product_id: int
    name: str
    amount: float
    note: str


class ConsumptionCheckResponse(BaseModel):
    """Response schema for availability check"""

    status: str  # "success" or "insufficient_stock"
    products_to_consume: dict[Any, Any]
    products_to_buy: dict[Any, Any]
    products_to_buy_detailed: list[ProductDetail]
    products_to_consume_detailed: list[ProductDetail]
    message: str


class ShoppingListRequest(BaseModel):
    """Request schema for creating shopping list"""

    date: str
    products_to_buy: dict[Any, Any]


class ShoppingListResponse(BaseModel):
    """Response schema for shopping list creation"""

    status: str
    message: str
    products_count: int


class DryRunRequest(BaseModel):
    """Request schema for dry run"""

    date: str


class ProductPreview(BaseModel):
    """Schema for product consumption preview"""

    grocy_id: int
    product_id: int | None
    name: str
    quantity: float
    note: str
    calories: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    proteins: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None


class MealPreview(BaseModel):
    """Schema for a single meal (recipe or standalone product) in dry-run preview"""

    type: str  # "recipe" or "product"
    recipe_name: str | None = None
    recipe_grocy_id: int | None = None
    available: bool = True
    missing_products_count: int = 0
    products: list[ProductPreview]


class DryRunResponse(BaseModel):
    """Response schema for dry run"""

    status: str
    date: str
    meals: list[MealPreview]
    total_calories: float
    total_nutrients: dict[str, float]
    products_count: int


class MealPlanConsumptionHistoryItem(BaseModel):
    """Schema for meal plan consumption history record"""

    id: int
    date: str
    meal_plan_id: int
    recipe_grocy_id: int
    recipe_name: str | None = None
    created_at: str | None = None


class MealPlanConsumptionHistoryResponse(BaseModel):
    """Response for consumption history list"""

    items: list[MealPlanConsumptionHistoryItem]
    total: int


class ExecuteConsumptionRequest(BaseModel):
    """Request schema for executing consumption"""

    date: str


class ConsumedProductInfo(BaseModel):
    """Schema for consumed product info"""

    grocy_id: int
    name: str
    quantity: float
    recipe_grocy_id: int | None = None


class MealPlanConsumptionInfo(BaseModel):
    """Schema for meal plan consumption record"""

    meal_plan_id: int
    recipe_grocy_id: int
    recipe_name: str


class SkippedMealInfo(BaseModel):
    """Schema for skipped meal (missing products)"""

    meal_plan_id: int
    recipe_name: str
    reason: str


class ExecuteConsumptionResponse(BaseModel):
    """Response schema for consumption execution"""

    status: str
    date: str
    consumed_meals: list[MealPlanConsumptionInfo]
    consumed_products: list[ConsumedProductInfo]
    skipped_meals: list[SkippedMealInfo]
    products_count: int
    message: str


class DailyNutrientStats(BaseModel):
    """Schema for daily nutrient totals from consumed products"""

    date: str
    total_calories: float
    total_carbohydrates: float
    total_carbohydrates_of_sugars: float
    total_proteins: float
    total_fats: float
    total_fats_saturated: float
    total_salt: float
    total_fibers: float
    products_count: int
    total_cost: float | None = None


class ConsumedProductsStatsResponse(BaseModel):
    """Response for consumed products statistics"""

    days: list[DailyNutrientStats]
    total: int


class ConsumedProductDetailItem(BaseModel):
    """Single product consumed on a day"""

    id: int
    product_name: str
    quantity: float  # in grams/ml
    recipe_grocy_id: int | None = None
    calories: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    proteins: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None
    cost: float | None = None
    # pre-multiplied totals (per_100g * quantity / 100)
    total_calories: float = 0.0
    total_carbohydrates: float = 0.0
    total_carbohydrates_of_sugars: float = 0.0
    total_proteins: float = 0.0
    total_fats: float = 0.0
    total_fats_saturated: float = 0.0
    total_salt: float = 0.0
    total_fibers: float = 0.0


class NoteDetailItem(BaseModel):
    """Note nutrients entry for a day"""

    id: int
    note: str | None = None
    calories: float | None = None
    proteins: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None


class ConsumedDayDetailResponse(BaseModel):
    """Detailed breakdown of a single day's consumption"""

    date: str
    products: list[ConsumedProductDetailItem]
    notes: list[NoteDetailItem]
    total_calories: float
    total_carbohydrates: float
    total_carbohydrates_of_sugars: float
    total_proteins: float
    total_fats: float
    total_fats_saturated: float
    total_salt: float
    total_fibers: float
    total_cost: float | None = None


class ExecuteConsumptionJobResponse(BaseModel):
    """Response when consumption job is enqueued"""

    task_id: str
    status: str  # "queued"


class ConsumptionJobStatusResponse(BaseModel):
    """Status of a consumption background job"""

    task_id: str
    state: str  # "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE"
    step: str | None = None  # human-readable progress message
    result: ExecuteConsumptionResponse | None = None
    error: str | None = None


class MealPlanConsumptionImportRow(BaseModel):
    """Single row from consumed_recipes.csv"""

    day: str  # YYYY-MM-DD
    meal_plan_id: int
    recipe_id: int  # recipe_grocy_id (may be negative from CSV)


class MealPlanConsumptionImportRequest(BaseModel):
    """Request body for importing consumed_recipes.csv"""

    rows: list[MealPlanConsumptionImportRow]


class MealPlanConsumptionImportResponse(BaseModel):
    """Response after importing consumed_recipes.csv"""

    imported: int
    skipped: int
    message: str
