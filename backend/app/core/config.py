import os
import secrets
from typing import List, Union

from pydantic import AnyHttpUrl, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8888", "http://localhost:5173"]
    
    # Database
    DATABASE_URL: str = str(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/grocy_stat"))
    
    # Debug mode
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 