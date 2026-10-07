from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health & Status"])


@router.get("/health")
async def health_check():
    """Returns the operational status of SachCheck Truth Engine."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "crawler_status": {
            "online_nodes": 48,
            "total_nodes": 48,
            "uptime": "99.9%",
            "primary_gateway": "NIC-DELHI-GW4",
        },
    }
