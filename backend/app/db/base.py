from app.db.base_class import Base  # noqa
from app.db.session import SessionLocal

# User must be imported before models that FK to users.id
from app.models.user import User  # noqa
from app.models.daily_nutrition import DailyNutrition  # noqa
from app.models.household import Household, HouseholdUser, Role  # noqa
from app.models.recipe import Recipe, RecipeData  # noqa


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
