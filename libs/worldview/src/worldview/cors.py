"""CORS configuration shared by all services (see ``CORS_ORIGINS`` env)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from worldview.config import Settings


def add_cors(app: FastAPI, settings: Settings) -> None:
    """Configure permissive CORS in dev, explicit origins in prod."""
    origins = settings.cors_origins
    wildcard = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if wildcard else origins,
        allow_credentials=not wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
