"""add is_bundle to recipes and originating_recipe_grocy_id to consumed_products

Local-only bundle-recipe feature: `recipes.is_bundle` marks a grouping recipe
whose fresh products should have their sugars excluded from the daily total,
and `consumed_products.originating_recipe_grocy_id` records the real (positive)
sub-recipe each product came from so nested bundles are honored. Both are
local-only — never synced to Grocy.

Revision ID: 031
Revises: 030
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("is_bundle", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "consumed_products",
        sa.Column("originating_recipe_grocy_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consumed_products", "originating_recipe_grocy_id")
    op.drop_column("recipes", "is_bundle")
