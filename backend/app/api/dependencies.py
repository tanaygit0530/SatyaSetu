from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import Settings, settings
from app.core.logging import logger
from app.core.security import verify_api_key
from app.schemas.core import User
from app.schemas.enums import UserRole
from app.services.auth_service import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    """Dependency returning current application settings."""
    return settings


def get_app_logger():
    """Dependency returning configured structured logger."""
    return logger


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """
    Enforces authentication on protected routes.
    Decodes Bearer JWT token and retrieves verified User profile.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = auth_service.user_repo.get_user(user_id)
    if not user:
        phone = payload.get("phone")
        if phone:
            user = auth_service.user_repo.get_by_phone(phone)
        if not user and (phone or user_id):
            # Token signature was cryptographically verified by our SECRET_KEY;
            # automatically restore user profile across restarts/in-memory cache clears
            user = User(
                user_id=user_id,
                phone_number=phone or "+918591784184",
                role=UserRole.CITIZEN,
            )
            auth_service.user_repo.save_user(user)
        elif not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found.",
            )

    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """
    Optional authentication for public routes (e.g. check submission)
    to automatically associate checks with the authenticated citizen when logged in.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = auth_service.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id:
            return auth_service.user_repo.get_user(user_id)
    except Exception:
        return None
    return None
