"""LLM provider abstraction.

Two implementations:
- :class:`MockProvider` - deterministic, offline, used in dev/tests and as the
  graceful-degradation fallback when the model gateway is unavailable.
- :class:`GatewayProvider` - calls the Model Gateway (or vendor directly) over
  HTTP for production-grade grounded answers.
"""

from __future__ import annotations

from typing import Protocol

import httpx
from pydantic import BaseModel

from .knowledge import SEED_ENTRIES, KeywordRetriever, KnowledgeEntry


class Answer(BaseModel):
    answer: str
    lang: str
    citations: list[dict]
    suggested_hotspots: list[str]


class Provider(Protocol):
    async def complete(
        self,
        query: str,
        context: list[KnowledgeEntry],
        lang: str,
    ) -> Answer: ...


class MockProvider:
    """Deterministic fallback: synthesizes an answer from retrieved context."""

    async def complete(
        self,
        query: str,
        context: list[KnowledgeEntry],
        lang: str,
    ) -> Answer:
        if not context:
            return Answer(
                answer="I don't have enough information about that here yet.",
                lang=lang,
                citations=[],
                suggested_hotspots=[],
            )
        entry = context[0]
        answer = (
            f"That's the {entry.name_en}. {entry.text} "
            "(This is a cached offline answer - the live model gateway is unavailable.)"
        )
        return Answer(
            answer=answer,
            lang=lang,
            citations=[
                {
                    "poi_id": entry.id,
                    "type": "poi",
                    "name": entry.name_en,
                    "t_begin": entry.t_begin_sec,
                }
            ],
            suggested_hotspots=[c.id for c in context[1:3]],
        )


class GatewayProvider:
    """Calls the WorldView Model Gateway (or a vendor) for grounded answers.

    Expects ``POST /v1/complete`` with ``{"query", "context", "lang"}``.
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def complete(
        self,
        query: str,
        context: list[KnowledgeEntry],
        lang: str,
    ) -> Answer:
        payload = {
            "query": query,
            "context": [entry.text for entry in context],
            "lang": lang,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        resp = await self._client.post(
            f"{self._base_url}/v1/complete", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return Answer(**data)

    async def aclose(self) -> None:
        await self._client.aclose()


def build_provider(
    provider_name: str, gateway_url: str | None, api_key: str | None = None
) -> Provider:
    if provider_name == "mock" or gateway_url is None:
        return MockProvider()
    return GatewayProvider(gateway_url, api_key)


def build_retriever() -> KeywordRetriever:
    return KeywordRetriever(SEED_ENTRIES)
