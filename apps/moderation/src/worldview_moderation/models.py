"""Moderation ORM models (docs/05 §3.6)."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from worldview.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ModerationItem(Base):
    """A flagged object awaiting or resolved by a human moderator decision.

    ``object_type`` is one of ``chat|stream|avatar|profile``; ``decision`` is
    ``approved|flagged|removed|escalated`` (NULL while still queued).
    """

    __tablename__ = "moderation_items"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    object_type: Mapped[str] = mapped_column(String(20), index=True)
    object_id: Mapped[str] = mapped_column(String(26), index=True)
    reporter_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    auto_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(26), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AdminAction(Base):
    """Audit trail of admin/moderator actions (suspensions, decisions)."""

    __tablename__ = "admin_actions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    admin_id: Mapped[str] = mapped_column(String(26), index=True)
    action: Mapped[str] = mapped_column(String(30))
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[str] = mapped_column(String(26), index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EnterpriseGroup(Base):
    """A school/company/group with its own tour access (FR-10.2)."""

    __tablename__ = "enterprise_groups"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[str] = mapped_column(String(26), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EnterpriseGroupMember(Base):
    """Membership of an enterprise group."""

    __tablename__ = "enterprise_group_members"

    group_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EnterpriseEvent(Base):
    """A private virtual event hosted for an enterprise group (FR-10.2)."""

    __tablename__ = "enterprise_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    group_id: Mapped[str] = mapped_column(String(26), index=True)
    title: Mapped[str] = mapped_column(String(120))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
