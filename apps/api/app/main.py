import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.middleware.correlation import CorrelationIdMiddleware, get_correlation_id
from app.middleware.request_metrics import RequestMetricsMiddleware
from app.observability.logging import configure_logging
from app.version import API_VERSION

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("app")


def create_app() -> FastAPI:
    docs_url = None if settings.is_production else "/docs"
    openapi_url = None if settings.is_production else "/openapi.json"
    app = FastAPI(
        title=settings.app_name,
        version=API_VERSION,
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
    )

    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            extra={"error_code": exc.error_code, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "correlation_id": get_correlation_id(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "correlation_id": get_correlation_id(),
            },
        )

    app.include_router(api_router)
    return app


app = create_app()
