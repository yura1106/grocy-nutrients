from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    consumption,
    daily_nutrition,
    households,
    nutrition_limits,
    products,
    recipes,
    sync,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(consumption.router, prefix="/consumption", tags=["consumption"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(
    daily_nutrition.router, prefix="/daily-nutrition", tags=["daily-nutrition"]
)
api_router.include_router(households.router, prefix="/households", tags=["households"])
api_router.include_router(
    nutrition_limits.router, prefix="/nutrition-limits", tags=["nutrition-limits"]
)
