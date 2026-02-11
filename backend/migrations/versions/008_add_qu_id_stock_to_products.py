"""add qu_id_stock to products

Revision ID: 008
Revises: 007
Create Date: 2026-02-09
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
    # Add qu_id_stock column to products table
    # nullable=True for backward compatibility with existing products
    op.add_column(
        "products",
        sa.Column("qu_id_stock", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    # Drop qu_id_stock column from products table
    op.drop_column("products", "qu_id_stock")
