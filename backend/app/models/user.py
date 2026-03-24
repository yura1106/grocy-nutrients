from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class User(SQLModel, table=True):
    """
    User model - combines ORM model with Pydantic schema

    This serves as the database table definition.
    Separate schemas will be created for API operations.
    """

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    gender: str | None = Field(default=None, nullable=True)
    date_of_birth: date_type | None = Field(default=None, nullable=True, sa_type=Date())
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
