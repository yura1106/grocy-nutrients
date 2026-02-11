"""add cascade to recipes_data foreign key

Revision ID: 011
Revises: 010
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing foreign key constraint
    op.drop_constraint(
        "recipes_data_recipe_id_fkey",
        "recipes_data",
        type_="foreignkey"
    )

    # Add foreign key constraint with CASCADE
    op.create_foreign_key(
        "recipes_data_recipe_id_fkey",
        "recipes_data",
        "recipes",
        ["recipe_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # Drop CASCADE foreign key constraint
    op.drop_constraint(
        "recipes_data_recipe_id_fkey",
        "recipes_data",
        type_="foreignkey"
    )

    # Restore original foreign key constraint without CASCADE
    op.create_foreign_key(
        "recipes_data_recipe_id_fkey",
        "recipes_data",
        "recipes",
        ["recipe_id"],
        ["id"]
    )
