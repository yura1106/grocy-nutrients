"""add health parameters to users and create user_health_profiles table

Revision ID: 021
Revises: 020
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gender", sa.String(), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))

    op.create_table(
        "user_health_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("activity_level", sa.String(), nullable=True),
        sa.Column("goal", sa.String(), nullable=True),
        sa.Column("daily_calories", sa.Float(), nullable=True),
        sa.Column("daily_proteins", sa.Float(), nullable=True),
        sa.Column("daily_fats", sa.Float(), nullable=True),
        sa.Column("daily_fats_saturated", sa.Float(), nullable=True),
        sa.Column("daily_carbohydrates", sa.Float(), nullable=True),
        sa.Column("daily_carbohydrates_of_sugars", sa.Float(), nullable=True),
        sa.Column("daily_salt", sa.Float(), nullable=True),
        sa.Column("daily_fibers", sa.Float(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_health_profiles")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "gender")
