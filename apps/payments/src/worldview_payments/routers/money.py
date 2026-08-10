"""Payouts, tips and pay-per-tour routes (docs/06-api-specification.md §8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import Tip, Transaction
from ..schemas import TipIn, TipOut, TransactionOut
from .billing import record_purchase

router = APIRouter(prefix="/v1", tags=["money"])


@router.post("/tips/{stream_id}", response_model=TipOut, status_code=201)
def create_tip(
    stream_id: str,
    payload: TipIn,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tip:
    from ..catalog_client import resolve_stream_creator

    creator_id = resolve_stream_creator(stream_id)
    if creator_id is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    if payload.idempotency_key:
        from sqlalchemy import select

        existing_tx = db.execute(
            select(Transaction).where(
                Transaction.idempotency_key == payload.idempotency_key,
                Transaction.user_id == claims["sub"],
            )
        ).scalar_one_or_none()
        if existing_tx is not None:
            existing_tip = db.execute(
                select(Tip).where(Tip.id == existing_tx.id)
            ).scalar_one_or_none()
            if existing_tip is not None:
                return existing_tip

    tx = record_purchase(db, claims["sub"], "tip", payload.cents, payload.idempotency_key)
    tip = Tip(
        id=tx.id,
        stream_id=stream_id,
        from_user=claims["sub"],
        to_creator=creator_id,
        cents=payload.cents,
        message=payload.message,
    )
    db.add(tip)
    db.commit()
    db.refresh(tip)
    return tip


@router.post("/tours/{tour_id}/purchase", response_model=TransactionOut, status_code=201)
def purchase_tour(
    tour_id: str,
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    from ..catalog_client import resolve_tour_price

    price_cents = resolve_tour_price(tour_id)
    if price_cents is None:
        raise HTTPException(status_code=404, detail="Tour not found")

    tx = record_purchase(
        db,
        claims["sub"],
        "pay_per_tour",
        price_cents,
        f"tour:{tour_id}:{claims['sub']}",
    )
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/purchases", response_model=list[TransactionOut])
def list_purchases(
    claims: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Transaction]:
    from sqlalchemy import select

    rows = db.execute(
        select(Transaction)
        .where(Transaction.user_id == claims["sub"], Transaction.type == "pay_per_tour")
        .order_by(Transaction.created_at.desc())
    ).scalars()
    return list(rows)
