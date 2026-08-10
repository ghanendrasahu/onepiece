"""Billing routes: plans, checkout, portal, invoices (docs/06-api-specification.md §8)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..gateway import build_gateway
from ..models import Subscription, Transaction
from ..schemas import (
    CheckoutIn,
    CheckoutOut,
    InvoiceOut,
    PlanOut,
    PortalOut,
    SubscriptionOut,
)

router = APIRouter(prefix="/v1/billing", tags=["billing"])

_PLANS: list[PlanOut] = [
    PlanOut(
        id="free",
        name="Explorer",
        price_cents=0,
        features=["1 guide ask / hour", "720p VOD", "public rooms"],
    ),
    PlanOut(
        id="pro",
        name="World Pass",
        price_cents=1199,
        features=["Unlimited guide asks", "4K VOD + offline", "private tours"],
    ),
    PlanOut(
        id="creator",
        name="Creator",
        price_cents=2999,
        features=["Go-live tools", "pay-per-tour", "tips + payouts"],
    ),
]


def _invoice_out(tx: Transaction) -> InvoiceOut:
    return InvoiceOut(
        id=tx.id,
        amount_cents=tx.gross_cents,
        currency=tx.currency,
        status=tx.status,
        created_at=tx.created_at.isoformat(),
    )


@router.get("/plans", response_model=list[PlanOut])
def list_plans() -> list[PlanOut]:
    return _PLANS


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    payload: CheckoutIn,
    claims: dict = Depends(get_current_user),
) -> CheckoutOut:
    plans = {p.id: p for p in _PLANS}
    if payload.plan_id not in plans:
        raise HTTPException(status_code=404, detail="Unknown plan")
    from worldview.config import get_settings

    settings = get_settings()
    gateway = build_gateway(settings.stripe_secret_key, payload.provider)
    result = await gateway.create_checkout(payload.plan_id, claims["sub"], payload.success_url)
    return CheckoutOut(
        checkout_url=result.checkout_url,
        provider_checkout_id=result.provider_checkout_id,
    )


@router.post("/portal", response_model=PortalOut)
def customer_portal(claims: dict = Depends(get_current_user)) -> PortalOut:
    from worldview.config import get_settings

    settings = get_settings()
    if settings.stripe_secret_key:
        return PortalOut(portal_url=f"https://billing.stripe.com/c/portal/{claims['sub']}")
    return PortalOut(portal_url=f"https://billing.worldview.vr/mock/portal/{claims['sub']}")


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Subscription]:
    rows = db.execute(
        select(Subscription)
        .where(Subscription.user_id == claims["sub"])
        .order_by(Subscription.created_at.desc())
    ).scalars()
    return list(rows)


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    rows = db.execute(
        select(Transaction)
        .where(Transaction.user_id == claims["sub"], Transaction.type == "sub_renewal")
        .order_by(Transaction.created_at.desc())
    ).scalars()
    return [_invoice_out(tx) for tx in rows]


def new_subscription(
    user_id: str, plan_id: str, provider: str, period_end: datetime
) -> Subscription:
    return Subscription(
        id=str(new_ulid()),
        user_id=user_id,
        plan_id=plan_id,
        status="active",
        provider=provider,
        current_period_end=period_end,
    )


def record_purchase(
    db: Session,
    user_id: str,
    tx_type: str,
    gross_cents: int,
    idempotency_key: str | None,
    provider_tx_id: str | None = None,
) -> Transaction:
    from math import floor

    fee_cents = floor(gross_cents * 0.029) + 30
    tx = Transaction(
        id=str(new_ulid()),
        user_id=user_id,
        type=tx_type,
        gross_cents=gross_cents,
        fee_cents=fee_cents,
        net_cents=gross_cents - fee_cents,
        provider_tx_id=provider_tx_id,
        idempotency_key=idempotency_key,
        status="succeeded",
        created_at=datetime.now(UTC),
    )
    db.add(tx)
    db.flush()
    return tx


__all__ = ["_PLANS", "list_plans", "new_subscription", "record_purchase"]
