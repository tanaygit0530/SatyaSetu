from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.language import router as language_router
from app.api.routes.claims import router as claims_router
from app.api.v1.sources import router as sources_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(ingest_router)
api_router.include_router(language_router)
api_router.include_router(claims_router)
api_router.include_router(sources_router)
