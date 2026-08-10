"""Cross-service lookups from the catalog API (tour price, stream creator).

The payments service does not own catalog rows; it resolves price / creator by
calling the catalog's REST API (``CATALOG_SERVICE_URL``). When the catalog is
unreachable for non-published rows we return ``None`` so the money routes can
404 cleanly instead of importing catalog ORM models.
"""

from __future__ import annotations

import functools

import httpx
from worldview.config import get_settings


@functools.lru_cache(maxsize=1)
def _client() -> httpx.Client:
    return httpx.Client(base_url=get_settings().catalog_service_url, timeout=5.0)


def resolve_tour_price(tour_id: str) -> int | None:
    """Return the published tour's price in cents, else None."""
    try:
        resp = _client().get(f"/v1/tours/{tour_id}")
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != "published":
        return None
    return int(data.get("price_cents", 0))


def resolve_stream_creator(stream_id: str) -> str | None:
    """Return the stream creator's user id, else None."""
    try:
        resp = _client().get(f"/v1/streams/{stream_id}")
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") in {"ended", "cancelled"}:
        return None
    return data.get("creator_id")
