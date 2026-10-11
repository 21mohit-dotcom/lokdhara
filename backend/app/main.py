"""FastAPI application factory. Run with: uv run uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app.config import get_settings
from app.health import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    is_production = settings.env == "production"
    app = FastAPI(
        title="Lokdhara API",
        version="0.1.0",
        # Interactive docs only outside production.
        docs_url=None if is_production else "/api/docs",
        openapi_url=None if is_production else "/api/openapi.json",
        redoc_url=None,
    )
    app.include_router(health_router)
    return app


app = create_app()
