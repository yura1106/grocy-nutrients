"""rename meal_plan product_id/recipe_id to *_grocy_id

Revision ID: 028
Revises: 027
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op


revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("meal_plans", "product_id", new_column_name="product_grocy_id")
    op.alter_column("meal_plans", "recipe_id", new_column_name="recipe_grocy_id")


def downgrade() -> None:
    op.alter_column("meal_plans", "product_grocy_id", new_column_name="product_id")
    op.alter_column("meal_plans", "recipe_grocy_id", new_column_name="recipe_id")
