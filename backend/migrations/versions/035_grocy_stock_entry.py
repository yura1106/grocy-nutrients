"""replace grocy_stock_expiry with per-entry grocy_stock_entry

Revision ID: 035
Revises: 034
Create Date: 2026-06-22

The stock cache is disposable (repopulated by the next sync), so the old
aggregated-per-product table is dropped and a per-entry table created in its
place. Each row is one Grocy stock entry, keyed by Grocy's stable stock_id,
allowing several entries per product with different best-before dates.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_grocy_stock_expiry_household_date", table_name="grocy_stock_expiry")
    op.drop_table("grocy_stock_expiry")

    op.create_table(
        "grocy_stock_entry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("grocy_stock_id", sa.Text(), nullable=False),
        sa.Column("grocy_product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("qu_id_stock", sa.Integer(), nullable=False),
        sa.Column("quantity_unit_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("best_before_date", sa.Date(), nullable=True),
        sa.Column("purchased_date", sa.Date(), nullable=True),
        sa.Column("opened", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("due_type", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("should_not_be_frozen", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"], ["households.id"], ondelete="CASCADE", onupdate="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "household_id", "grocy_stock_id",
            name="uq_grocy_stock_entry_household_stock",
        ),
    )
    op.create_index(
        "ix_grocy_stock_entry_household_date",
        "grocy_stock_entry",
        ["household_id", "best_before_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_grocy_stock_entry_household_date", table_name="grocy_stock_entry")
    op.drop_table("grocy_stock_entry")

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
