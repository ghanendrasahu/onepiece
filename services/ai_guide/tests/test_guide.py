"""AI guide tests: retriever + RAG endpoint."""

import pytest
from fastapi.testclient import TestClient
from worldview_ai_guide.knowledge import SEED_ENTRIES, KeywordRetriever
from worldview_ai_guide.main import app


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
