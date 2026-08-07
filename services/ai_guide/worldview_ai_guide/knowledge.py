"""Grounded knowledge base for the AI guide.

The RAG pipeline retrieves context from here before calling the LLM. In
production the POI/tour knowledge is seeded into Milvus; this module provides a
pluggable retriever interface with a dependency-free keyword implementation so
the service runs and is testable offline.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol

_STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "what",
    "this",
    "that",
    "tell",
    "me",
    "about",
    "in",
    "on",
    "at",
    "of",
    "to",
    "for",
    "and",
    "or",
    "how",
    "why",
    "it",
    "there",
    "here",
}


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    tour_id: str
    name_en: str
    text: str
    tags: tuple[str, ...] = ()
    t_begin_sec: float = 0.0
    t_end_sec: float | None = None
    language: str = "en"


class Retriever(Protocol):
    def search(
        self, query: str, tour_id: str | None = None, top_k: int = 6
    ) -> list[KnowledgeEntry]: ...


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


class KeywordRetriever:
    """BM25-ish lexical retriever. Replace with a vector retriever in production."""

    def __init__(self, entries: list[KnowledgeEntry]) -> None:
        self._entries = entries
        self._doc_freq: dict[str, int] = {}
        for entry in entries:
            for token in _tokens(f"{entry.name_en} {entry.text} {' '.join(entry.tags)}"):
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1

    def search(
        self, query: str, tour_id: str | None = None, top_k: int = 6
    ) -> list[KnowledgeEntry]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        scored: list[tuple[float, KnowledgeEntry]] = []
        for entry in self._entries:
            if tour_id and entry.tour_id != tour_id:
                continue
            score = 0.0
            corpus = _tokens(f"{entry.name_en} {entry.text} {' '.join(entry.tags)}")
            for token in query_tokens:
                if token not in corpus:
                    continue
                n = sum(1 for e in self._entries if token in _tokens(f"{e.name_en} {e.text}"))
                idf = math.log(1 + (len(self._entries) + 1) / (n + 1))
                score += idf
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]


# Seed knowledge for the demo tour. Production data comes from catalog + Milvus.
SEED_ENTRIES: list[KnowledgeEntry] = [
    KnowledgeEntry(
        id="poi-tokyo-tower",
        tour_id="tour-tokyo",
        name_en="Tokyo Tower",
        text="Tokyo Tower is a communications and observation tower in Shiba Park, Tokyo, built in 1958. "
        "Standing 332.9 metres tall, it was inspired by the Eiffel Tower and is painted in international orange "
        "and white for air-safety regulations.",
        tags=("landmark", "tower", "tokyo"),
        t_begin_sec=10.0,
        t_end_sec=180.0,
    ),
    KnowledgeEntry(
        id="poi-hachiko",
        tour_id="tour-tokyo",
        name_en="Hachiko Statue",
        text="The Hachiko Statue sits outside Shibuya Station and commemorates Hachiko, an Akita dog who waited "
        "for his owner for nearly a decade. It is a popular meeting point.",
        tags=("landmark", "statue", "shibuya", "dog"),
        t_begin_sec=0.0,
        t_end_sec=90.0,
    ),
    KnowledgeEntry(
        id="poi-shibuya-crossing",
        tour_id="tour-tokyo",
        name_en="Shibuya Crossing",
        text="Shibuya Crossing, or the Shibuya Scramble, is one of the world's busiest pedestrian crossings, "
        "seeing up to 3,000 people cross at once during peak times.",
        tags=("landmark", "crossing", "shibuya", "street"),
        t_begin_sec=0.0,
        t_end_sec=120.0,
    ),
    KnowledgeEntry(
        id="poi-ramen",
        tour_id="tour-tokyo",
        name_en="Tokyo Ramen",
        text="Tokyo ramen is typically a soy-sauce (shoyu) based noodle soup with chashu pork, served with "
        "thin, curly noodles. Popular shops cluster around Ikebukuro and Shinjuku.",
        tags=("food", "ramen", "noodles", "tokyo"),
        t_begin_sec=0.0,
        t_end_sec=None,
    ),
    KnowledgeEntry(
        id="poi-eiffel",
        tour_id="tour-paris",
        name_en="Eiffel Tower",
        text="The Eiffel Tower was completed in 1889 for the World's Fair, standing 330 metres tall. Designed "
        "by Gustave Eiffel, it was the world's tallest structure until 1930.",
        tags=("landmark", "tower", "paris"),
        t_begin_sec=0.0,
        t_end_sec=None,
    ),
    KnowledgeEntry(
        id="poi-croissant",
        tour_id="tour-paris",
        name_en="Croissant",
        text="A croissant is a buttery, flaky French pastry. In Paris it is traditionally eaten for breakfast "
        "with coffee, straight from a neighbourhood boulangerie.",
        tags=("food", "pastry", "breakfast", "paris"),
        t_begin_sec=0.0,
        t_end_sec=None,
    ),
]

SUPPORTED_LANGUAGES = ("en", "fr", "de", "es", "ja", "zh")
