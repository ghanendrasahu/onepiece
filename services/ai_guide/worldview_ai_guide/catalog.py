"""Grounded knowledge: seed data merged with the live catalog.

The static :data:`~worldview_ai_guide.knowledge.SEED_ENTRIES` demo seed is merged
with the POIs published in the catalog service. This makes the AI guide answer
from real, operator-curated tour content rather than a frozen script, while
still degrading gracefully to the seed when the catalog is unreachable.
"""

from __future__ import annotations

import time
from typing import Protocol

import httpx

from .knowledge import SEED_ENTRIES, KeywordRetriever, KnowledgeEntry


class CatalogPort(Protocol):
    """Minimal surface of the catalog the guide depends on."""

    async def knowledge_entries(self) -> list[KnowledgeEntry]: ...


class CatalogClient:
    """Fetches published tours + their POIs from the catalog service."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def knowledge_entries(self) -> list[KnowledgeEntry]:
        tours = await self._tours()
        entries: list[KnowledgeEntry] = []
        for tour in tours:
            for poi in await self._pois(tour["id"]):
                entries.append(_to_entry(tour, poi))
        return entries

    async def _tours(self) -> list[dict]:
        resp = await self._client.get(f"{self._base_url}/v1/tours", params={"limit": 100})
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def _pois(self, tour_id: str) -> list[dict]:
        resp = await self._client.get(f"{self._base_url}/v1/tours/{tour_id}/pois")
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


def _to_entry(tour: dict, poi: dict) -> KnowledgeEntry:
    t_end = poi.get("t_end_sec")
    text = poi.get("description_en") or f"{poi.get('name_en', '')} in {tour.get('title_en', '')}."
    return KnowledgeEntry(
        id=poi["id"],
        tour_id=poi["tour_id"],
        name_en=poi["name_en"],
        text=text,
        tags=(poi.get("poi_type", "landmark"),),
        t_begin_sec=float(poi.get("t_begin_sec", 0.0) or 0.0),
        t_end_sec=float(t_end) if t_end is not None else None,
    )


class KnowledgeService:
    """Merged, cached view of seed + catalog knowledge with a retriever."""

    def __init__(self, catalog: CatalogPort) -> None:
        self._catalog = catalog
        self._cache: list[KnowledgeEntry] | None = None
        self._loaded_at = 0.0

    async def entries(self, ttl_seconds: float = 300.0) -> list[KnowledgeEntry]:
        if self._cache is None or time.monotonic() - self._loaded_at > ttl_seconds:
            try:
                live = await self._catalog.knowledge_entries()
            except httpx.HTTPError:
                live = []
            merged: dict[str, KnowledgeEntry] = {e.id: e for e in SEED_ENTRIES}
            merged.update({e.id: e for e in live})  # live catalog overrides seed
            self._cache = list(merged.values())
            self._loaded_at = time.monotonic()
        return self._cache

    async def retriever(self, ttl_seconds: float = 300.0) -> KeywordRetriever:
        return KeywordRetriever(await self.entries(ttl_seconds))
