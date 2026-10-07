from typing import List, Literal, Optional
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

    # Firebase & Cloud Firestore Persistence
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    FIRESTORE_DATABASE_ID: Optional[str] = "(default)"
    FIRESTORE_EMULATOR_HOST: Optional[str] = None

    # Ingestion Constraints
    MAX_TEXT_INPUT_LENGTH: int = 15000
    MAX_IMAGE_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_MIME_TYPES: List[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png"]
    )

    # OCR Engine Configuration
    OCR_CONFIDENCE_THRESHOLD: float = 0.70  # Below 0.70 triggers fallback or needs_confirmation
    TESSERACT_CMD: Optional[str] = None
    GOOGLE_VISION_API_KEY: Optional[str] = None

    # Voice Ingestion & STT Configuration
    MAX_VOICE_DURATION_SECONDS: float = 60.0  # 60s max for MVP
    MAX_VOICE_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    STT_CONFIDENCE_THRESHOLD: float = 0.65  # Below 0.65 triggers needs_confirmation
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_API_URL: str = "https://api.sarvam.ai/speech-to-text"


settings = Settings()
