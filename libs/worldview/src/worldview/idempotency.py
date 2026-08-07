"""Idempotent request handling for money-moving and other unsafe writes.

Usage: include :class:`IdempotencyHeaderMiddleware` in the app, then apply the
``idempotency_required`` dependency to endpoints that must be replay-safe.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class IdempotencyHeaderMiddleware(BaseHTTPMiddleware):
    """Extract the ``Idempotency-Key`` header (if present) into request state.

    Enforcement is opt-in: handlers that move money or create unique resources
    use the :func:`idempotency_required` dependency to require the header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.idempotency_key = request.headers.get("Idempotency-Key")
        return await call_next(request)


def idempotency_key(request: Request) -> str:
    """FastAPI dependency exposing the idempotency key or raising if absent."""
    key = request.state.idempotency_key
    if key is None or not 8 <= len(key) <= 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or invalid Idempotency-Key header",
        )
    return key


_required = Depends(idempotency_key)


def idempotency_required(key: str = _required) -> str:
    """Declare an endpoint as requiring an idempotency key.

    Example: ``async def create_tip(payload: TipIn, key: str = idempotency_required)``
    """
    return key


async def raise_http(status_code_: int, detail: str) -> None:
    raise HTTPException(status_code=status_code_, detail=detail)
