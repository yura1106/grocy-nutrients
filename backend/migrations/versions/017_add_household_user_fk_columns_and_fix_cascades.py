"""add household_id/user_id FK columns to data tables, fix CASCADE on all FKs

Revision ID: 017
Revises: 016
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # === 1. Add household_id FK to data tables ===
    household_tables = [
        "products", "recipes", "consumed_products",
        "meal_plan_consumptions", "note_nutrients", "daily_nutrition",
    ]
    for table in household_tables:
        columns = [c["name"] for c in inspector.get_columns(table)]
        if "household_id" not in columns:
            op.add_column(
                table,
                sa.Column(
                    "household_id",
                    sa.Integer(),
                    sa.ForeignKey("households.id", ondelete="CASCADE", onupdate="CASCADE"),
                    nullable=True,
                    index=True,
                ),
            )

    # === 2. Add user_id FK to data tables ===
    user_tables = [
        "consumed_products", "recipes_data",
        "meal_plan_consumptions", "note_nutrients", "daily_nutrition",
    ]
    for table in user_tables:
        columns = [c["name"] for c in inspector.get_columns(table)]
        if "user_id" not in columns:
            op.add_column(
                table,
                sa.Column(
                    "user_id",
                    sa.Integer(),
                    sa.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
                    nullable=True,
                    index=True,
                ),
            )

    # === 3. Change unique constraints: grocy_id → (grocy_id, household_id) ===

    # Products: drop old unique index
    products_indexes = inspector.get_indexes("products")
    for idx in products_indexes:
        if idx["unique"] and idx["column_names"] == ["grocy_id"]:
            op.drop_index(idx["name"], table_name="products")
            break

    # Recipes: drop old unique index and/or unique constraint
    recipes_indexes = inspector.get_indexes("recipes")
    for idx in recipes_indexes:
        if idx["unique"] and idx["column_names"] == ["grocy_id"]:
            op.drop_index(idx["name"], table_name="recipes")
            break

    recipes_constraints = inspector.get_unique_constraints("recipes")
    for uc in recipes_constraints:
        if uc["column_names"] == ["grocy_id"]:
            op.drop_constraint(uc["name"], "recipes", type_="unique")
            break

    op.create_unique_constraint(
        "uq_products_grocy_id_household", "products", ["grocy_id", "household_id"],
    )
    op.create_unique_constraint(
        "uq_recipes_grocy_id_household", "recipes", ["grocy_id", "household_id"],
    )

    # === 4. Add soft delete to household_users ===
    hu_columns = [c["name"] for c in inspector.get_columns("household_users")]
    if "is_active" not in hu_columns:
        op.add_column(
            "household_users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
    if "deactivated_at" not in hu_columns:
        op.add_column(
            "household_users",
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # === 5. Fix CASCADE on household_users FKs ===
    op.drop_constraint("household_users_household_id_fkey", "household_users", type_="foreignkey")
    op.create_foreign_key(
        "household_users_household_id_fkey", "household_users", "households",
        ["household_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE",
    )

    op.drop_constraint("household_users_user_id_fkey", "household_users", type_="foreignkey")
    op.create_foreign_key(
        "household_users_user_id_fkey", "household_users", "users",
        ["user_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE",
    )

    op.drop_constraint("household_users_role_id_fkey", "household_users", type_="foreignkey")
    op.create_foreign_key(
        "household_users_role_id_fkey", "household_users", "roles",
        ["role_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE",
    )

    # === 6. Fix CASCADE on pre-existing FKs ===
    op.drop_constraint("products_data_product_id_fkey", "products_data", type_="foreignkey")
    op.create_foreign_key(
        "products_data_product_id_fkey", "products_data", "products",
        ["product_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE",
    )

    op.drop_constraint("consumed_products_product_data_id_fkey", "consumed_products", type_="foreignkey")
    op.create_foreign_key(
        "consumed_products_product_data_id_fkey", "consumed_products", "products_data",
        ["product_data_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE",
    )


def downgrade() -> None:
    # Restore original FKs without CASCADE
    op.drop_constraint("consumed_products_product_data_id_fkey", "consumed_products", type_="foreignkey")
    op.create_foreign_key(
        "consumed_products_product_data_id_fkey", "consumed_products", "products_data",
        ["product_data_id"], ["id"],
    )

    op.drop_constraint("products_data_product_id_fkey", "products_data", type_="foreignkey")
    op.create_foreign_key(
        "products_data_product_id_fkey", "products_data", "products",
        ["product_id"], ["id"],
    )

    # Restore household_users FKs without CASCADE
    op.drop_constraint("household_users_role_id_fkey", "household_users", type_="foreignkey")
    op.create_foreign_key(
        "household_users_role_id_fkey", "household_users", "roles",
        ["role_id"], ["id"],
    )

    op.drop_constraint("household_users_user_id_fkey", "household_users", type_="foreignkey")
    op.create_foreign_key(
        "household_users_user_id_fkey", "household_users", "users",
        ["user_id"], ["id"],
    )

    op.drop_constraint("household_users_household_id_fkey", "household_users", type_="foreignkey")
    op.create_foreign_key(
        "household_users_household_id_fkey", "household_users", "households",
        ["household_id"], ["id"],
    )

    # Drop soft delete columns
    op.drop_column("household_users", "deactivated_at")
    op.drop_column("household_users", "is_active")

    # Restore global unique constraints
    op.drop_constraint("uq_products_grocy_id_household", "products", type_="unique")
    op.drop_constraint("uq_recipes_grocy_id_household", "recipes", type_="unique")
    op.create_index("ix_products_grocy_id", "products", ["grocy_id"], unique=True)
    op.create_index("ix_recipes_grocy_id", "recipes", ["grocy_id"], unique=True)

    # Drop user_id columns
    for table in ["daily_nutrition", "note_nutrients", "meal_plan_consumptions", "recipes_data", "consumed_products"]:
        op.drop_column(table, "user_id")

    # Drop household_id columns
    for table in ["daily_nutrition", "note_nutrients", "meal_plan_consumptions", "consumed_products", "recipes", "products"]:
        op.drop_column(table, "household_id")
