"""add household_grocy_mapping table

Revision ID: 025
Revises: 024
Create Date: 2026-05-09
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Note: env values are read at upgrade time. Running downgrade then upgrade in a
# different env loses the original values — they fall back to NULL and admins
# refill via the UI.
_KEY_ENV: list[tuple[str, str]] = [
    ("gram_unit_id", "GROCY_GRAM_UNIT_ID"),
    ("ml_unit_id", "GROCY_ML_UNIT_ID"),
    ("portion_unit_id", "GROCY_PORTION_UNIT_ID"),
]


def upgrade() -> None:
    op.create_table(
        "household_grocy_mapping",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "household_id",
            sa.Integer(),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column(
            "updated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "household_id", "key", name="uq_household_grocy_mapping_household_key"
        ),
        sa.CheckConstraint(
            "key IN ('gram_unit_id', 'ml_unit_id', 'portion_unit_id')",
            name="ck_household_grocy_mapping_key",
        ),
    )

    # Seed one row per (household, key). Values pulled from .env at upgrade time;
    # empty/missing → NULL.
    conn = op.get_bind()
    households = conn.execute(sa.text("SELECT id FROM households")).fetchall()
    for key, env_var in _KEY_ENV:
        raw = os.getenv(env_var) or None
        for (household_id,) in households:
            conn.execute(
                sa.text(
                    "INSERT INTO household_grocy_mapping (household_id, key, value) "
                    "VALUES (:hid, :key, :value)"
                ),
                {"hid": household_id, "key": key, "value": raw},
            )


def downgrade() -> None:
    op.drop_table("household_grocy_mapping")
