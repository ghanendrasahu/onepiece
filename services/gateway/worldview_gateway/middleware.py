"""Middleware for the gateway app."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

_EXEMPT_PATHS = {"/", "/healthz", "/docs", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce the gateway rate limit per client IP + upstream service."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        limiter = request.app.state.rate_limiter
        client_ip = request.client.host if request.client else "unknown"
        parts = path.strip("/").split("/")
        service = parts[1] if len(parts) > 1 else "root"
        key = f"{client_ip}:{service}"

        allowed, retry_after = await limiter.allow(key)
        if not allowed:
            return Response(
                status_code=429,
                content=b'{"detail": "rate limit exceeded"}',
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-Request-ID": _request_id_from(request),
                },
            )
        return await call_next(request)


def _request_id_from(request) -> str:
    return request.headers.get("X-Request-ID", "-")
