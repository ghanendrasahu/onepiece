"""AI guide schemas."""

from pydantic import BaseModel, Field


class AskIn(BaseModel):
    tour_id: str | None = None
    t: float = Field(default=0.0, ge=0)
    look_dir: dict = Field(default_factory=lambda: {"yaw": 0.0, "pitch": 0.0})
    text: str = Field(min_length=1, max_length=500)
    lang: str = Field(default="en", max_length=10)
    stream: bool = False


class Citation(BaseModel):
    poi_id: str
    type: str = "poi"
    name: str
    t_begin: float = 0.0


class AskOut(BaseModel):
    answer: str
    lang: str
    citations: list[Citation]
    suggested_hotspots: list[str]
    provider: str


class TranslateSignOut(BaseModel):
    ocr_text: str
    translation: str
    lang: str


class LanguagesOut(BaseModel):
    languages: list[str]


class IdentifyIn(BaseModel):
    tour_id: str | None = None
    t: float = Field(default=0.0, ge=0)
    bbox: list[float] | None = Field(default=None, max_length=4)
    lang: str = Field(default="en", max_length=10)


class IdentifyOut(BaseModel):
    label: str
    kind: str  # plant|animal|landmark|unknown
    confidence: float = Field(default=0.0, ge=0, le=1)
    poi_id: str | None = None
    description: str | None = None
    provider: str


class ItineraryStop(BaseModel):
    poi_id: str
    tour_id: str
    name: str
    description_en: str | None = None
    t_begin: float
    stop_minutes: int


class ItineraryOut(BaseModel):
    stops: list[ItineraryStop]
    total_hours: float
    rationale: str
    provider: str
