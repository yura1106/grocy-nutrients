"""
Schemas for consumption endpoints
"""
from typing import Dict, List, Any, Optional
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
    products_to_consume: Dict[Any, Any]
    products_to_buy: Dict[Any, Any]
    products_to_buy_detailed: List[ProductDetail]
    products_to_consume_detailed: List[ProductDetail]
    message: str


class ShoppingListRequest(BaseModel):
    """Request schema for creating shopping list"""
    date: str
    products_to_buy: Dict[Any, Any]


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
    product_id: Optional[int]
    name: str
    quantity: float
    note: str
    calories: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    proteins: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None


class MealPreview(BaseModel):
    """Schema for a single meal (recipe or standalone product) in dry-run preview"""
    type: str  # "recipe" or "product"
    recipe_name: Optional[str] = None
    recipe_grocy_id: Optional[int] = None
    available: bool = True
    missing_products_count: int = 0
    products: List[ProductPreview]


class DryRunResponse(BaseModel):
    """Response schema for dry run"""
    status: str
    date: str
    meals: List[MealPreview]
    total_calories: float
    total_nutrients: Dict[str, float]
    products_count: int


class MealPlanConsumptionHistoryItem(BaseModel):
    """Schema for meal plan consumption history record"""
    id: int
    date: str
    meal_plan_id: int
    recipe_grocy_id: int
    recipe_name: Optional[str] = None
    created_at: Optional[str] = None


class MealPlanConsumptionHistoryResponse(BaseModel):
    """Response for consumption history list"""
    items: List[MealPlanConsumptionHistoryItem]
    total: int


class ExecuteConsumptionRequest(BaseModel):
    """Request schema for executing consumption"""
    date: str


class ConsumedProductInfo(BaseModel):
    """Schema for consumed product info"""
    grocy_id: int
    name: str
    quantity: float
    recipe_grocy_id: Optional[int] = None


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
    consumed_meals: List[MealPlanConsumptionInfo]
    consumed_products: List[ConsumedProductInfo]
    skipped_meals: List[SkippedMealInfo]
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


class ConsumedProductsStatsResponse(BaseModel):
    """Response for consumed products statistics"""
    days: List[DailyNutrientStats]
    total: int


class ConsumedProductDetailItem(BaseModel):
    """Single product consumed on a day"""
    id: int
    product_name: str
    quantity: float  # in grams/ml
    recipe_grocy_id: Optional[int] = None
    calories: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    proteins: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None
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
    note: Optional[str] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None


class ConsumedDayDetailResponse(BaseModel):
    """Detailed breakdown of a single day's consumption"""
    date: str
    products: List[ConsumedProductDetailItem]
    notes: List[NoteDetailItem]
    total_calories: float
    total_carbohydrates: float
    total_carbohydrates_of_sugars: float
    total_proteins: float
    total_fats: float
    total_fats_saturated: float
    total_salt: float
    total_fibers: float


class ExecuteConsumptionJobResponse(BaseModel):
    """Response when consumption job is enqueued"""
    task_id: str
    status: str  # "queued"


class ConsumptionJobStatusResponse(BaseModel):
    """Status of a consumption background job"""
    task_id: str
    state: str  # "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE"
    step: Optional[str] = None   # human-readable progress message
    result: Optional[ExecuteConsumptionResponse] = None
    error: Optional[str] = None


class MealPlanConsumptionImportRow(BaseModel):
    """Single row from consumed_recipes.csv"""
    day: str           # YYYY-MM-DD
    meal_plan_id: int
    recipe_id: int     # recipe_grocy_id (may be negative from CSV)


class MealPlanConsumptionImportRequest(BaseModel):
    """Request body for importing consumed_recipes.csv"""
    rows: List[MealPlanConsumptionImportRow]


class MealPlanConsumptionImportResponse(BaseModel):
    """Response after importing consumed_recipes.csv"""
    imported: int
    skipped: int
    message: str
