import hashlib
import hmac
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

from app.core.security.file_security import (
    FileSecurityValidator,
    file_security_validator,
)
from app.core.security.image_security import (
    ImageSecurityService,
    image_security_service,
)
from app.core.security.pdf_security import (
    PDFSecurityValidator,
    pdf_security_validator,
)
from app.core.security.url_security import (
    URLSecurityValidator,
    url_security_validator,
)
from app.core.security.prompt_security import (
    PromptSecurityService,
    prompt_security_service,
)
from app.core.security.prompt_injection import (
    PromptInjectionDefenseService,
    PromptInjectionScanResult,
    prompt_injection_defense_service,
)
from app.core.security.pii_redactor import (
    PIIRedactorService,
    pii_redactor_service,
)
from app.core.security.phone_hasher import (
    PhoneHasher,
    hash_phone_number,
    phone_hasher,
)
from app.core.security.secrets_validator import (
    SecretsValidator,
    secrets_validator,
)
from app.core.security.rate_limiter import (
    RateLimitExceededException,
    SlidingWindowRateLimiter,
    rate_limiter,
)
from app.core.security.token_budget import (
    DailyTokenBudgetManager,
    token_budget_manager,
)
from app.core.security.audit_logger import (
    SecurityAuditLogger,
    audit_logger,
)
from app.core.security.replay_protector import (
    ReplayProtector,
    replay_protector,
)

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


__all__ = [
    "verify_api_key",
    "generate_content_hash",
    "file_security_validator",
    "FileSecurityValidator",
    "image_security_service",
    "ImageSecurityService",
    "pdf_security_validator",
    "PDFSecurityValidator",
    "url_security_validator",
    "URLSecurityValidator",
    "prompt_security_service",
    "PromptSecurityService",
    "prompt_injection_defense_service",
    "PromptInjectionDefenseService",
    "PromptInjectionScanResult",
    "pii_redactor_service",
    "PIIRedactorService",
    "phone_hasher",
    "PhoneHasher",
    "hash_phone_number",
    "secrets_validator",
    "SecretsValidator",
    "rate_limiter",
    "SlidingWindowRateLimiter",
    "token_budget_manager",
    "DailyTokenBudgetManager",
    "audit_logger",
    "SecurityAuditLogger",
    "replay_protector",
    "ReplayProtector",
]
