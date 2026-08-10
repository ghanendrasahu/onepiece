"""Moderation service application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.cors import add_cors
from worldview.db import init_db
from worldview.health import router as health_router
from worldview.idempotency import IdempotencyHeaderMiddleware, build_idempotency_store
from worldview.logging import setup_logging
from worldview.observability import init_observability, instrument_app
from worldview.request_id import RequestIDMiddleware

from . import models  # noqa: F401 - register tables
from .routers import admin, reports

log = setup_logging("moderation", get_settings().log_level)


def create_app() -> FastAPI:
    settings = get_settings()
    init_observability("moderation", settings)
    init_db()
    app = FastAPI(title="WorldView Moderation", version="0.1.0")
    add_cors(app, settings)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        IdempotencyHeaderMiddleware, store=build_idempotency_store(settings.redis_url)
    )
    instrument_app(app, "moderation")
    app.include_router(health_router)
    app.include_router(reports.router)
    app.include_router(admin.router)
    return app


app = create_app()
