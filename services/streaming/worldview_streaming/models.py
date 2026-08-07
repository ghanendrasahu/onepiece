"""Streaming-control ORM models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from worldview.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    tour_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    creator_id: Mapped[str] = mapped_column(String(26), index=True)
    status: Mapped[str] = mapped_column(String(20), default="preparing", index=True)
    quality_ladder: Mapped[str] = mapped_column(String(100), default="720p,1080p,4k_tiled")
    ingest_endpoint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    spatial_audio: Mapped[bool] = mapped_column(default=False)
    region_key: Mapped[str] = mapped_column(String(20), default="us-east-1")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
