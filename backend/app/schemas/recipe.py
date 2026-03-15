from pydantic import BaseModel


class RecipeIngredient(BaseModel):
    """Single recipe ingredient"""

    product_id: int
    product_id_effective: int
    name: str
    amount: float
    unit: str | None = None


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
    costs_per_serving: float | None = None
    calories: float | None = None
    due_score: int
    product_names_comma_separated: str
    prices_incomplete: int


class MissingNutrients(BaseModel):
    """Products with missing nutrient data"""

    calories: list[str] = []
    proteins: list[str] = []
    carbohydrates: list[str] = []
    carbohydrates_of_sugars: list[str] = []
    fats: list[str] = []
    fats_saturated: list[str] = []
    salt: list[str] = []
    fibers: list[str] = []


class RecipeCalculateRequest(BaseModel):
    """Request to calculate recipe nutrients"""

    recipe_id: int


class RecipeCalculateResponse(BaseModel):
    """Response with calculated recipe nutrients"""

    status: str
    recipe_id: int
    recipe_name: str
    has_product: bool
    product_id: int | None = None
    product_url: str | None = None
    desired_servings: int | None = None
    weight_per_serving: float | None = None
    product_conversion_factor: float | None = None
    product_conversion_unit: str | None = None
    product_qu_id_stock: int | None = None
    product_conversion_target_qu_id: int | None = None
    ingredients: list[RecipeIngredient]
    total_nutrients: RecipeNutrients
    per_serving_nutrients: RecipeNutrients | None = None
    fulfillment: RecipeFulfillment
    missing_nutrients: MissingNutrients | None = None
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
    servings: int | None = None
    price_per_serving: float | None = None
    weight_per_serving: float | None = None
    per_serving_nutrients: RecipeNutrients | None = None


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
    latest_servings: int | None = None
    latest_price_per_serving: float | None = None
    latest_weight_per_serving: float | None = None
    latest_calories: float | None = None
    latest_proteins: float | None = None
    latest_carbohydrates: float | None = None
    latest_fats: float | None = None
    latest_consumed_at: str | None = None


class RecipesListResponse(BaseModel):
    """Response with list of recipes"""

    recipes: list[RecipeWithData]
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
    price_per_serving: float | None = None
    weight_per_serving: float | None = None
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
    price_per_serving: float | None = None
    weight_per_serving: float | None = None
    calories: float | None = None
    proteins: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None
    consumed_at: str
    consumed_date: str | None = None


class RecipeDetailResponse(BaseModel):
    """Response with recipe details and consumption history"""

    id: int
    grocy_id: int
    name: str
    created_at: str
    history: list[RecipeHistoryItem]
    total_history: int


class GrocyRecipeItem(BaseModel):
    """Lightweight recipe item fetched from Grocy"""

    id: int
    name: str


class CreateShoppingListRequest(BaseModel):
    """Request to create a shopping list for missing recipe products"""

    recipe_id: int


class CreateShoppingListResponse(BaseModel):
    """Response after creating a shopping list"""

    status: str
    shopping_list_id: int | None = None
    shopping_list_name: str
    items_added: int
    message: str
