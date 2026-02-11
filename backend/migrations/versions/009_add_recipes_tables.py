"""add recipes tables

Revision ID: 009
Revises: 008
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create recipes table
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grocy_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grocy_id"),
    )
    op.create_index(op.f("ix_recipes_grocy_id"), "recipes", ["grocy_id"], unique=True)

    # Create recipes_data table
    op.create_table(
        "recipes_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("price_per_serving", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("carbohydrates", sa.Float(), nullable=True),
        sa.Column("carbohydrates_of_sugars", sa.Float(), nullable=True),
        sa.Column("proteins", sa.Float(), nullable=True),
        sa.Column("fats", sa.Float(), nullable=True),
        sa.Column("fats_saturated", sa.Float(), nullable=True),
        sa.Column("salt", sa.Float(), nullable=True),
        sa.Column("fibers", sa.Float(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipes_data_recipe_id"), "recipes_data", ["recipe_id"], unique=False)


def downgrade() -> None:
    # Drop recipes_data table
    op.drop_index(op.f("ix_recipes_data_recipe_id"), table_name="recipes_data")
    op.drop_table("recipes_data")

    # Drop recipes table
    op.drop_index(op.f("ix_recipes_grocy_id"), table_name="recipes")
    op.drop_table("recipes")
