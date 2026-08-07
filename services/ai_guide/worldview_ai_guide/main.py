"""AI guide application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.health import router as health_router
from worldview.logging import setup_logging

from .routers import guide

log = setup_logging("ai_guide", get_settings().log_level)


def create_app() -> FastAPI:
    app = FastAPI(title="WorldView AI Guide", version="0.1.0")
    app.include_router(health_router)
    app.include_router(guide.router)
    return app


app = create_app()
