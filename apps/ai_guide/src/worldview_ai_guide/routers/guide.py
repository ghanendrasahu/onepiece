"""AI guide routes."""

import httpx
from fastapi import APIRouter, Depends

from ..catalog import CatalogClient, KnowledgeService
from ..knowledge import SUPPORTED_LANGUAGES
from ..provider import Answer, MockProvider, Provider, build_provider
from ..schemas import AskIn, AskOut, Citation, LanguagesOut, TranslateSignOut

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


@router.get("/languages", response_model=LanguagesOut)
async def languages() -> LanguagesOut:
    return LanguagesOut(languages=list(SUPPORTED_LANGUAGES))
