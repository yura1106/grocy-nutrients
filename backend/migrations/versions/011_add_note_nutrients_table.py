"""add note_nutrients table

Revision ID: 011
Revises: 010
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_nutrients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("proteins", sa.Float(), nullable=True),
        sa.Column("carbohydrates", sa.Float(), nullable=True),
        sa.Column("carbohydrates_of_sugars", sa.Float(), nullable=True),
        sa.Column("fats", sa.Float(), nullable=True),
        sa.Column("fats_saturated", sa.Float(), nullable=True),
        sa.Column("salt", sa.Float(), nullable=True),
        sa.Column("fibers", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("note_nutrients")
