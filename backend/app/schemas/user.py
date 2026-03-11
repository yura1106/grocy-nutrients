from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlmodel import SQLModel


# Shared properties
class UserBase(SQLModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = True
    grocy_api_key: Optional[str] = None
    grocy_url: Optional[str] = None


# Properties to receive via API on creation
class UserCreate(SQLModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    grocy_api_key: Optional[str] = None
    grocy_url: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = Field(default=None, min_length=8)


# Properties to return via API
class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_products_sync_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Properties for user login
class UserLogin(SQLModel):
    username: str
    password: str


# Token schema (not model-related, keep as Pydantic BaseModel)
class Token(BaseModel):
    access_token: str
    token_type: str


# Token payload
class TokenPayload(BaseModel):
    sub: Optional[int] = None
