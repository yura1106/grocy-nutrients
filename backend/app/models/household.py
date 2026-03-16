from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Boolean, Column, DateTime, Field, SQLModel

from app.core.config import settings
from app.db.custom_types import EncryptedString


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


class HouseholdUser(SQLModel, table=True):
    __tablename__ = "household_users"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="uq_household_user"),)

    id: int | None = Field(default=None, primary_key=True, index=True)
    household_id: int = Field(foreign_key="households.id", nullable=False, index=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    role_id: int = Field(foreign_key="roles.id", nullable=False)
    grocy_api_key: str | None = Field(
        default=None,
        sa_column=Column(EncryptedString(settings.THEMIS_MASTER_KEY), nullable=True),
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
