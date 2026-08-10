"""Cross-service reporting to the moderation service (FR-9.3).

The streaming service does not own moderation rows; it forwards viewer reports
to the moderation upstream over HTTP. Returns ``None`` when unreachable so the
calling route can 503 cleanly instead of half-processing a report.
"""

from __future__ import annotations

import httpx
from worldview.config import get_settings


def submit_report(
    stream_id: str,
    reporter_id: str,
    reason: str | None,
    context: str | None,
) -> str | None:
    from worldview.auth import create_access_token

    settings = get_settings()
    if not settings.moderation_service_url:
        return None
    client_token = create_access_token(reporter_id, scopes=["user"])
    try:
        resp = httpx.post(
            f"{settings.moderation_service_url}/v1/reports",
            headers={"Authorization": f"Bearer {client_token}"},
            timeout=5.0,
            json={
                "object_type": "stream",
                "object_id": stream_id,
                "reason": reason,
                "context": context,
            },
        )
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPError:
        return None
