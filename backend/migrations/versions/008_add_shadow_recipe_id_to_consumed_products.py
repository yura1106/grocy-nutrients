"""add recipe_grocy_id_shadow to consumed_products

Revision ID: 008
Revises: 007
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consumed_products",
        sa.Column("recipe_grocy_id_shadow", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consumed_products", "recipe_grocy_id_shadow")
