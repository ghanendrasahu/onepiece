"""Gateway tests: routing, request-ID propagation, rate limiting, CORS."""

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from worldview_gateway.config import GatewaySettings
from worldview_gateway.main import create_app
from worldview_gateway.ratelimit import MemoryRateLimiter

upstream = FastAPI(title="fake upstream")


@upstream.get("/v1/echo")
async def echo(request: Request):
    return {
        "path": request.url.path,
        "rid": request.headers.get("X-Request-ID"),
    }


@upstream.post("/v1/create")
async def create(request: Request):
    return {"method": request.method, "rid": request.headers.get("X-Request-ID")}


@pytest.fixture
def settings() -> GatewaySettings:
    return GatewaySettings(
        cors_origins=["*"],
        redis_url=None,
        identity_upstream="http://upstream",
        catalog_upstream="http://upstream",
        streaming_upstream="http://upstream",
        ai_guide_upstream="http://upstream",
        rate_limit_rpm=5,
        auth_rate_limit_rpm=5,
    )


@pytest.fixture
def client(settings):
    app = create_app(settings=settings, upstream_app=upstream)
    with TestClient(app) as c:
        yield c


def test_proxy_forward_and_request_id(client):
    r = client.get("/api/identity/v1/echo")
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "/v1/echo"
    assert body["rid"]
    assert r.headers["X-Request-ID"] == body["rid"]


def test_request_id_preserved_when_provided(client):
    r = client.get("/api/catalog/v1/echo", headers={"X-Request-ID": "abc123"})
    assert r.json()["rid"] == "abc123"


def test_post_forwarded(client):
    r = client.post("/api/streaming/v1/create")
    assert r.status_code == 200
    assert r.json()["method"] == "POST"


def test_unknown_service_404(client):
    r = client.get("/api/unknown/v1/foo")
    assert r.status_code == 404


def test_upstream_error_502(client, monkeypatch, settings):
    async def boom(*args, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr("httpx.AsyncClient.request", boom)
    app = create_app(settings=settings, upstream_app=upstream)
    with TestClient(app) as c:
        r = c.get("/api/identity/v1/echo")
        assert r.status_code == 502


def test_rate_limit_exceeded(client):
    for _ in range(5):
        assert client.get("/api/identity/v1/echo").status_code == 200
    r = client.get("/api/identity/v1/echo")
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_healthz_not_rate_limited(settings):
    app = create_app(settings=settings, upstream_app=upstream, rate_limiter=MemoryRateLimiter(1))
    with TestClient(app) as c:
        assert c.get("/healthz").status_code == 200
        assert c.get("/healthz").status_code == 200
        assert c.get("/api/catalog/v1/echo").status_code == 200
        assert c.get("/api/catalog/v1/echo").status_code == 429


def test_auth_rate_limit_stricter(settings):
    app = create_app(
        settings=settings,
        upstream_app=upstream,
        rate_limiter=MemoryRateLimiter(100),
    )
    with TestClient(app) as c:
        app.state.auth_rate_limiter = MemoryRateLimiter(2)
        assert c.get("/api/identity/v1/echo").status_code == 200
        assert c.get("/api/identity/v1/echo").status_code == 200
        assert c.get("/api/identity/v1/echo").status_code == 429
        # Non-identity traffic keeps the looser global limit.
        assert c.get("/api/catalog/v1/echo").status_code == 200


def test_security_headers_present(client):
    r = client.get("/healthz")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
