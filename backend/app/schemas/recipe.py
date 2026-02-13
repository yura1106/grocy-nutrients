from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class RecipeIngredient(BaseModel):
    """Single recipe ingredient"""
    product_id: int
    product_id_effective: int
    name: str
    amount: float
    unit: Optional[str] = None


class RecipeNutrients(BaseModel):
    """Recipe nutritional information"""
    calories: float
    proteins: float
    carbohydrates: float
    carbohydrates_of_sugars: float
    fats: float
    fats_saturated: float
    salt: float
    fibers: float


class RecipeFulfillment(BaseModel):
    """Recipe fulfillment status from Grocy"""
    id: int
    recipe_id: int
    need_fulfilled: int
    need_fulfilled_with_shopping_list: int
    missing_products_count: int
    costs: float
    costs_per_serving: Optional[float] = None
    calories: Optional[float] = None
    due_score: int
    product_names_comma_separated: str
    prices_incomplete: int


class MissingNutrients(BaseModel):
    """Products with missing nutrient data"""
    calories: List[str] = []
    proteins: List[str] = []
    carbohydrates: List[str] = []
    carbohydrates_of_sugars: List[str] = []
    fats: List[str] = []
    fats_saturated: List[str] = []
    salt: List[str] = []
    fibers: List[str] = []


class RecipeCalculateRequest(BaseModel):
    """Request to calculate recipe nutrients"""
    recipe_id: int


class RecipeCalculateResponse(BaseModel):
    """Response with calculated recipe nutrients"""
    status: str
    recipe_id: int
    recipe_name: str
    has_product: bool
    product_id: Optional[int] = None
    product_url: Optional[str] = None
    desired_servings: Optional[int] = None
    product_conversion_factor: Optional[float] = None
    product_conversion_unit: Optional[str] = None
    product_qu_id_stock: Optional[int] = None
    product_conversion_target_qu_id: Optional[int] = None
    ingredients: List[RecipeIngredient]
    total_nutrients: RecipeNutrients
    per_serving_nutrients: Optional[RecipeNutrients] = None
    fulfillment: RecipeFulfillment
    missing_nutrients: Optional[MissingNutrients] = None
    can_consume: bool
    message: str


class UpdateConversionRequest(BaseModel):
    """Request to update product unit conversion in Grocy"""
    product_id: int
    from_qu_id: int
    to_qu_id: int
    factor: float


class UpdateConversionResponse(BaseModel):
    """Response after updating unit conversion"""
    status: str
    message: str


class RecipeConsumeRequest(BaseModel):
    """Request to consume a recipe"""
    recipe_id: int
    confirmed: bool = False
    # Optional data to save after consumption
    servings: Optional[int] = None
    price_per_serving: Optional[float] = None
    per_serving_nutrients: Optional[RecipeNutrients] = None


class RecipeConsumeResponse(BaseModel):
    """Response after consuming a recipe"""
    status: str
    recipe_id: int
    message: str
    consumed: bool


# ===== Local Recipe Storage Schemas =====


class RecipeWithData(BaseModel):
    """Recipe with its latest consumption data"""
    id: int
    grocy_id: int
    name: str
    created_at: str
    latest_servings: Optional[int] = None
    latest_price_per_serving: Optional[float] = None
    latest_calories: Optional[float] = None
    latest_proteins: Optional[float] = None
    latest_carbohydrates: Optional[float] = None
    latest_fats: Optional[float] = None
    latest_consumed_at: Optional[str] = None


class RecipesListResponse(BaseModel):
    """Response with list of recipes"""
    recipes: List[RecipeWithData]
    total: int
    skip: int
    limit: int


class RecipeSyncRequest(BaseModel):
    """Request to sync recipe from Grocy"""
    recipe_id: int


class RecipeSyncResponse(BaseModel):
    """Response after syncing recipe"""
    status: str
    recipe_id: int
    recipe_name: str
    message: str


class RecipesSyncAllResponse(BaseModel):
    """Response after syncing all recipes"""
    status: str
    processed: int
    synced: int
    errors: int
    message: str


class RecipeDataSaveRequest(BaseModel):
    """Request to save recipe consumption data"""
    recipe_id: int
    servings: int
    price_per_serving: Optional[float] = None
    per_serving_nutrients: RecipeNutrients


class RecipeDataSaveResponse(BaseModel):
    """Response after saving recipe data"""
    status: str
    recipe_data_id: int
    message: str


class RecipeHistoryItem(BaseModel):
    """Single recipe consumption history item"""
    id: int
    servings: int
    price_per_serving: Optional[float] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None
    consumed_at: str


class RecipeDetailResponse(BaseModel):
    """Response with recipe details and consumption history"""
    id: int
    grocy_id: int
    name: str
    created_at: str
    history: List[RecipeHistoryItem]
    total_history: int


class GrocyRecipeItem(BaseModel):
    """Lightweight recipe item fetched from Grocy"""
    id: int
    name: str
