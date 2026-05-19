"""add note column to meal_plans

Revision ID: 029
Revises: 028
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meal_plans", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_plans", "note")
