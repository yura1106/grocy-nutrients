"""add grocy_stock_expiry table

Revision ID: 034
Revises: 033
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grocy_stock_expiry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("grocy_product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("qu_id_stock", sa.Integer(), nullable=False),
        sa.Column("quantity_unit_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("best_before_date", sa.Date(), nullable=True),
        sa.Column("due_type", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("should_not_be_frozen", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"], ["households.id"], ondelete="CASCADE", onupdate="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "household_id", "grocy_product_id",
            name="uq_grocy_stock_expiry_household_product",
        ),
    )
    op.create_index(
        "ix_grocy_stock_expiry_household_date",
        "grocy_stock_expiry",
        ["household_id", "best_before_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_grocy_stock_expiry_household_date", table_name="grocy_stock_expiry")
    op.drop_table("grocy_stock_expiry")
