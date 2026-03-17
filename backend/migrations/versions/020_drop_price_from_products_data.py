"""drop price from products_data

Revision ID: 020
Revises: 019
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("products_data", "price")


def downgrade() -> None:
    op.add_column(
        "products_data",
        sa.Column("price", sa.Float(), nullable=False, server_default="10.0"),
    )
