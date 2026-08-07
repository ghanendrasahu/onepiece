"""AI guide tests: retriever + RAG endpoint + catalog grounding."""

import pytest
from fastapi.testclient import TestClient
from worldview_ai_guide.catalog import KnowledgeService
from worldview_ai_guide.knowledge import SEED_ENTRIES, KeywordRetriever, KnowledgeEntry
from worldview_ai_guide.main import app
from worldview_ai_guide.routers import guide


class _FakeCatalog:
    def __init__(self, entries):
        self._entries = entries

    async def knowledge_entries(self):
        return self._entries


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_keyword_retriever_finds_matching_entry():
    retriever = KeywordRetriever(SEED_ENTRIES)
    results = retriever.search("what building is the orange tower?", tour_id="tour-tokyo")
    assert results and results[0].name_en == "Tokyo Tower"


def test_retriever_respects_tour_filter():
    retriever = KeywordRetriever(SEED_ENTRIES)
    results = retriever.search("ramen", tour_id="tour-paris")
    assert all(e.tour_id == "tour-paris" for e in results)


def test_ask_returns_grounded_answer(client):
    r = client.post(
        "/v1/guide/ask",
        json={
            "tour_id": "tour-tokyo",
            "t": 120,
            "text": "What is that orange tower?",
            "lang": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "Tokyo Tower" in body["answer"]
    assert body["citations"][0]["name"] == "Tokyo Tower"
    assert body["provider"] == "MockProvider"


def test_ask_unknown_returns_honest_fallback(client):
    r = client.post(
        "/v1/guide/ask", json={"tour_id": "tour-tokyo", "text": "quantum physics", "lang": "en"}
    )
    body = r.json()
    assert body["citations"] == []


def test_languages(client):
    langs = client.get("/v1/guide/languages").json()["languages"]
    assert "en" in langs and "ja" in langs


def test_ask_grounded_from_live_catalog():
    catalog_entry = KnowledgeEntry(
        id="poi-old-town",
        tour_id="tour-tokyo",
        name_en="Old Town Square",
        text="Prague's Old Town Square is home to the famous Astronomical Clock.",
        tags=("landmark", "square", "clock"),
    )
    service = KnowledgeService(_FakeCatalog([catalog_entry]))
    app.dependency_overrides[guide.get_knowledge_service] = lambda: service
    try:
        with TestClient(app) as c:
            r = c.post(
                "/v1/guide/ask",
                json={"tour_id": "tour-tokyo", "text": "tell me about the clock", "lang": "en"},
            )
        assert r.status_code == 200
        body = r.json()
        assert "Old Town Square" in body["answer"]
        assert body["citations"][0]["name"] == "Old Town Square"
    finally:
        app.dependency_overrides.clear()


def test_knowledge_service_merges_live_over_seed():
    catalog_entry = KnowledgeEntry(
        id="poi-tokyo-tower",
        tour_id="tour-tokyo",
        name_en="Tokyo Tower Reborn",
        text="A catalog-curated entry that must override the stale seed.",
        tags=("landmark",),
    )
    service = KnowledgeService(_FakeCatalog([catalog_entry]))

    import asyncio

    entries = asyncio.run(service.entries())
    by_id = {e.id: e for e in entries}
    assert by_id["poi-tokyo-tower"].name_en == "Tokyo Tower Reborn"
