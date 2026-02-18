"""add weight_per_serving to recipes_data

Revision ID: 009
Revises: 008
Create Date: 2026-02-17

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
    op.add_column(
        "recipes_data",
        sa.Column("weight_per_serving", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recipes_data", "weight_per_serving")
