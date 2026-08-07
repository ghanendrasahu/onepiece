"""Catalog service application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.cors import add_cors
from worldview.db import init_db
from worldview.health import router as health_router
from worldview.logging import setup_logging
from worldview.request_id import RequestIDMiddleware

from . import models  # noqa: F401 - register tables
from .routers import tours

log = setup_logging("catalog", get_settings().log_level)


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    app = FastAPI(title="WorldView Catalog", version="0.1.0")
    add_cors(app, settings)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_router)
    app.include_router(tours.router)
    return app


app = create_app()
