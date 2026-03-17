from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel


class Product(SQLModel, table=True):
    """
    Product model - stores basic product information from Grocy
    """

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("grocy_id", "household_id", name="uq_products_grocy_id_household"),
    )

    id: int | None = Field(default=None, primary_key=True)
    grocy_id: int = Field(index=True, nullable=False)
    active: bool = Field(default=True, nullable=False)
    name: str = Field(nullable=False)
    product_group_id: int = Field(nullable=False)
    qu_id_stock: int | None = Field(default=None, nullable=True)
    household_id: int | None = Field(
        default=None, foreign_key="households.id", nullable=True, index=True
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationship to product data (history)
    product_data: list["ProductData"] = Relationship(back_populates="product")


class ProductData(SQLModel, table=True):
    """
    ProductData model - stores nutritional data history for products
    Keeps historical records of changes to nutritional information
    """

    __tablename__ = "products_data"

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", nullable=False, index=True)
    price: float = Field(default=10.0, nullable=False)
    calories: float | None = Field(default=None, nullable=True)
    carbohydrates: float | None = Field(default=None, nullable=True)
    carbohydrates_of_sugars: float | None = Field(default=None, nullable=True)
    proteins: float | None = Field(default=None, nullable=True)
    fats: float | None = Field(default=None, nullable=True)
    fats_saturated: float | None = Field(default=None, nullable=True)
    salt: float | None = Field(default=None, nullable=True)
    fibers: float | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationship to product
    product: Product | None = Relationship(back_populates="product_data")


class ConsumedProduct(SQLModel, table=True):
    """
    ConsumedProduct model - stores consumed products per day
    """

    __tablename__ = "consumed_products"

    id: int | None = Field(default=None, primary_key=True)
    product_data_id: int = Field(foreign_key="products_data.id", nullable=False, index=True)
    date: date_type = Field(nullable=False, index=True, sa_type=Date())
    quantity: float = Field(nullable=False)
    cost: float | None = Field(default=None, nullable=True)
    recipe_grocy_id: int | None = Field(default=None, nullable=True)
    recipe_grocy_id_shadow: int | None = Field(default=None, nullable=True)
    household_id: int | None = Field(
        default=None, foreign_key="households.id", nullable=True, index=True
    )
    user_id: int | None = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class MealPlanConsumption(SQLModel, table=True):
    """
    MealPlanConsumption model - stores meal plan consumption history (replaces CSV files)
    """

    __tablename__ = "meal_plan_consumptions"

    id: int | None = Field(default=None, primary_key=True)
    date: date_type = Field(nullable=False, index=True, sa_type=Date())
    meal_plan_id: int = Field(nullable=False)
    recipe_grocy_id: int = Field(nullable=False)
    household_id: int | None = Field(
        default=None, foreign_key="households.id", nullable=True, index=True
    )
    user_id: int | None = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class NoteNutrients(SQLModel, table=True):
    """
    NoteNutrients model - stores nutrients from meal plan note entries.
    Multiple notes can exist per day.
    Format example: "Калорій:500/Білків:30/Вуглеводів:60/Жирів:15"
    """

    __tablename__ = "note_nutrients"

    id: int | None = Field(default=None, primary_key=True)
    date: date_type = Field(nullable=False, index=True, sa_type=Date())
    note: str | None = Field(default=None, nullable=True)
    household_id: int | None = Field(
        default=None, foreign_key="households.id", nullable=True, index=True
    )
    user_id: int | None = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    calories: float | None = Field(default=None, nullable=True)
    proteins: float | None = Field(default=None, nullable=True)
    carbohydrates: float | None = Field(default=None, nullable=True)
    carbohydrates_of_sugars: float | None = Field(default=None, nullable=True)
    fats: float | None = Field(default=None, nullable=True)
    fats_saturated: float | None = Field(default=None, nullable=True)
    salt: float | None = Field(default=None, nullable=True)
    fibers: float | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
