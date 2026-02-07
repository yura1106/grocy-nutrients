"""add quantity to consumed_products

Revision ID: 007
Revises: 006
Create Date: 2026-02-07
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
    # Add quantity column to consumed_products table
    op.add_column(
        "consumed_products",
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1.0")
    )
    # Remove server default after adding the column
    op.alter_column("consumed_products", "quantity", server_default=None)


def downgrade() -> None:
    # Drop quantity column from consumed_products table
    op.drop_column("consumed_products", "quantity")
