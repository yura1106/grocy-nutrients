from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.services.grocy_api import GrocyAPI
from app.services.recipe import (
    calculate_recipe_nutrients,
    consume_recipe,
    RecipeCalculationError,
)
from app.schemas.recipe import (
    RecipeCalculateRequest,
    RecipeCalculateResponse,
    RecipeConsumeRequest,
    RecipeConsumeResponse,
    RecipesListResponse,
    RecipeSyncResponse,
    RecipesSyncAllResponse,
    RecipeDataSaveRequest,
    RecipeDataSaveResponse,
    RecipeDetailResponse,
    UpdateConversionRequest,
    UpdateConversionResponse,
    GrocyRecipeItem,
    CreateShoppingListRequest,
    CreateShoppingListResponse,
)
from typing import List
import random

router = APIRouter()


@router.post("/calculate", response_model=RecipeCalculateResponse)
def calculate_recipe(
    request: RecipeCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeCalculateResponse:
    """
    Calculate nutritional information for a recipe

    This endpoint:
    - Fetches recipe data from Grocy
    - Calculates total nutrients from all ingredients
    - Calculates per-serving nutrients if recipe has a product
    - Returns fulfillment status
    - Lists products with missing nutrient data

    Requires authentication and Grocy API key.
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    # Initialize Grocy API client
    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        result = calculate_recipe_nutrients(
            db=db,
            grocy_api=grocy_api,
            recipe_id=request.recipe_id,
            include_missing=True,
        )
        return result
    except RecipeCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate recipe nutrients: {str(e)}"
        )


@router.post("/update-conversion", response_model=UpdateConversionResponse)
def update_conversion(
    request: UpdateConversionRequest,
    current_user: User = Depends(get_current_user),
) -> UpdateConversionResponse:
    """
    Update or create a unit conversion for a product in Grocy.

    Requires authentication and Grocy API key.
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        grocy_api.update_unit_conversion(
            product_id=request.product_id,
            from_qu_id=request.from_qu_id,
            to_qu_id=request.to_qu_id,
            factor=request.factor,
        )
        return UpdateConversionResponse(
            status="success",
            message=f"Conversion factor updated to {request.factor}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update conversion: {str(e)}"
        )


@router.post("/consume", response_model=RecipeConsumeResponse)
def consume_recipe_endpoint(
    request: RecipeConsumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeConsumeResponse:
    """
    Consume a recipe in Grocy

    This endpoint:
    - Checks if all required products are available
    - Consumes the recipe if confirmed
    - Updates stock levels in Grocy

    Requires authentication and Grocy API key.
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Recipe consumption must be confirmed"
        )

    # Initialize Grocy API client
    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        result = consume_recipe(
            db=db,
            grocy_api=grocy_api,
            recipe_id=request.recipe_id,
            servings=request.servings,
            price_per_serving=request.price_per_serving,
            per_serving_nutrients=request.per_serving_nutrients,
        )
        return result
    except RecipeCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to consume recipe: {str(e)}"
        )

@router.get("/grocy-list", response_model=List[GrocyRecipeItem])
def get_grocy_recipes(
    current_user: User = Depends(get_current_user),
) -> List[GrocyRecipeItem]:
    """
    Fetch all recipes directly from Grocy API.
    Returns lightweight list with id and name only.
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)

    try:
        recipes_data = grocy_api.get("/objects/recipes", {"query[]": ["id>0"]})
        return [
            GrocyRecipeItem(id=r["id"], name=r.get("name", f"Recipe {r['id']}"))
            for r in recipes_data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recipes from Grocy: {str(e)}"
        )


# ===== Local Recipe Storage Endpoints =====

@router.get("/list", response_model=RecipesListResponse)
def get_recipes_list(
    skip: int = Query(default=0, ge=0, description="Number of recipes to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of recipes to return"),
    search: str = Query(default=None, description="Search by grocy ID or recipe name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipesListResponse:
    """
    Get all recipes with their latest consumption data with pagination

    Supports optional search by grocy_id or recipe name.
    Requires authentication.
    """
    from app.services.recipe import get_recipes_with_pagination

    return get_recipes_with_pagination(db, skip=skip, limit=limit, search=search)


@router.post("/sync/{recipe_id}", response_model=RecipeSyncResponse)
def sync_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeSyncResponse:
    """
    Sync a single recipe from Grocy to local database
    
    Requires authentication and Grocy API key.
    """
    from app.services.recipe import sync_recipe_from_grocy
    
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )
    
    grocy_api = GrocyAPI(current_user.grocy_api_key)
    
    try:
        result = sync_recipe_from_grocy(
            db=db,
            grocy_api=grocy_api,
            grocy_recipe_id=recipe_id,
        )
        return result
    except RecipeCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync recipe: {str(e)}"
        )


@router.post("/sync-all", response_model=RecipesSyncAllResponse)
def sync_all_recipes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipesSyncAllResponse:
    """
    Sync all recipes from Grocy to local database
    
    Requires authentication and Grocy API key.
    """
    from app.services.recipe import sync_all_recipes_from_grocy
    
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )
    
    grocy_api = GrocyAPI(current_user.grocy_api_key)
    
    try:
        result = sync_all_recipes_from_grocy(
            db=db,
            grocy_api=grocy_api,
        )
        return result
    except RecipeCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync recipes: {str(e)}"
        )


@router.post("/save-data", response_model=RecipeDataSaveResponse)
def save_recipe_data(
    request: RecipeDataSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeDataSaveResponse:
    """
    Save recipe consumption data to local database

    This endpoint saves the nutritional data after consuming a recipe.
    Requires authentication.
    """
    from app.services.recipe import save_recipe_consumption_data

    try:
        result = save_recipe_consumption_data(
            db=db,
            grocy_recipe_id=request.recipe_id,
            servings=request.servings,
            price_per_serving=request.price_per_serving,
            per_serving_nutrients=request.per_serving_nutrients,
        )
        return result
    except RecipeCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save recipe data: {str(e)}"
        )


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe_detail(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeDetailResponse:
    """
    Get recipe details with consumption history

    Returns recipe information and all consumption history records.
    Requires authentication.
    """
    from app.services.recipe import get_recipe_detail

    try:
        result = get_recipe_detail(db=db, recipe_id=recipe_id)
        return result
    except RecipeCalculationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recipe details: {str(e)}"
        )


@router.post("/create-shopping-list", response_model=CreateShoppingListResponse)
def create_shopping_list_for_recipe(
    request: CreateShoppingListRequest,
    current_user: User = Depends(get_current_user),
) -> CreateShoppingListResponse:
    """
    Create a Grocy shopping list with missing products for a recipe.

    Requires authentication and Grocy API key.
    """
    if not current_user.grocy_api_key:
        raise HTTPException(
            status_code=400,
            detail="Grocy API key not configured. Please set it in your profile."
        )

    grocy_api = GrocyAPI(current_user.grocy_api_key)
    list_name = f"recipe_{request.recipe_id}_check_{random.randint(100, 999)}"

    try:
        result = grocy_api.create_recipe_shopping_list(request.recipe_id, list_name)

        if result["items_added"] == 0:
            return CreateShoppingListResponse(
                status="success",
                shopping_list_name=list_name,
                items_added=0,
                message="No missing products found — all ingredients are in stock.",
            )

        return CreateShoppingListResponse(
            status="success",
            shopping_list_id=result["shopping_list_id"],
            shopping_list_name=list_name,
            items_added=result["items_added"],
            message=f"Shopping list '{list_name}' created with {result['items_added']} items.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create shopping list: {str(e)}"
        )
