"""Catalog service application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.db import init_db
from worldview.health import router as health_router
from worldview.logging import setup_logging

from . import models  # noqa: F401 - register tables
from .routers import tours

log = setup_logging("catalog", get_settings().log_level)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="WorldView Catalog", version="0.1.0")
    app.include_router(health_router)
    app.include_router(tours.router)
    return app


app = create_app()
