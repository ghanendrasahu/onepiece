"""Idempotent request handling for money-moving and other unsafe writes.

The middleware extracts an ``Idempotency-Key`` header into request state; endpoints
that must be replay-safe opt in via :func:`idempotency_required`. When a caller
sends an idempotency key, the middleware additionally stores successful
responses so that a retry replays the recorded response instead of executing
the effect twice.

Storage is pluggable (:class:`IdempotencyStore`). A process-local memory store
is the default; :func:`build_idempotency_store` returns a Redis-backed store
when ``REDIS_URL`` is configured.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any, Protocol

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

_DEFAULT_TTL_SECONDS = 86_400

_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CachedResponse(Protocol):
    status_code: int
    content_type: str
    body_bytes: bytes


class IdempotencyStore(Protocol):
    """Persist and retrieve idempotent responses."""

    async def get(self, key: str) -> CachedResponse | None: ...

    async def set(self, key: str, value: CachedResponse, ttl_seconds: int) -> None: ...


class MemoryIdempotencyStore:
    """Process-local store with expiry. Fine for a single instance / dev."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[float, CachedResponse]] = {}

    async def get(self, key: str) -> CachedResponse | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._items.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: CachedResponse, ttl_seconds: int) -> None:
        self._items[key] = (time.time() + ttl_seconds, value)


class RedisIdempotency:
    """Redis-backed store. Requires a ``redis`` connection; imports lazily."""

    def __init__(self, redis_url: str, prefix: str = "idem:") -> None:
        import redis

        self._redis: Any = redis.from_url(
            redis_url, decode_responses=False, socket_connect_timeout=2
        )
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return self._prefix + key

    async def get(self, key: str) -> CachedResponse | None:
        raw = self._redis.get(self._key(key))
        if raw is None:
            return None
        try:
            doc = json.loads(raw)
            return _DecodedResponse(
                doc["status"],
                doc["content_type"],
                base64.b64decode(doc["body"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    async def set(self, key: str, value: CachedResponse, ttl_seconds: int) -> None:
        doc = json.dumps(
            {
                "status": value.status_code,
                "content_type": value.content_type,
                "body": base64.b64encode(value.body_bytes).decode(),
            }
        )
        self._redis.set(self._key(key), doc, ex=ttl_seconds)


def build_idempotency_store(redis_url: str | None) -> IdempotencyStore:
    """Return a Redis-backed store when a URL is given, else a memory store."""
    if redis_url:
        return RedisIdempotency(redis_url)
    return MemoryIdempotencyStore()


class _DecodedResponse:
    def __init__(self, status_code: int, content_type: str, body: bytes) -> None:
        self.status_code = status_code
        self.content_type = content_type
        self.body_bytes = body


def _cache_key(request: Request, key: str) -> str:
    raw = f"{request.method}|{request.url.path}|{key}"
    return hashlib.sha256(raw.encode()).hexdigest()


class IdempotencyHeaderMiddleware(BaseHTTPMiddleware):
    """Extract ``Idempotency-Key`` into state and replay recorded responses.

    Optional keyword args: ``store`` (default memory store) and ``ttl_seconds``.
    The ``idempotency_required`` dependency still enforces the header on
    specific endpoints; caching replays applies whenever a key is present.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self, app, store: IdempotencyStore | None = None, ttl_seconds: int = _DEFAULT_TTL_SECONDS
    ) -> None:
        super().__init__(app)
        self._store = store or MemoryIdempotencyStore()
        self._ttl = ttl_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        key = request.headers.get("Idempotency-Key")
        request.state.idempotency_key = key
        if key is None or request.method in _IDEMPOTENT_METHODS:
            return await call_next(request)

        cache_key = _cache_key(request, key)
        replay = await self._store.get(cache_key)
        if replay is not None:
            headers = {"Content-Type": replay.content_type, "X-Idempotent-Replay": "true"}
            return Response(
                content=replay.body_bytes, status_code=replay.status_code, headers=headers
            )

        response = await call_next(request)
        body = await _collect_body(response)
        if response.status_code < 400 and body:
            cached = _CachedResponse(response.status_code, _content_type(response), body)
            await self._store.set(cache_key, cached, self._ttl)
        if body is None:
            return response
        # We consumed the streaming body; return a fresh response with it intact.
        return Response(
            content=body, status_code=response.status_code, headers=dict(response.headers)
        )


async def _collect_body(response: Response) -> bytes | None:
    """Read a streaming response body into bytes, or None if not possible."""
    try:
        chunks = [chunk async for chunk in response.body_iterator]
    except (AttributeError, RuntimeError, TypeError):
        return None
    return b"".join(chunks)


def _content_type(response: Response) -> str:
    return response.headers.get("content-type", "application/json")


class _CachedResponse:
    def __init__(self, status_code: int, content_type: str, body_bytes: bytes) -> None:
        self.status_code = status_code
        self.content_type = content_type
        self.body_bytes = body_bytes


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
    """Declare an endpoint as requiring an idempotency key."""
    return key


async def raise_http(status_code_: int, detail: str) -> None:
    raise HTTPException(status_code=status_code_, detail=detail)
