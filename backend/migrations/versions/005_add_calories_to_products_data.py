"""add calories column to products_data

Revision ID: 005
Revises: 004
Create Date: 2026-02-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products_data",
        sa.Column("calories", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products_data", "calories")
