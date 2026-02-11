"""add daily_nutrition table

Revision ID: 006
Revises: 005
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_nutrition",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("calories", sa.Float(), nullable=False, server_default="0"),
        sa.Column("proteins", sa.Float(), nullable=False, server_default="0"),
        sa.Column("carbohydrates", sa.Float(), nullable=False, server_default="0"),
        sa.Column("carbohydrates_of_sugars", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fats", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fats_saturated", sa.Float(), nullable=False, server_default="0"),
        sa.Column("salt", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fibers", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )
    op.create_index(op.f("ix_daily_nutrition_date"), "daily_nutrition", ["date"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_nutrition_date"), table_name="daily_nutrition")
    op.drop_table("daily_nutrition")
