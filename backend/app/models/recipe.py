from typing import Optional
from datetime import datetime, date as date_type
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import ForeignKey, Integer, Date


class Recipe(SQLModel, table=True):
    """Recipe model for storing recipe basic info"""
    __tablename__ = "recipes"

    id: Optional[int] = Field(default=None, primary_key=True)
    grocy_id: int = Field(index=True, unique=True, description="Recipe ID from Grocy")
    name: str = Field(description="Recipe name")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    recipe_data: list["RecipeData"] = Relationship(back_populates="recipe")


class RecipeData(SQLModel, table=True):
    """Recipe data model for storing consumed recipe nutritional info"""
    __tablename__ = "recipes_data"

    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(
        sa_column=Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    servings: int = Field(description="Number of servings")
    price_per_serving: Optional[float] = Field(default=None, description="Price per serving")

    weight_per_serving: Optional[float] = Field(default=None, description="Weight of one serving in grams (from Grocy recipe linked product)")

    # Nutrients per serving
    calories: Optional[float] = Field(default=None)
    carbohydrates: Optional[float] = Field(default=None)
    carbohydrates_of_sugars: Optional[float] = Field(default=None)
    proteins: Optional[float] = Field(default=None)
    fats: Optional[float] = Field(default=None)
    fats_saturated: Optional[float] = Field(default=None)
    salt: Optional[float] = Field(default=None)
    fibers: Optional[float] = Field(default=None)

    consumed_at: datetime = Field(default_factory=datetime.utcnow, description="When recipe was consumed")
    consumed_date: Optional[date_type] = Field(default=None, sa_column=Column(Date(), nullable=True), description="Actual date of consumption (from meal plan)")

    # Relationship
    recipe: Optional[Recipe] = Relationship(back_populates="recipe_data")
