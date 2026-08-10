"""Payments ORM models: subscriptions, transactions, tips (docs/05 §3.5)."""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from worldview.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), index=True)
    plan_id: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    provider: Mapped[str] = mapped_column(String(20), default="stripe")
    provider_sub_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), index=True)
    type: Mapped[str] = mapped_column(String(20))  # sub_renewal|pay_per_tour|tip|payout|refund
    gross_cents: Mapped[int] = mapped_column(BigInteger)
    fee_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    net_cents: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(5), default="USD")
    provider_tx_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Tip(Base):
    __tablename__ = "tips"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    stream_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    from_user: Mapped[str] = mapped_column(String(26), index=True)
    to_creator: Mapped[str] = mapped_column(String(26), index=True)
    cents: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
