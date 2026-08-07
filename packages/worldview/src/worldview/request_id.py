"""Request-ID propagation: generate when absent, correlate logs, echo back.

Every service includes :class:`RequestIDMiddleware`; the gateway ensures a
value exists and the services forward it, giving end-to-end trace correlation
via the ``X-Request-ID`` header and the ``request_id`` field in JSON logs.
"""

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def current_request_id() -> str:
    """Return the request ID bound to this async context (or ``-`` outside a request)."""
    return _request_id.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Set ``X-Request-ID`` (generating one if absent), bind it for loggers, echo it back."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = _request_id.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestIDFilter(logging.Filter):
    """Attach the current request ID to every log record as ``request_id``."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        return True
