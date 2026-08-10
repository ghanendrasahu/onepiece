"""Creator platform routes (docs/06-api-specification.md §9, FR-5).

Onboarding (apply/verify) writes creator rows owned by this service; the
dashboard and streams list aggregate read-only across the shared database using
streaming and payments models imported lazily inside each handler (same
cross-app pattern as the moderation admin console).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import worldview_payments.models as _payments_models  # noqa: F401  (register tables)
import worldview_streaming.models as _streaming_models  # noqa: F401  (register tables)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ulid import new as new_ulid
from worldview.auth import get_current_user
from worldview.db import get_db

from ..models import CreatorProfile, EquipmentLoan, Payout, PrivateTourOffer
from ..schemas import (
    CreatorApplyIn,
    CreatorProfileOut,
    CreatorStreamOut,
    CreatorVerifyIn,
    DashboardOut,
    EquipmentLoanIn,
    EquipmentLoanOut,
    PayoutOut,
    PrivateTourIn,
    PrivateTourOut,
)

router = APIRouter(prefix="/v1/creators", tags=["creators"])


def _profile_or_404(db: Session, user_id: str) -> CreatorProfile:
    profile = db.get(CreatorProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    return profile


@router.post("/apply", response_model=CreatorProfileOut, status_code=201)
def apply(
    payload: CreatorApplyIn,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreatorProfile:
    """Begin creator onboarding (FR-5.1). Re-apply updates equipment/region."""
    profile = db.get(CreatorProfile, claims["sub"])
    if profile is None:
        profile = CreatorProfile(
            user_id=claims["sub"],
            equipment=",".join(payload.equipment),
            region=payload.region,
            id_doc_token=payload.id_doc_token,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    profile.equipment = ",".join(payload.equipment)
    profile.region = payload.region
    profile.id_doc_token = payload.id_doc_token
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/verify", response_model=CreatorProfileOut)
def verify(
    payload: CreatorVerifyIn,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreatorProfile:
    """Complete identity verification (liveness + geo check) and grant verified."""
    profile = _profile_or_404(db, claims["sub"])
    if not payload.geocheck:
        raise HTTPException(status_code=422, detail="Geolocation check failed")
    profile.liveness_token = payload.liveness_token
    profile.status = "verified"
    profile.verified_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me/dashboard", response_model=DashboardOut)
def dashboard(
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOut:
    """Creator metrics: streams, tips, payouts (FR-5.4/5.6)."""
    _profile_or_404(db, claims["sub"])
    from worldview_payments.models import Tip
    from worldview_streaming.models import StreamSession

    total_streams = db.scalar(
        select(func.count())
        .select_from(StreamSession)
        .where(StreamSession.creator_id == claims["sub"])
    )
    live_streams = db.scalar(
        select(func.count())
        .select_from(StreamSession)
        .where(StreamSession.creator_id == claims["sub"], StreamSession.status == "live")
    )
    total_tips_cents = db.scalar(
        select(func.coalesce(func.sum(Tip.cents), 0)).where(Tip.to_creator == claims["sub"])
    )
    pending = db.scalar(
        select(func.coalesce(func.sum(Payout.amount_cents), 0)).where(
            Payout.creator_id == claims["sub"], Payout.status == "pending"
        )
    )
    paid = db.scalar(
        select(func.coalesce(func.sum(Payout.amount_cents), 0)).where(
            Payout.creator_id == claims["sub"], Payout.status == "paid"
        )
    )
    offers = db.scalar(
        select(func.count())
        .select_from(PrivateTourOffer)
        .where(PrivateTourOffer.creator_id == claims["sub"])
    )
    loan_requested = bool(
        db.scalar(
            select(func.count())
            .select_from(EquipmentLoan)
            .where(EquipmentLoan.user_id == claims["sub"])
        )
    )

    return DashboardOut(
        total_streams=total_streams or 0,
        live_streams=live_streams or 0,
        total_tips_cents=total_tips_cents or 0,
        pending_payout_cents=pending or 0,
        paid_payout_cents=paid or 0,
        private_tour_offers=offers or 0,
        loan_requested=loan_requested,
    )


@router.get("/me/streams", response_model=list[CreatorStreamOut])
def my_streams(
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CreatorStreamOut]:
    """List the creator's own stream sessions (read-only cross-app)."""
    _profile_or_404(db, claims["sub"])
    from worldview_streaming.models import StreamSession

    rows = db.execute(
        select(StreamSession)
        .where(StreamSession.creator_id == claims["sub"])
        .order_by(StreamSession.created_at.desc())
        .limit(200)
    ).scalars()
    return [
        CreatorStreamOut(
            id=s.id,
            tour_id=s.tour_id,
            status=s.status,
            started_at=s.started_at,
            ended_at=s.ended_at,
            created_at=s.created_at,
        )
        for s in rows
    ]


@router.post("/me/equipment-loan", response_model=EquipmentLoanOut, status_code=201)
def request_equipment_loan(
    payload: EquipmentLoanIn,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EquipmentLoan:
    """Request a loaner (FR-5.7, T1)."""
    _profile_or_404(db, claims["sub"])
    loan = EquipmentLoan(
        id=str(new_ulid()),
        user_id=claims["sub"],
        equipment=payload.equipment,
        status="requested",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.get("/me/payouts", response_model=list[PayoutOut])
def my_payouts(
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Payout]:
    _profile_or_404(db, claims["sub"])
    rows = db.execute(
        select(Payout)
        .where(Payout.creator_id == claims["sub"])
        .order_by(Payout.created_at.desc())
        .limit(200)
    ).scalars()
    return list(rows)


@router.post("/me/private-tours", response_model=PrivateTourOut, status_code=201)
def create_private_tour(
    payload: PrivateTourIn,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrivateTourOffer:
    """Create a private-tour booking offering (FR-5.5)."""
    _profile_or_404(db, claims["sub"])
    offer = PrivateTourOffer(
        id=str(new_ulid()),
        creator_id=claims["sub"],
        title=payload.title,
        description=payload.description,
        price_cents=payload.price_cents,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer
