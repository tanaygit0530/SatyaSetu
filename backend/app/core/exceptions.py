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
