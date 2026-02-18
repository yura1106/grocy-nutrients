"""add meal_plan_consumptions table and recipe_grocy_id to consumed_products

Revision ID: 007
Revises: 006
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New table for meal plan consumption history (replaces CSV files)
    op.create_table(
        "meal_plan_consumptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_plan_id", sa.Integer(), nullable=False),
        sa.Column("recipe_grocy_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_meal_plan_consumptions_date"),
        "meal_plan_consumptions",
        ["date"],
        unique=False,
    )

    # Add recipe_grocy_id to consumed_products (nullable for standalone product meals)
    op.add_column(
        "consumed_products",
        sa.Column("recipe_grocy_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consumed_products", "recipe_grocy_id")
    op.drop_index(
        op.f("ix_meal_plan_consumptions_date"),
        table_name="meal_plan_consumptions",
    )
    op.drop_table("meal_plan_consumptions")
