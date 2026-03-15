import os
import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8888", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = str(
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/grocy_stat")
    )

    # Debug mode
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    THEMIS_MASTER_KEY: str = os.getenv("THEMIS_MASTER_KEY", "")

    # Allow grocy_url to point to private/internal IPs (e.g. 192.168.x.x)
    # Set to False if the app is exposed to the public internet
    ALLOW_PRIVATE_GROCY_URL: bool = os.getenv("ALLOW_PRIVATE_GROCY_URL", "True").lower() == "true"

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

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
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Grocy Reports")
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
