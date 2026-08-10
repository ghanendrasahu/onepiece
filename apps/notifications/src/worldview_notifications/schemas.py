"""Notification-service schemas (docs/06-api-specification.md §11)."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from worldview.schemas import OrmModel

PUSH_PLATFORMS = ("apns", "fcm", "web")
TOPICS = ("creator.live", "tour.published", "chat.mention", "tip.received", "booking.confirmed")


class SubscribeIn(BaseModel):
    push_token: str = Field(min_length=1, max_length=300)
    platform: str = Field(pattern=f"^({'|'.join(PUSH_PLATFORMS)})$")
    topics: list[str] = Field(default_factory=lambda: ["creator.live"])


class SubscribeOut(OrmModel):
    id: str
    user_id: str
    platform: str
    topics: list[str]
    created_at: datetime

    @field_validator("topics", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [t for t in v.split(",") if t]
        return v


class TestNotificationIn(BaseModel):
    topic: str = Field(pattern=f"^({'|'.join(TOPICS)})$")


class TestNotificationOut(OrmModel):
    id: str
    user_id: str
    topic: str
    status: str
    created_at: datetime
