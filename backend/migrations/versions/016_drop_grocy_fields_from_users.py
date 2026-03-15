"""drop grocy fields from users, move last_products_sync_at to household_users

Revision ID: 016
Revises: 015
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "grocy_api_key")
    op.drop_column("users", "grocy_url")
    op.drop_column("users", "last_products_sync_at")
    op.add_column("household_users", sa.Column("last_products_sync_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("household_users", "last_products_sync_at")
    op.add_column("users", sa.Column("last_products_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("grocy_url", sa.String(), nullable=True))
    op.add_column("users", sa.Column("grocy_api_key", sa.String(), nullable=True))
