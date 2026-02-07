"""add consumed_products table

Revision ID: 006
Revises: 005
Create Date: 2026-02-07
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
    # Create consumed_products table
    op.create_table(
        "consumed_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_data_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["product_data_id"], ["products_data.id"]),
    )
    op.create_index(
        op.f("ix_consumed_products_product_data_id"),
        "consumed_products",
        ["product_data_id"],
        unique=False
    )
    op.create_index(
        op.f("ix_consumed_products_date"),
        "consumed_products",
        ["date"],
        unique=False
    )


def downgrade() -> None:
    # Drop consumed_products table
    op.drop_index(op.f("ix_consumed_products_date"), table_name="consumed_products")
    op.drop_index(op.f("ix_consumed_products_product_data_id"), table_name="consumed_products")
    op.drop_table("consumed_products")
