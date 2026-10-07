from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.verify import router as verify_router
from app.api.v1.sources import router as sources_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(verify_router)
api_v1_router.include_router(sources_router)
