"""Cross-service tip forwarding to the payments service (docs/06 §5).

The streaming service does not own money rows; ``POST /v1/streams/{id}/tip``
is an alias for the payments service's ``POST /v1/tips/{stream_id}``. Returns
``None`` when unreachable so the route can 503 cleanly.
"""

from __future__ import annotations

import httpx
from worldview.config import get_settings


def submit_tip(
    stream_id: str,
    user_id: str,
    cents: int,
    message: str | None,
    idempotency_key: str | None,
) -> dict | None:
    settings = get_settings()
    if not settings.payments_service_url:
        return None
    from worldview.auth import create_access_token

    client_token = create_access_token(user_id, scopes=["user"])
    body: dict = {"cents": cents}
    if message:
        body["message"] = message
    if idempotency_key:
        body["idempotency_key"] = idempotency_key
    try:
        resp = httpx.post(
            f"{settings.payments_service_url}/v1/tips/{stream_id}",
            headers={"Authorization": f"Bearer {client_token}"},
            timeout=5.0,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return None
