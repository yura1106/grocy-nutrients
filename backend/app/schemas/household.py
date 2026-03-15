from datetime import datetime

from pydantic import field_validator
from sqlmodel import SQLModel


class HouseholdCreate(SQLModel):
    name: str
    grocy_url: str | None = None
    address: str | None = None

    @field_validator("grocy_url")
    @classmethod
    def validate_grocy_url(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        from app.schemas.user import _validate_grocy_url

        return _validate_grocy_url(v)


class HouseholdUpdate(SQLModel):
    name: str | None = None
    grocy_url: str | None = None
    address: str | None = None

    @field_validator("grocy_url")
    @classmethod
    def validate_grocy_url(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        from app.schemas.user import _validate_grocy_url

        return _validate_grocy_url(v)


class HouseholdMemberRead(SQLModel):
    user_id: int
    username: str
    email: str
    role_name: str
    has_grocy_key: bool = False
    last_products_sync_at: datetime | None = None

    model_config = {"from_attributes": True}


class HouseholdRead(SQLModel):
    id: int
    name: str
    grocy_url: str | None = None
    address: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class HouseholdWithRole(HouseholdRead):
    role_name: str


class HouseholdDetail(HouseholdRead):
    role_name: str
    members: list[HouseholdMemberRead] = []


class SetGrocyKeyRequest(SQLModel):
    grocy_api_key: str


class AddUserRequest(SQLModel):
    user_id: int
    role_name: str = "user"


class AddUserResponse(SQLModel):
    household_id: int
    user_id: int
    role_name: str


class UserSearchResult(SQLModel):
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}
