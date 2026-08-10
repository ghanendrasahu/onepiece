"""Creator-platform schemas (docs/06-api-specification.md §9)."""

from datetime import datetime

from pydantic import BaseModel, Field
from worldview.schemas import OrmModel


class CreatorApplyIn(BaseModel):
    equipment: list[str] = Field(default_factory=list, max_length=20)
    region: str = Field(min_length=1, max_length=40)
    id_doc_token: str = Field(min_length=1, max_length=120)


class CreatorVerifyIn(BaseModel):
    liveness_token: str = Field(min_length=1, max_length=120)
    geocheck: bool = True


class CreatorProfileOut(OrmModel):
    user_id: str
    status: str
    equipment: str | None
    region: str | None
    verified_at: datetime | None
    created_at: datetime


class CreatorStreamOut(BaseModel):
    id: str
    tour_id: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class DashboardOut(BaseModel):
    total_streams: int
    live_streams: int
    total_tips_cents: int
    pending_payout_cents: int
    paid_payout_cents: int
    private_tour_offers: int
    loan_requested: bool


class EquipmentLoanIn(BaseModel):
    equipment: str = Field(min_length=1, max_length=80)


class EquipmentLoanOut(OrmModel):
    id: str
    user_id: str
    equipment: str
    status: str
    created_at: datetime


class PayoutOut(OrmModel):
    id: str
    amount_cents: int
    currency: str
    status: str
    created_at: datetime


class PrivateTourIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    price_cents: int = Field(ge=0, le=10_000_000)


class PrivateTourOut(OrmModel):
    id: str
    creator_id: str
    title: str
    description: str | None
    price_cents: int
    currency: str
    status: str
    created_at: datetime
