"""add calorie_deficit_percent to user_health_profiles

Revision ID: 023
Revises: 022
Create Date: 2026-03-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_health_profiles",
        sa.Column("calorie_deficit_percent", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_health_profiles", "calorie_deficit_percent")
