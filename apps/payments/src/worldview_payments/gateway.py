"""Payment-gateway abstraction (Stripe first, deterministic mock fallback).

Follows the same shape as ai_guide's provider module: a protocol surface plus
two implementations. When ``STRIPE_SECRET_KEY`` is set the real Stripe API is
used for checkout; otherwise a :class:`MockGateway` produces stable fake URLs
so the whole payments flow is exercisable in dev and CI with zero external
calls.
"""

from __future__ import annotations

import importlib.util
from typing import Protocol
from urllib.parse import quote

from pydantic import BaseModel
from ulid import new as new_ulid


class CheckoutResult(BaseModel):
    checkout_url: str
    provider_checkout_id: str


class Gateway(Protocol):
    async def create_checkout(
        self, plan_id: str, customer_id: str, success_url: str | None
    ) -> CheckoutResult: ...


class MockGateway:
    """Deterministic offline checkout; no external calls."""

    async def create_checkout(
        self, plan_id: str, customer_id: str, success_url: str | None
    ) -> CheckoutResult:
        checkout_id = f"cs_mock_{plan_id}_{new_ulid()}"
        base = "https://checkout.worldview.vr/mock"
        url = f"{base}?session={checkout_id}&customer={quote(customer_id)}"
        if success_url:
            url += f"&redirect={quote(success_url)}"
        return CheckoutResult(checkout_url=url, provider_checkout_id=checkout_id)


class StripeGateway:
    """Thin Stripe Checkout wrapper (hosted, subscription mode)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def create_checkout(
        self, plan_id: str, customer_id: str, success_url: str | None
    ) -> CheckoutResult:
        _check_import("stripe")
        import stripe  # pyright: ignore[reportMissingImports]  # optional SDK, guarded above

        stripe.api_key = self._api_key
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": plan_id, "quantity": 1}],
            success_url=success_url or "https://worldview.vr/billing/success",
            cancel_url="https://worldview.vr/billing",
            metadata={"customer_id": customer_id},
        )
        return CheckoutResult(checkout_url=session.url, provider_checkout_id=session.id)


def build_gateway(secret_key: str | None, provider: str = "stripe") -> Gateway:
    """Return Stripe when a key is configured, else the deterministic mock."""
    if provider != "stripe" or not secret_key:
        return MockGateway()
    return StripeGateway(secret_key)


def _check_import(pkg: str) -> None:
    """Fail fast with an actionable message when an optional SDK is missing."""
    if not _importable(pkg):
        raise RuntimeError(
            f"The '{pkg}' SDK is not installed. Add it to apps/payments, e.g. "
            f"`uv add --package worldview-payments {pkg}`."
        )


def _importable(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None
