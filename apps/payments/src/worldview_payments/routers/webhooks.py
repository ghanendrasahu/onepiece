"""Stripe webhook handling (docs/06-api-specification.md §8).

Signature verification uses the webhook secret when configured; in dev/mock mode
payloads are still validated structurally so the flow is testable end to end.
Responds 200 fast and processes asynchronously to match the "process async"
prescription.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from worldview.config import get_settings
from worldview.db import get_db

from .billing import new_subscription, record_purchase

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

_logger = logging.getLogger("worldview_payments.webhooks")

_PERIOD_HOURS = {"month": 730, "year": 8760}


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    settings = get_settings()
    signature = request.headers.get("stripe-signature")
    if settings.stripe_webhook_secret and not signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        raw_body = await request.body()
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid body") from exc

    event_type = payload.get("type", "")
    handler = _HANDLERS.get(event_type)
    if handler is None:
        return {"received": True}  # acknowledge unhandled event types

    if settings.stripe_webhook_secret:
        _verify_signature(raw_body, signature, settings.stripe_webhook_secret)

    asyncio.get_running_loop().create_task(handler(db, payload.get("data", {})))
    return {"received": True}


async def _on_checkout_completed(db: Session, data: dict) -> None:
    obj = data.get("object", {})
    customer_id = obj.get("customer")
    plan_id = obj.get("metadata", {}).get("plan_id")
    if not customer_id or not plan_id:
        return
    sub = new_subscription(
        user_id=customer_id,
        plan_id=plan_id,
        provider="stripe",
        period_end=datetime.now(UTC) + timedelta(hours=_PERIOD_HOURS.get("month", 730)),
    )
    sub.provider_sub_id = obj.get("subscription")
    db.add(sub)
    db.commit()
    _logger.info("Subscription activated", extra={"user_id": customer_id, "plan": plan_id})


async def _on_invoice_paid(db: Session, data: dict) -> None:
    obj = data.get("object", {})
    customer_id = obj.get("customer")
    amount = obj.get("amount_paid") or obj.get("amount_due") or 0
    if not customer_id:
        return
    record_purchase(
        db,
        customer_id,
        "sub_renewal",
        int(amount) // 100,
        f"stripe:{obj.get('id')}",
        provider_tx_id=obj.get("payment_intent"),
    )
    db.commit()


_HANDLERS = {
    "checkout.session.completed": _on_checkout_completed,
    "invoice.paid": _on_invoice_paid,
}


def _verify_signature(raw_body: bytes, signature: str, secret: str) -> None:
    """Verify the canonical Stripe signature: ``t=<ts>,v1=<hmac-sha256(ts.raw)``.

    Uses the exact raw request body as required by Stripe (re-serialization
    would break the MAC). Tolerates clock skew of a few minutes.
    """
    params: dict[str, str] = {}
    for part in signature.split(","):
        name, _, value = part.partition("=")
        params[name.strip()] = value.strip()

    timestamp = params.get("t")
    candidate = params.get("v1")
    if not timestamp or not candidate:
        raise HTTPException(status_code=400, detail="Malformed signature")

    try:
        ts_int = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Malformed signature timestamp") from exc
    if abs(int(datetime.now(UTC).timestamp()) - ts_int) > 300:
        raise HTTPException(status_code=400, detail="Stale signature")

    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, candidate):
        raise HTTPException(status_code=400, detail="Invalid signature")
