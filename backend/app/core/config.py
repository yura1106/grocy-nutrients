import os
import secrets
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"  # Hardcoded to prevent algorithm substitution attacks
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8888", "http://localhost:5173"]
    CORS_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    CORS_HEADERS: list[str] = ["Authorization", "Content-Type"]

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/grocy_stat"

    @field_validator("DATABASE_URL")
    @classmethod
    def ensure_psycopg3_dialect(cls, v: str) -> str:
        """Rewrite postgresql:// to postgresql+psycopg:// for psycopg3."""
        return v.replace("postgresql://", "postgresql+psycopg://", 1)

    # Debug mode
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Allow grocy_url to point to private/internal IPs (e.g. 192.168.x.x)
    # Set to False if the app is exposed to the public internet
    ALLOW_PRIVATE_GROCY_URL: bool = os.getenv("ALLOW_PRIVATE_GROCY_URL", "True").lower() == "true"

    # Grocy quantity unit IDs (per-instance — find in Master Data → Quantity Units)
    GROCY_GRAM_UNIT_ID: int = int(os.getenv("GROCY_GRAM_UNIT_ID", "0"))  # type: ignore[arg-type]
    GROCY_ML_UNIT_ID: int = int(os.getenv("GROCY_ML_UNIT_ID", "0"))  # type: ignore[arg-type]
    GROCY_PORTION_UNIT_ID: int = int(os.getenv("GROCY_PORTION_UNIT_ID", "0"))  # type: ignore[arg-type]

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Auth cookies
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "False").lower() == "true"
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "strict"
    ACCESS_COOKIE_PATH: str = "/"
    REFRESH_COOKIE_PATH: str = "/api/auth"

    @property
    def access_cookie_name(self) -> str:
        # __Host- prefix requires Secure + Path=/ + no Domain. Used in prod (HTTPS).
        return "__Host-access_token" if self.COOKIE_SECURE else "access_token"

    @property
    def refresh_cookie_name(self) -> str:
        # Refresh cookie uses Path=/api/auth, so it cannot use __Host- prefix.
        return "refresh_token"

    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "15")
    )

    # SMTP email settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Grocy Nutrients")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True").lower() == "true"

    # Frontend URL for password reset links
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Rate limiting
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
