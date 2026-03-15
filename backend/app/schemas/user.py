import ipaddress
import re
import socket
from datetime import datetime
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


def _validate_password_strength(password: str) -> str:
    """OWASP password strength: min 8 chars, upper, lower, digit, special."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must contain at least one special character")
    return password


# Shared properties
class UserBase(SQLModel):
    email: EmailStr | None = None
    username: str | None = None


# Properties to receive via API on creation
class UserCreate(SQLModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: str | None = Field(default=None, min_length=8)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_password_strength(v)


# Properties to return via API
class UserRead(UserBase):
    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# Properties for user login
class UserLogin(SQLModel):
    username: str
    password: str


# Token schema (not model-related, keep as Pydantic BaseModel)
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


# Token payload
class TokenPayload(BaseModel):
    sub: int | None = None
    purpose: str | None = None


# Password reset
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# Refresh token
class RefreshTokenRequest(BaseModel):
    refresh_token: str
