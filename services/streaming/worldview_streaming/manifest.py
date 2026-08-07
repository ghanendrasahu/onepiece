"""Media manifest generation for live VR sessions.

For each rung in a session's quality ladder we emit a playable HLS rendition.
In production the segment lists are produced by the media (packaging) tier;
this module is the control-plane view the client asks for before playback.
"""

from __future__ import annotations

from .models import StreamSession
from .schemas import ManifestOut, Rendition

_QUALITY_RESOLUTION = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k_tiled": (3840, 2160),
}
_DEFAULT_RESOLUTION = (1280, 720)


def build_manifest(session: StreamSession) -> ManifestOut:
    rungs = [rung.strip() for rung in session.quality_ladder.split(",") if rung.strip()]
    renditions = [
        Rendition(
            quality=rung,
            width=width,
            height=height,
            manifest_url=f"/v1/streams/{session.id}/renditions/{rung}/index.m3u8",
        )
        for rung in rungs
        for width, height in [_QUALITY_RESOLUTION.get(rung, _DEFAULT_RESOLUTION)]
    ]
    return ManifestOut(session_id=session.id, status=session.status, renditions=renditions)
