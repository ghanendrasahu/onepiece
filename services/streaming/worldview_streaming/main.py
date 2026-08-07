"""Streaming service application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.cors import add_cors
from worldview.db import init_db
from worldview.health import router as health_router
from worldview.idempotency import IdempotencyHeaderMiddleware
from worldview.logging import setup_logging
from worldview.request_id import RequestIDMiddleware

from . import models  # noqa: F401 - register tables
from .routers import streams

log = setup_logging("streaming", get_settings().log_level)


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    app = FastAPI(title="WorldView Streaming", version="0.1.0")
    add_cors(app, settings)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(IdempotencyHeaderMiddleware)
    app.include_router(health_router)
    app.include_router(streams.router)
    return app


app = create_app()
