from typing import Generator
from fastapi import Depends
from app.core.config import Settings, settings
from app.core.logging import logger
from app.core.security import verify_api_key


def get_settings() -> Settings:
    """Dependency returning current application settings."""
    return settings


def get_app_logger():
    """Dependency returning configured structured logger."""
    return logger
