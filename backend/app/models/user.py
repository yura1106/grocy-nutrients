from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, DateTime
from sqlalchemy.sql import func
from app.db.custom_types import EncryptedString
from app.core.config import settings


class User(SQLModel, table=True):
    """
    User model - combines ORM model with Pydantic schema

    This serves as the database table definition.
    Separate schemas will be created for API operations.
    """
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    grocy_api_key: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedString(settings.THEMIS_MASTER_KEY), nullable=True)
    )
    grocy_url: Optional[str] = Field(default=None, nullable=True)
    last_products_sync_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
