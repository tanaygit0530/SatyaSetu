from typing import List, Literal, Optional, Union
import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Foundation Settings
    SERVICE_NAME: str = "satyasetu-backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server & Networking
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000", "*"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

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
    SARVAM_TTS_API_URL: str = "https://api.sarvam.ai/text-to-speech"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_TTS_SPEAKER: str = "shubh"
    TTS_AUDIO_DIR: str = "/tmp/sachcheck_audio"

    # PDF Ingestion Configuration
    MAX_PDF_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    MAX_PDF_PAGE_COUNT: int = 100  # Page limit
    PDF_PAGE_RANKING_LIMIT: int = 10  # Max ranked claim-bearing pages returned
    PDF_MIN_TEXT_CHARS: int = 40  # Meaningful text threshold per page

    # URL Ingestion & SSRF Protection
    URL_FETCH_TIMEOUT_SECONDS: float = 10.0
    URL_MAX_RESPONSE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    URL_MAX_REDIRECTS: int = 5

    # LLM Structured Extraction Configuration
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: Optional[str] = None
    DEMO_MODE: bool = False

    # Evidence Retrieval & Search Providers Configuration
    GOOGLE_FACT_CHECK_API_KEY: Optional[str] = None
    GOOGLE_FACT_CHECK_API_URL: str = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    TAVILY_API_KEY: Optional[str] = None
    TAVILY_API_URL: str = "https://api.tavily.com/search"
    SEARCH_PROVIDER: str = "tavily"
    MAX_RETRIEVAL_CANDIDATES: int = 10
    MAX_EVIDENCE_ITEMS: int = 5

    # Twilio & WhatsApp Integration Configuration
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_VERIFY_SERVICE_SID: Optional[str] = "VA58dc2a328182898aca39dec02c93c37a"
    TWILIO_WHATSAPP_NUMBER: Optional[str] = "whatsapp:+14155238886"
    TWILIO_VALIDATE_SIGNATURE: bool = True
    TWILIO_MEDIA_DOWNLOAD_TIMEOUT_SECONDS: float = 15.0
    TWILIO_ASYNC_DISPATCH: bool = True
    BASE_PUBLIC_URL: str = "https://sachcheck.in"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = 7

    # Security Controls Configuration
    SECURITY_PHONE_SALT: str = "sachcheck_salt_v1"
    RATE_LIMIT_PER_NUMBER_PER_MINUTE: int = 10
    RATE_LIMIT_PER_IP_PER_MINUTE: int = 30
    DAILY_TOKEN_BUDGET: int = 1000000
    REPLAY_WINDOW_SECONDS: int = 300


settings = Settings()
