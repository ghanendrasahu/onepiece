"""Payments schemas (docs/06-api-specification.md §8)."""

from pydantic import BaseModel, Field
from worldview.schemas import OrmModel


class PlanOut(BaseModel):
    id: str
    name: str
    price_cents: int
    currency: str = "USD"
    period: str = "month"  # month|year
    features: list[str] = []


class CheckoutIn(BaseModel):
    plan_id: str
    provider: str = Field(default="web", pattern="^(web|apple|google)$")
    success_url: str | None = None


class CheckoutOut(BaseModel):
    checkout_url: str
    provider_checkout_id: str


class PortalOut(BaseModel):
    portal_url: str


class SubscriptionOut(OrmModel):
    id: str
    user_id: str
    plan_id: str
    status: str
    provider: str
    current_period_end: str


class InvoiceOut(BaseModel):
    id: str
    amount_cents: int
    currency: str
    status: str
    created_at: str


class TransactionOut(OrmModel):
    id: str
    type: str
    gross_cents: int
    fee_cents: int
    net_cents: int
    currency: str
    status: str


class TipIn(BaseModel):
    cents: int = Field(gt=0, le=1_000_000)
    message: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, max_length=200)


class TipOut(OrmModel):
    id: str
    stream_id: str | None
    from_user: str
    to_creator: str
    cents: int
    message: str | None


class WebhookIn(BaseModel):
    id: str | None = None
    object: str = "event"
    type: str = ""
    data: dict = None  # type: ignore[assignment]
