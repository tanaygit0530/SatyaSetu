from typing import List, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Foundation Settings
    SERVICE_NAME: str = "sachcheck-backend"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server & Networking
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # Security
    SECRET_KEY: str = "sachcheck-foundation-secret-key-change-in-production"
    API_KEY_HEADER_NAME: str = "X-API-Key"


settings = Settings()
