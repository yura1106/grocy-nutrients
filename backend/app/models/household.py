from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Boolean, Column, DateTime, Field, Relationship, SQLModel


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: int | None = Field(default=None, primary_key=True, index=True)
    name: str = Field(unique=True, index=True, nullable=False)


class Household(SQLModel, table=True):
    __tablename__ = "households"

    id: int | None = Field(default=None, primary_key=True, index=True)
    name: str = Field(nullable=False)
    grocy_url: str | None = Field(default=None, nullable=True)
    address: str | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )

    # Cascade-only relationship — read paths use explicit queries.
    grocy_mapping: list["HouseholdGrocyMapping"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class HouseholdUser(SQLModel, table=True):
    __tablename__ = "household_users"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="uq_household_user"),)

    id: int | None = Field(default=None, primary_key=True, index=True)
    household_id: int = Field(foreign_key="households.id", nullable=False, index=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    role_id: int = Field(foreign_key="roles.id", nullable=False)
    grocy_api_key: str | None = Field(
        default=None,
        sa_column=Column(String(), nullable=True),
    )
    last_products_sync_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean(), nullable=False, server_default="true"),
    )
    deactivated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class HouseholdGrocyMapping(SQLModel, table=True):
    __tablename__ = "household_grocy_mapping"
    __table_args__ = (
        UniqueConstraint("household_id", "key", name="uq_household_grocy_mapping_household_key"),
        CheckConstraint(
            "key IN ('gram_unit_id', 'ml_unit_id', 'portion_unit_id')",
            name="ck_household_grocy_mapping_key",
        ),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    household_id: int = Field(
        sa_column=Column(
            ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    key: str = Field(sa_column=Column(String(), nullable=False))
    value: str | None = Field(
        default=None,
        sa_column=Column(String(), nullable=True),
    )
    updated_by_user_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )
