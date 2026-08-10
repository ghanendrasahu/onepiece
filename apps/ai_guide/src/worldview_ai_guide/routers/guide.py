"""AI guide routes."""

import httpx
from fastapi import APIRouter, Depends, Query

from ..catalog import CatalogClient, KnowledgeService
from ..knowledge import SUPPORTED_LANGUAGES, KnowledgeEntry
from ..provider import Answer, MockProvider, Provider, build_provider
from ..schemas import (
    AskIn,
    AskOut,
    Citation,
    IdentifyIn,
    IdentifyOut,
    ItineraryOut,
    ItineraryStop,
    LanguagesOut,
    TranslateSignOut,
)

router = APIRouter(prefix="/v1/guide", tags=["guide"])

_service: KnowledgeService | None = None


def _provider() -> Provider:
    from worldview.config import get_settings

    settings = get_settings()
    return build_provider(
        settings.ai_provider,
        settings.model_gateway_url,
    )


def get_knowledge_service() -> KnowledgeService:
    """Return the process-wide knowledge service (lazy, request-independent)."""
    global _service
    if _service is None:
        from worldview.config import get_settings

        _service = KnowledgeService(CatalogClient(get_settings().catalog_service_url))
    return _service


def _provider_name(provider: Provider) -> str:
    return type(provider).__name__


async def _active_poi(
    knowledge: KnowledgeService, tour_id: str | None, t: float
) -> KnowledgeEntry | None:
    """Return the POI active at playback time ``t`` for ``tour_id``."""
    if not tour_id:
        return None
    entries = await knowledge.entries()
    for entry in entries:
        if entry.tour_id != tour_id:
            continue
        if entry.t_begin_sec <= t and (entry.t_end_sec is None or t <= entry.t_end_sec):
            return entry
    return None


def _guess_kind(tags: tuple[str, ...]) -> str:
    lowered = " ".join(tags).lower()
    if "plant" in lowered or "tree" in lowered or "flower" in lowered:
        return "plant"
    if "animal" in lowered or "bird" in lowered:
        return "animal"
    if "landmark" in lowered or "building" in lowered or "statue" in lowered:
        return "landmark"
    return "unknown"


def _dwell(tags: tuple[str, ...]) -> int:
    lowered = " ".join(tags).lower()
    if "museum" in lowered:
        return 90
    if "landmark" in lowered:
        return 45
    return 30


async def _complete(provider: Provider, query: str, context, lang: str) -> tuple[Answer, str]:
    """Complete, degrading to the mock on any model-gateway transport error."""
    try:
        answer = await provider.complete(query, context, lang)
        return answer, type(provider).__name__
    except httpx.HTTPError:
        mock = MockProvider()
        answer = await mock.complete(query, context, lang)
        return answer, type(mock).__name__


@router.post("/ask", response_model=AskOut)
async def ask(
    payload: AskIn,
    provider: Provider = Depends(_provider),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
) -> AskOut:
    retriever = await knowledge.retriever()
    context = retriever.search(payload.text, tour_id=payload.tour_id, top_k=6)
    answer, provider_name = await _complete(provider, payload.text, context, payload.lang)
    return AskOut(
        answer=answer.answer,
        lang=answer.lang,
        citations=[Citation(**c) for c in answer.citations],
        suggested_hotspots=answer.suggested_hotspots,
        provider=provider_name,
    )


@router.post("/translate-sign", response_model=TranslateSignOut)
async def translate_sign(payload: dict) -> TranslateSignOut:
    # T1: OCR frame -> translate via NMT. Stub returns echo.
    text = payload.get("ocr_text") or "(sign detected)"
    return TranslateSignOut(ocr_text=text, translation=f"[{text}]", lang=payload.get("lang", "en"))


@router.post("/identify", response_model=IdentifyOut)
async def identify(
    payload: IdentifyIn,
    provider: Provider = Depends(_provider),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
) -> IdentifyOut:
    """Identify a plant/animal/landmark at playback time ``t`` (FR-4.2).

    Grounding: the active POI at the moment the user points the viewfinder is
    the primary candidate. The LLM provider refines/describes it when a gateway
    is configured; the mock returns the grounded candidate with confidence 1.
    """
    active = await _active_poi(knowledge, payload.tour_id, payload.t)
    if active is None:
        return IdentifyOut(
            label="unknown",
            kind="unknown",
            confidence=0.0,
            poi_id=None,
            description="I could not identify anything here yet.",
            provider=_provider_name(provider),
        )
    try:
        answer = await provider.complete(
            "What is the landmark or feature I'm looking at? Identify it.",
            [active],
            payload.lang,
        )
    except httpx.HTTPError:
        answer = await MockProvider().complete(
            "What is the landmark or feature I'm looking at? Identify it.",
            [active],
            payload.lang,
        )
    description = answer.answer if answer.answer else active.text
    kind = _guess_kind(active.tags)
    return IdentifyOut(
        label=active.name_en,
        kind=kind,
        confidence=1.0,
        poi_id=active.id,
        description=description,
        provider=_provider_name(provider),
    )


@router.get("/itinerary", response_model=ItineraryOut)
async def itinerary(
    prefs: list[str] = Query(default=[], max_length=20),
    duration_hours: float = Query(default=4, gt=0, le=24),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
) -> ItineraryOut:
    """Build a day plan from saved/preferred POIs (FR-4.7, T1).

    Selects candidate POIs by keyword preference then greedily packs them into
    the requested window, capping each stop at a sensible dwell time.
    """
    entries = await knowledge.entries()
    pref_list = [p.lower() for p in prefs]
    candidates = [
        e for e in entries if not pref_list or any(p in e.text.lower() for p in pref_list)
    ]
    if not candidates:
        candidates = entries

    stops, used, remaining = [], set(), duration_hours * 60.0
    for entry in candidates:
        if entry.id in used:
            continue
        stop_minutes = _dwell(entry.tags)
        if stop_minutes > remaining:
            continue
        used.add(entry.id)
        stops.append(
            ItineraryStop(
                poi_id=entry.id,
                tour_id=entry.tour_id,
                name=entry.name_en,
                description_en=entry.text,
                t_begin=entry.t_begin_sec,
                stop_minutes=stop_minutes,
            )
        )
        remaining -= stop_minutes
        if remaining < 15:
            break

    total = duration_hours - remaining / 60.0
    return ItineraryOut(
        stops=stops,
        total_hours=round(total, 1),
        rationale=(
            "Packed preferred POIs into the requested window, leaving buffer "
            "time for travel between stops."
        ),
        provider="mock",
    )


@router.get("/languages", response_model=LanguagesOut)
async def languages() -> LanguagesOut:
    return LanguagesOut(languages=list(SUPPORTED_LANGUAGES))
