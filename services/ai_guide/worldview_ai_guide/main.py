"""AI guide application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.cors import add_cors
from worldview.health import router as health_router
from worldview.logging import setup_logging
from worldview.request_id import RequestIDMiddleware

from .routers import guide

log = setup_logging("ai_guide", get_settings().log_level)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="WorldView AI Guide", version="0.1.0")
    add_cors(app, settings)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_router)
    app.include_router(guide.router)
    return app


app = create_app()
