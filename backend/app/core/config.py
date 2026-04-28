import secrets
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"

    # Security
    APP_SECRET_KEY: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
    )
    JWT_ALGORITHM: str = "HS256"  # Hardcoded to prevent algorithm substitution attacks
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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
    DEBUG: bool = False

    REDIS_URL: str = "redis://redis:6379/0"

    # Allow grocy_url to point to private/internal IPs (e.g. 192.168.x.x)
    # Set to False if the app is exposed to the public internet
    ALLOW_PRIVATE_GROCY_URL: bool = True

    # Grocy quantity unit IDs (per-instance — find in Master Data → Quantity Units)
    GROCY_GRAM_UNIT_ID: int = 0
    GROCY_ML_UNIT_ID: int = 0
    GROCY_PORTION_UNIT_ID: int = 0

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Auth cookies
    COOKIE_SECURE: bool = False
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
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # SMTP email settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Grocy Nutrients"
    SMTP_USE_TLS: bool = True

    # Frontend URL for password reset links
    FRONTEND_URL: str = "http://localhost:5173"

    # Rate limiting
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_ignore_empty=True,
    )


settings = Settings()
