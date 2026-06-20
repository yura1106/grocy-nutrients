"""bind user_api_keys to a household; GIN trigram index on recipes.name

Overturns ADR-0004's "household from MCP server config": the household is now
chosen when the key is minted (per-membership, from the Households UI). Existing
keys get household_id=NULL and MCP auth rejects NULL, so they must be re-minted.

Revision ID: 033
Revises: 032
Create Date: 2026-06-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_api_keys",
        sa.Column("household_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_api_keys_household_id",
        "user_api_keys",
        "households",
        ["household_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_user_api_keys_household_id"),
        "user_api_keys",
        ["household_id"],
        unique=False,
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recipes_name_trgm "
        "ON recipes USING gin (name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recipes_name_trgm")
    # Leave pg_trgm installed — other objects (032's products index) depend on it.
    op.drop_index(op.f("ix_user_api_keys_household_id"), table_name="user_api_keys")
    op.drop_constraint(
        "fk_user_api_keys_household_id", "user_api_keys", type_="foreignkey"
    )
    op.drop_column("user_api_keys", "household_id")
