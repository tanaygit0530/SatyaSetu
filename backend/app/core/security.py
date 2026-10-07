import hmac
import hashlib
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Optional API key verifier for protected routes.
    In development mode or when no key is configured, permits requests.
    """
    if settings.ENVIRONMENT == "development":
        return api_key or "dev-key"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required API key.",
        )
    return api_key


def generate_content_hash(content: str) -> str:
    """Computes a SHA-256 fingerprint for citizen messages."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
