from fastapi import APIRouter, Depends
from app.core.config import Settings
from app.api.dependencies import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """
    Health check endpoint returning service identification and status.
    """
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
    )
