from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.sql import func
from sqlmodel import Boolean, Column, DateTime, Field, Integer, Numeric, SQLModel, String


class MealPlan(SQLModel, table=True):
    __tablename__ = "meal_plans"
    __table_args__ = (
        UniqueConstraint("household_id", "grocy_meal_plan_id", name="uq_meal_plans_grocy_id"),
        Index("ix_meal_plans_household_day", "household_id", "day"),
        Index(
            "ix_meal_plans_status_pending",
            "status",
            postgresql_where=text("status IN ('pending','syncing','failed')"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)

    household_id: int = Field(
        sa_column=Column(
            ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    user_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Grocy linkage (nullable until batch reconcile fills them in)
    grocy_meal_plan_id: int | None = Field(default=None, nullable=True)
    grocy_shadow_recipe_id: int | None = Field(default=None, nullable=True)

    # Mirrors Grocy payload
    type: str = Field(sa_column=Column(String(), nullable=False))
    day: date = Field(nullable=False)
    section_id: int = Field(sa_column=Column(Integer(), nullable=False))

    product_grocy_id: int | None = Field(default=None, nullable=True)
    product_amount: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=6), nullable=True),
    )
    # product_amount expressed in the product's stock unit. This is what Grocy
    # stores internally and what we POST as `product_amount` to /objects/meal_plan.
    # `product_amount` above stays in the user-introduced unit (qu_id below).
    product_amount_stock: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=6), nullable=True),
    )
    product_qu_id: int | None = Field(default=None, nullable=True)

    recipe_grocy_id: int | None = Field(default=None, nullable=True)
    recipe_servings: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=6), nullable=True),
    )

    # Free-text body for `type="note"` rows. NULL for product/recipe rows.
    note: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))

    # Lifecycle: pending | syncing | synced | failed
    status: str = Field(
        default="pending",
        sa_column=Column(String(), nullable=False, server_default="pending"),
    )
    error_message: str | None = Field(default=None, nullable=True)
    retry_count: int = Field(
        default=0,
        sa_column=Column(Integer(), nullable=False, server_default="0"),
    )

    done: bool = Field(
        default=False,
        sa_column=Column(Boolean(), nullable=False, server_default="false"),
    )
    done_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )
