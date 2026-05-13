"""add meal_plans table

Revision ID: 026
Revises: 025
Create Date: 2026-05-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meal_plans",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "household_id",
            sa.Integer(),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("grocy_meal_plan_id", sa.Integer(), nullable=True),
        sa.Column("grocy_shadow_recipe_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_amount", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("product_qu_id", sa.Integer(), nullable=True),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("recipe_servings", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "household_id", "grocy_meal_plan_id", name="uq_meal_plans_grocy_id"
        ),
    )
    op.create_index(
        "ix_meal_plans_household_day",
        "meal_plans",
        ["household_id", "day"],
    )
    op.create_index(
        "ix_meal_plans_status_pending",
        "meal_plans",
        ["status"],
        postgresql_where=sa.text("status IN ('pending','syncing','failed')"),
    )


def downgrade() -> None:
    op.drop_index("ix_meal_plans_status_pending", table_name="meal_plans")
    op.drop_index("ix_meal_plans_household_day", table_name="meal_plans")
    op.drop_table("meal_plans")
