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
