from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, ForeignKey, Integer
from sqlmodel import Column, Field, Relationship, SQLModel


class Recipe(SQLModel, table=True):
    """Recipe model for storing recipe basic info"""

    __tablename__ = "recipes"

    id: int | None = Field(default=None, primary_key=True)
    grocy_id: int = Field(index=True, unique=True, description="Recipe ID from Grocy")
    name: str = Field(description="Recipe name")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    recipe_data: list["RecipeData"] = Relationship(back_populates="recipe")


class RecipeData(SQLModel, table=True):
    """Recipe data model for storing consumed recipe nutritional info"""

    __tablename__ = "recipes_data"

    id: int | None = Field(default=None, primary_key=True)
    recipe_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("recipes.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )
    )
    servings: int = Field(description="Number of servings")
    price_per_serving: float | None = Field(default=None, description="Price per serving")

    weight_per_serving: float | None = Field(
        default=None,
        description="Weight of one serving in grams (from Grocy recipe linked product)",
    )

    # Nutrients per serving
    calories: float | None = Field(default=None)
    carbohydrates: float | None = Field(default=None)
    carbohydrates_of_sugars: float | None = Field(default=None)
    proteins: float | None = Field(default=None)
    fats: float | None = Field(default=None)
    fats_saturated: float | None = Field(default=None)
    salt: float | None = Field(default=None)
    fibers: float | None = Field(default=None)

    consumed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When recipe was consumed"
    )
    consumed_date: date_type | None = Field(
        default=None,
        sa_column=Column(Date(), nullable=True),
        description="Actual date of consumption (from meal plan)",
    )

    # Relationship
    recipe: Recipe | None = Relationship(back_populates="recipe_data")
