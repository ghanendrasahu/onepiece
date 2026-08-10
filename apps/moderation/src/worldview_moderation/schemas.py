"""Moderation & admin schemas (docs/06-api-specification.md §10, 05 §3.6)."""

from datetime import datetime

from pydantic import BaseModel, Field
from worldview.schemas import OrmModel

OBJECT_TYPES = ("chat", "stream", "avatar", "profile")
DECISIONS = ("approved", "flagged", "removed", "escalated")


class ReportIn(BaseModel):
    object_type: str = Field(pattern="^(chat|stream|avatar|profile)$")
    object_id: str = Field(min_length=1, max_length=26)
    reason: str | None = Field(default=None, max_length=100)
    context: str | None = Field(default=None, max_length=500)


class ModerationItemOut(OrmModel):
    id: str
    object_type: str
    object_id: str
    reporter_id: str | None
    reason: str | None
    risk_score: float | None
    decision: str | None
    auto_flag: bool
    reviewed_by: str | None
    created_at: datetime


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approved|flagged|removed|escalated)$")
    note: str | None = Field(default=None, max_length=500)


class SuspendIn(BaseModel):
    reason: str = Field(min_length=1, max_length=200)
    duration_hours: int = Field(default=24, gt=0, le=8760)


class AdminUserOut(BaseModel):
    id: str
    email: str
    display_name: str
    status: str = "active"  # active|suspended|deleted
    is_verified: bool


class AdminActionOut(OrmModel):
    id: str
    admin_id: str
    action: str
    target_type: str
    target_id: str
    note: str | None
    created_at: datetime
