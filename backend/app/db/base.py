from app.db.base_class import Base  # noqa
from app.db.session import SessionLocal
from app.models.daily_nutrition import DailyNutrition  # noqa
from app.models.household import Household, HouseholdUser, Role  # noqa
from app.models.product import Product, ProductData  # noqa
from app.models.recipe import Recipe, RecipeData  # noqa

# Імпорт моделей для Alembic metadata
from app.models.user import User  # noqa


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
