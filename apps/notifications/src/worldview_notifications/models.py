"""Notification-service ORM models (docs/06-api-specification.md §11).

``push_subscriptions`` records which device tokens a user wants notified and for
which topics; ``notification_log`` is an audit of deliveries (mock provider in
dev, FCM/APNs in production).
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from worldview.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), index=True)
    platform: Mapped[str] = mapped_column(String(10))  # apns|fcm|web
    push_token: Mapped[str] = mapped_column(String(300))
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(20), default="mock")
    status: Mapped[str] = mapped_column(String(20), default="sent", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
