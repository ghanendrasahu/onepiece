"""Identity service application factory."""

from fastapi import FastAPI
from worldview.config import get_settings
from worldview.cors import add_cors
from worldview.db import init_db
from worldview.health import router as health_router
from worldview.idempotency import IdempotencyHeaderMiddleware
from worldview.logging import setup_logging
from worldview.request_id import RequestIDMiddleware

from . import models  # noqa: F401 - register tables with Base.metadata
from .routers import auth, me

log = setup_logging("identity", get_settings().log_level)


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()

    app = FastAPI(
        title="WorldView Identity",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    add_cors(app, settings)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(IdempotencyHeaderMiddleware)
    app.include_router(health_router)
    app.include_router(auth.router)
    app.include_router(me.router)

    log.info("identity service booted", extra={"region": settings.region_key})
    return app


app = create_app()
