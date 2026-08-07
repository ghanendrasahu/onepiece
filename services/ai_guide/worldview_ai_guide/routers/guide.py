"""AI guide routes."""

from fastapi import APIRouter, Depends

from ..knowledge import SEED_ENTRIES, SUPPORTED_LANGUAGES, KeywordRetriever
from ..provider import Provider, build_provider
from ..schemas import AskIn, AskOut, Citation, LanguagesOut, TranslateSignOut

router = APIRouter(prefix="/v1/guide", tags=["guide"])

_RETRIEVER = KeywordRetriever(SEED_ENTRIES)


def _provider() -> Provider:
    from worldview.config import get_settings

    settings = get_settings()
    return build_provider(
        settings.ai_provider,
        settings.model_gateway_url,
    )


@router.post("/ask", response_model=AskOut)
async def ask(payload: AskIn, provider: Provider = Depends(_provider)) -> AskOut:
    context = _RETRIEVER.search(payload.text, tour_id=payload.tour_id, top_k=6)
    answer = await provider.complete(payload.text, context, payload.lang)
    return AskOut(
        answer=answer.answer,
        lang=answer.lang,
        citations=[Citation(**c) for c in answer.citations],
        suggested_hotspots=answer.suggested_hotspots,
        provider=type(provider).__name__,
    )


@router.post("/translate-sign", response_model=TranslateSignOut)
async def translate_sign(payload: dict) -> TranslateSignOut:
    # T1: OCR frame -> translate via NMT. Stub returns echo.
    text = payload.get("ocr_text") or "(sign detected)"
    return TranslateSignOut(ocr_text=text, translation=f"[{text}]", lang=payload.get("lang", "en"))


@router.get("/languages", response_model=LanguagesOut)
async def languages() -> LanguagesOut:
    return LanguagesOut(languages=list(SUPPORTED_LANGUAGES))
