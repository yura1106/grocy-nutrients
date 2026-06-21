import secrets
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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

    # Mount the read-only MCP server at /mcp. Each API key binds to its own
    # household (chosen at mint time), so there is no server-level household.
    MCP_ENABLED: bool = False
    MCP_ALLOWED_HOSTS: list[str] = []

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
    # Per-account brute-force limit (keyed by username, independent of IP) so a
    # single attacker rotating IPs cannot grind one account.
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS_PER_ACCOUNT: int = 10

    # Generic per-endpoint throttle (forgot-password, reset, deletion, refresh)
    SENSITIVE_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    SENSITIVE_RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # Trust X-Forwarded-For only when the immediate peer is a known proxy.
    # Behind nginx/Traefik in Docker this is the proxy's address/CIDR. Empty =
    # trust nothing (use the raw socket peer), which is the safe default if the
    # app is exposed directly.
    TRUSTED_PROXY_IPS: list[str] = ["172.16.0.0/12", "10.0.0.0/8", "127.0.0.1/32"]

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_ignore_empty=True,
    )

    @model_validator(mode="after")
    def _enforce_secure_cookies_in_prod(self) -> "Settings":
        """Refuse to boot a non-debug deployment that would send auth cookies
        over plaintext HTTP. In production COOKIE_SECURE must be True so the
        cookies get the Secure flag and the __Host- prefix."""
        if not self.DEBUG and not self.COOKIE_SECURE:
            raise ValueError(
                "COOKIE_SECURE must be True when DEBUG is False "
                "(auth cookies would otherwise travel over plaintext HTTP)."
            )
        return self


settings = Settings()
