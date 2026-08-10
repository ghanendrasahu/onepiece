"""Creator-platform ORM models (docs/06-api-specification.md §9).

The schema is a single shared Postgres database: creator rows live here while
stream sessions and money movement live in the owning services. Routers lazily
import those cross-app models for read-only aggregation (same pattern as the
moderation admin console).
"""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from worldview.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CreatorProfile(Base):
    """A user's creator onboarding state (FR-5.1)."""

    __tablename__ = "creator_profiles"

    user_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(20), default="applied", index=True
    )  # applied|verified|rejected
    equipment: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(String(40), nullable=True)
    id_doc_token: Mapped[str | None] = mapped_column(String(120), nullable=True)
    liveness_token: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class EquipmentLoan(Base):
    """Equipment loaner program request (FR-5.7, T1)."""

    __tablename__ = "equipment_loans"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), index=True)
    equipment: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(
        String(20), default="requested", index=True
    )  # requested|approved|shipped|returned|declined
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Payout(Base):
    """Creator payout record (FR-5.6). Money leaves via a payout provider."""

    __tablename__ = "payouts"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    creator_id: Mapped[str] = mapped_column(String(26), index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(5), default="USD")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending|paid|failed
    provider_tx_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PrivateTourOffer(Base):
    """A bookable private-tour offering (FR-5.5)."""

    __tablename__ = "private_tour_offers"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    creator_id: Mapped[str] = mapped_column(String(26), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(String(5), default="USD")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # draft|published
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
