"""add grocy_url to users

Revision ID: 012
Revises: 011
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("grocy_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "grocy_url")
