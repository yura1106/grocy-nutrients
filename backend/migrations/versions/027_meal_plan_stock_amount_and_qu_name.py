"""add product_amount_stock and product_qu_name to meal_plans

Revision ID: 027
Revises: 026
Create Date: 2026-05-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meal_plans",
        sa.Column("product_amount_stock", sa.Numeric(precision=20, scale=6), nullable=True),
    )
    op.add_column(
        "meal_plans",
        sa.Column("product_qu_name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meal_plans", "product_qu_name")
    op.drop_column("meal_plans", "product_amount_stock")
