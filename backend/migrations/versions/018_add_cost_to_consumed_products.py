"""add cost to consumed_products

Revision ID: 018
Revises: 017
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consumed_products",
        sa.Column("cost", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consumed_products", "cost")
