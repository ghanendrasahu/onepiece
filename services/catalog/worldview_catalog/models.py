"""Catalog ORM models: tours, POIs, hotspots."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from worldview.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Tour(Base):
    __tablename__ = "tours"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    title_en: Mapped[str] = mapped_column(String(200), index=True)
    title_i18n: Mapped[dict] = mapped_column(JSON, default=dict)
    kind: Mapped[str] = mapped_column(String(20), default="vod")  # live|vod|ai_guided|time_travel
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True
    )  # draft|published|archived
    creator_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    region_key: Mapped[str] = mapped_column(String(20), index=True)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    premium: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Poi(Base):
    __tablename__ = "pois"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    tour_id: Mapped[str] = mapped_column(ForeignKey("tours.id", ondelete="CASCADE"), index=True)
    name_en: Mapped[str] = mapped_column(String(200))
    name_i18n: Mapped[dict] = mapped_column(JSON, default=dict)
    t_begin_sec: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    t_end_sec: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    look_dir: Mapped[dict] = mapped_column(JSON, default=dict)  # {"yaw":..,"pitch":..}
    poi_type: Mapped[str] = mapped_column(String(20), default="landmark")
    description_en: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class Hotspot(Base):
    __tablename__ = "hotspots"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    poi_id: Mapped[str] = mapped_column(ForeignKey("pois.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="info")  # info|photo|quiz|audio
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
