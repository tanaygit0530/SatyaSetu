from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import SachCheckException
from app.core.logging import logger
from app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s...", settings.SERVICE_NAME, settings.VERSION)
    logger.info("Environment: %s | Debug: %s", settings.ENVIRONMENT, settings.DEBUG)
    yield
    logger.info("Shutting down %s...", settings.SERVICE_NAME)


def create_application() -> FastAPI:
    """Application factory for SachCheck backend foundation."""
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.VERSION,
        description="Backend foundation for SachCheck claim verification platform.",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handling
    @app.exception_handler(SachCheckException)
    async def sachcheck_exception_handler(request: Request, exc: SachCheckException):
        logger.warning("Domain exception: [%s] %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled server exception: %s", str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                }
            },
        )

    # Mount API version prefix: /api/v1
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Also mount /checks at root to support /checks alongside /api/v1/checks
    from app.api.routes.checks import router as checks_router
    app.include_router(checks_router, include_in_schema=False)

    return app


app = create_application()
