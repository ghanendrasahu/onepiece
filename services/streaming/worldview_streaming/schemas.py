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
