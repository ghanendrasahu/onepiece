"""WorldView API gateway: single entry point for all upstream services.

Responsibilities:
- Route ``/api/<service>/<path>`` to the matching upstream.
- Ensure and propagate ``X-Request-ID`` end to end.
- Apply rate limiting (per client IP + service) and hardening headers.
- Terminate TLS when certificates are configured (dev uses an LB/ingress).
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from worldview.logging import setup_logging
from worldview.request_id import RequestIDMiddleware
from worldview.security import SecurityHeadersMiddleware

from .config import GatewaySettings, get_gateway_settings
from .middleware import RateLimitMiddleware
from .proxy import forward
from .ratelimit import build_rate_limiter

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def create_app(
    settings: GatewaySettings | None = None,
    upstream_app=None,
    rate_limiter=None,
) -> FastAPI:
    """Build the gateway. ``upstream_app``/``rate_limiter`` are test seams."""
    s = settings or get_gateway_settings()
    setup_logging("gateway", s.log_level)
    log = logging.getLogger("gateway")

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        transport = httpx.ASGITransport(app=upstream_app) if upstream_app else None
        app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(15.0), transport=transport)
        app.state.rate_limiter = rate_limiter or build_rate_limiter(s.redis_url, s.rate_limit_rpm)
        app.state.auth_rate_limiter = build_rate_limiter(s.redis_url, s.auth_rate_limit_rpm)
        async with app.state.client:
            log.info("gateway listening", extra={"region": s.region_key})
            yield

    app = FastAPI(
        title="WorldView API Gateway",
        version="0.2.0",
        lifespan=_lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # CORS first (outermost) so preflight short-circuits before rate limiting.
    wildcard = "*" in s.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if wildcard else s.cors_origins,
        allow_credentials=not wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    @app.get("/")
    async def root():
        return {
            "service": "worldview-gateway",
            "services": list(s.upstreams),
            "region": s.region_key,
        }

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.api_route("/api/{service}/{path:path}", methods=_METHODS)
    async def route_proxy(service: str, path: str, request: Request):
        app_state_client = request.app.state.client
        if service not in s.upstreams:
            return JSONResponse(
                status_code=404,
                content={"detail": f"unknown service: {service}"},
                headers={"X-Request-ID": request.headers.get("X-Request-ID", "-")},
            )
        return await forward(request, app_state_client, s.upstreams[service], path)

    log.info("gateway built")
    return app


app = create_app()
