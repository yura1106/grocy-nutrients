"""add recipe_consumed_products table

Revision ID: 019
Revises: 018
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipe_consumed_products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recipe_data_id",
            sa.Integer(),
            sa.ForeignKey("recipes_data.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "product_data_id",
            sa.Integer(),
            sa.ForeignKey("products_data.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("recipe_consumed_products")
