"""add households, roles, household_users tables

Revision ID: 014
Revises: 013
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "roles" not in existing_tables:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(), nullable=False, unique=True, index=True),
        )

    # Pre-populate roles if empty
    result = conn.execute(sa.text("SELECT COUNT(*) FROM roles"))
    if result.scalar() == 0:
        roles_table = sa.table("roles", sa.column("name", sa.String))
        op.bulk_insert(roles_table, [{"name": "admin"}, {"name": "user"}])

    if "households" not in existing_tables:
        op.create_table(
            "households",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("grocy_url", sa.String(), nullable=True),
            sa.Column("address", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "household_users" not in existing_tables:
        op.create_table(
            "household_users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
            sa.UniqueConstraint("household_id", "user_id", name="uq_household_user"),
        )


def downgrade() -> None:
    op.drop_table("household_users")
    op.drop_table("households")
    op.drop_table("roles")
