from datetime import datetime
from typing import Optional

import ipaddress
import socket
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlmodel import SQLModel

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _validate_grocy_url(url: str) -> str:
    from app.core.config import settings

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("grocy_url must use http or https scheme")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("grocy_url must have a valid hostname")
    if not settings.ALLOW_PRIVATE_GROCY_URL:
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for _, _, _, _, sockaddr in resolved:
                ip = ipaddress.ip_address(sockaddr[0])
                for net in BLOCKED_NETWORKS:
                    if ip in net:
                        raise ValueError("grocy_url must not point to a private/internal address")
        except socket.gaierror:
            raise ValueError("grocy_url hostname could not be resolved")
    return url


# Shared properties
class UserBase(SQLModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
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

    @field_validator("grocy_url")
    @classmethod
    def validate_grocy_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return _validate_grocy_url(v)


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = Field(default=None, min_length=8)

    @field_validator("grocy_url")
    @classmethod
    def validate_grocy_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return _validate_grocy_url(v)


# Properties to return via API
class UserRead(UserBase):
    id: int
    is_active: bool = True
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
