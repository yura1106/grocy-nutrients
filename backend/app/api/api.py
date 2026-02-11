from fastapi import APIRouter

from app.api.endpoints import auth, users, sync, products, consumption, recipes, daily_nutrition

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(consumption.router, prefix="/consumption", tags=["consumption"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(daily_nutrition.router, prefix="/daily-nutrition", tags=["daily-nutrition"])