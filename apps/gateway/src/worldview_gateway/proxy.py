"""Reverse proxying from the gateway to upstream WorldView services."""

import logging

import httpx
from fastapi import Request
from starlette.responses import Response
from worldview.request_id import current_request_id

log = logging.getLogger("gateway.proxy")

# Headers we never forward (hop-by-hop + those httpx manages itself).
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "accept-encoding",
}


def _forwardable_headers(request: Request, upstream_base: str) -> dict[str, str]:
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
    headers.setdefault("X-Request-ID", current_request_id())
    headers["Host"] = upstream_base.split("://", 1)[1]
    return headers


async def forward(
    request: Request,
    client: httpx.AsyncClient,
    upstream_base: str,
    path: str,
) -> Response:
    """Proxy ``request`` (with the service prefix stripped) to ``upstream_base``."""
    url = f"{upstream_base.rstrip('/')}/{path}"
    headers = _forwardable_headers(request, upstream_base)
    try:
        upstream = await client.request(
            request.method,
            url,
            params=request.query_params,
            headers=headers,
            content=await request.body() or None,
        )
    except httpx.HTTPError as exc:
        log.warning("upstream error %s: %s", upstream_base, exc)
        return Response(
            status_code=502,
            content=b'{"detail": "upstream service unavailable"}',
            headers={"Content-Type": "application/json", "X-Request-ID": current_request_id()},
        )

    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP}
    response_headers["X-Request-ID"] = current_request_id()
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
