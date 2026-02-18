from datetime import datetime
from datetime import date as date_type
from typing import Optional, List
from sqlmodel import Field, SQLModel, Column, DateTime, Relationship
from sqlalchemy import Date
from sqlalchemy.sql import func


class Product(SQLModel, table=True):
    """
    Product model - stores basic product information from Grocy
    """
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    grocy_id: int = Field(unique=True, index=True, nullable=False)
    active: bool = Field(default=True, nullable=False)
    name: str = Field(nullable=False)
    product_group_id: int = Field(nullable=False)
    qu_id_stock: Optional[int] = Field(default=None, nullable=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Relationship to product data (history)
    product_data: List["ProductData"] = Relationship(back_populates="product")


class ProductData(SQLModel, table=True):
    """
    ProductData model - stores nutritional data history for products
    Keeps historical records of changes to nutritional information
    """
    __tablename__ = "products_data"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", nullable=False, index=True)
    price: float = Field(default=10.0, nullable=False)
    calories: Optional[float] = Field(default=None, nullable=True)
    carbohydrates: Optional[float] = Field(default=None, nullable=True)
    carbohydrates_of_sugars: Optional[float] = Field(default=None, nullable=True)
    proteins: Optional[float] = Field(default=None, nullable=True)
    fats: Optional[float] = Field(default=None, nullable=True)
    fats_saturated: Optional[float] = Field(default=None, nullable=True)
    salt: Optional[float] = Field(default=None, nullable=True)
    fibers: Optional[float] = Field(default=None, nullable=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Relationship to product
    product: Optional[Product] = Relationship(back_populates="product_data")


class ConsumedProduct(SQLModel, table=True):
    """
    ConsumedProduct model - stores consumed products per day
    """
    __tablename__ = "consumed_products"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_data_id: int = Field(foreign_key="products_data.id", nullable=False, index=True)
    date: date_type = Field(nullable=False, index=True, sa_type=Date())
    quantity: float = Field(nullable=False)
    recipe_grocy_id: Optional[int] = Field(default=None, nullable=True)
    recipe_grocy_id_shadow: Optional[int] = Field(default=None, nullable=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class MealPlanConsumption(SQLModel, table=True):
    """
    MealPlanConsumption model - stores meal plan consumption history (replaces CSV files)
    """
    __tablename__ = "meal_plan_consumptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date_type = Field(nullable=False, index=True, sa_type=Date())
    meal_plan_id: int = Field(nullable=False)
    recipe_grocy_id: int = Field(nullable=False)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class NoteNutrients(SQLModel, table=True):
    """
    NoteNutrients model - stores nutrients from meal plan note entries.
    Multiple notes can exist per day.
    Format example: "Калорій:500/Білків:30/Вуглеводів:60/Жирів:15"
    """
    __tablename__ = "note_nutrients"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date_type = Field(nullable=False, index=True, sa_type=Date())
    note: Optional[str] = Field(default=None, nullable=True)
    calories: Optional[float] = Field(default=None, nullable=True)
    proteins: Optional[float] = Field(default=None, nullable=True)
    carbohydrates: Optional[float] = Field(default=None, nullable=True)
    carbohydrates_of_sugars: Optional[float] = Field(default=None, nullable=True)
    fats: Optional[float] = Field(default=None, nullable=True)
    fats_saturated: Optional[float] = Field(default=None, nullable=True)
    salt: Optional[float] = Field(default=None, nullable=True)
    fibers: Optional[float] = Field(default=None, nullable=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
