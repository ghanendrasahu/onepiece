"""Streaming-control schemas."""

from pydantic import BaseModel, Field
from worldview.schemas import OrmModel


class CreateStreamIn(BaseModel):
    tour_id: str | None = None
    quality_ladder: str = Field(default="720p,1080p,4k_tiled")
    spatial_audio: bool = False


class StreamOut(OrmModel):
    id: str
    tour_id: str | None
    creator_id: str
    status: str
    quality_ladder: str
    ingest_endpoint: str | None
    spatial_audio: bool
    version: int


class ActionIn(BaseModel):
    # future: reason / metadata for the transition
    note: str | None = None


class Rendition(BaseModel):
    quality: str
    media_type: str = "video"
    width: int
    height: int
    manifest_url: str


class ManifestOut(BaseModel):
    session_id: str
    status: str
    container: str = "hls"
    renditions: list[Rendition]


class StreamReportIn(BaseModel):
    reason: str | None = Field(default=None, max_length=100)
    context: str | None = Field(default=None, max_length=500)


class StreamReportAccepted(BaseModel):
    report_id: str


class TipIn(BaseModel):
    cents: int = Field(gt=0, le=1_000_000)
    message: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, max_length=200)


class TipAccepted(BaseModel):
    tip_id: str


class StreamStatsOut(OrmModel):
    id: str
    viewers: int
    tips_cents: int
