from typing import Any, Dict, Optional


class SachCheckException(Exception):
    """Base class for all SachCheck domain exceptions."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InvalidInputException(SachCheckException):
    """Raised when submitted data fails sanity or boundary validation."""
    def __init__(self, message: str = "Invalid request input.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INVALID_INPUT",
            status_code=400,
            details=details,
        )


class ResourceNotFoundException(SachCheckException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource_name: str, resource_id: str):
        super().__init__(
            message=f"{resource_name} with ID '{resource_id}' was not found.",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource_name, "id": resource_id},
        )


class FirebaseConfigurationError(SachCheckException):
    """Raised when Firebase credentials or project settings are missing or invalid."""
    def __init__(
        self,
        message: str = "Firebase is unavailable: Missing credentials or project ID. Set FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_PATH, or FIREBASE_CREDENTIALS_JSON.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="FIREBASE_UNAVAILABLE",
            status_code=503,
            details=details,
        )


class DatabaseOperationError(SachCheckException):
    """Raised when a Firestore read or write operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )


class ProviderUnavailableException(SachCheckException):
    """Raised when an external AI/OCR/STT provider is unconfigured or unavailable."""
    def __init__(self, provider_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Provider '{provider_name}' is unavailable: {message}",
            code="PROVIDER_UNAVAILABLE",
            status_code=503,
            details=details or {"provider": provider_name},
        )


class CheckNotFoundException(ResourceNotFoundException):
    """Raised when a specific verification check dossier is not found."""
    def __init__(self, check_id: str):
        super().__init__(resource_name="Verification Check", resource_id=check_id)


class PromptInjectionDetectedException(SachCheckException):
    """Raised when adversarial prompt injection patterns are detected in input."""
    def __init__(self, message: str = "Adversarial prompt injection pattern detected in input.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PROMPT_INJECTION_DETECTED",
            status_code=400,
            details=details,
        )


class SecurityViolationException(SachCheckException):
    """Raised when an operation violates security controls (SSRF, malicious file, etc.)."""
    def __init__(self, message: str = "Security policy violation.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SECURITY_VIOLATION",
            status_code=403,
            details=details,
        )


class RateLimitExceededException(SachCheckException):
    """Raised when rate limits for an IP or phone number are exceeded."""
    def __init__(self, message: str = "Rate limit exceeded. Please try again later.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
        )


class TokenBudgetExceededException(SachCheckException):
    """Raised when the daily model/token budget cap has been reached."""
    def __init__(self, message: str = "Daily token budget exceeded.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="TOKEN_BUDGET_EXCEEDED",
            status_code=429,
            details=details,
        )



