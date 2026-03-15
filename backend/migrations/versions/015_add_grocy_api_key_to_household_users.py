"""add grocy_api_key to household_users

Revision ID: 015
Revises: 014
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("household_users", sa.Column("grocy_api_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("household_users", "grocy_api_key")
