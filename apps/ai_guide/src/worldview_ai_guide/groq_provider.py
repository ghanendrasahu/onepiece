"""Groq LLM provider for the AI guide.

Uses Groq's free, fast inference API (OpenAI-compatible) for grounded answers.
Groq provides free API access with generous rate limits - perfect for dev.

Get a free API key at: https://console.groq.com/keys

Models available (free tier):
- llama-3.3-70b-versatile (recommended - best quality)
- llama-3.1-8b-instant (faster, lower quality)
- gemma2-9b-it (alternative)
"""

from __future__ import annotations

import logging
import os

import httpx

from .knowledge import KnowledgeEntry
from .provider import Answer, MockProvider

log = logging.getLogger(__name__)

# System prompt that grounds the AI guide in tour knowledge
SYSTEM_PROMPT = (
    "You are WorldView VR's AI World Guide, a knowledgeable and enthusiastic "
    "virtual travel companion.\n\n"
    "Your role is to answer questions about what the viewer sees in a 360° tour. "
    "You have access to a knowledge base of points of interest (POIs) for each "
    "tour.\n\n"
    "Guidelines:\n"
    "- Be conversational, warm, and informative\n"
    "- Use the provided context to ground your answers in facts\n"
    "- If you don't have specific information, say so honestly\n"
    "- Keep answers concise (2-4 sentences) unless asked for more\n"
    "- Mention specific details from the context\n"
    "- Answer in the same language the user asks in\n"
    "- Suggest related things to look at or ask about"
)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    """Groq-based LLM provider for fast, free inference.

    Uses Groq's OpenAI-compatible API with Llama 3.3 70B for
    high-quality, grounded answers at no cost.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._model = model
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def complete(
        self,
        query: str,
        context: list[KnowledgeEntry],
        lang: str,
    ) -> Answer:
        """Generate a grounded answer using Groq."""
        if not self._api_key:
            log.warning("No GROQ_API_KEY set, falling back to mock provider")
            return await MockProvider().complete(query, context, lang)

        # Build context string from retrieved entries
        context_parts = []
        for i, entry in enumerate(context, 1):
            tags_str = ", ".join(entry.tags) if entry.tags else "general"
            context_parts.append(
                f"[{i}] {entry.name_en} ({tags_str})\n{entry.text}"
            )
        context_str = (
            "\n\n".join(context_parts) if context_parts else "No context available."
        )

        user_message = f"""Tour context:
{context_str}

User question: {query}

Please answer the question based on the tour context above. Answer in {lang}."""

        try:
            client = await self._get_client()
            resp = await client.post(
                GROQ_API_URL,
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "top_p": 0.9,
                },
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            answer_text = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {})

            log.info(
                "Groq completion: model=%s tokens=%s",
                self._model,
                tokens_used.get("total_tokens", "unknown"),
            )

            # Build citations from context
            citations = []
            suggested_hotspots = []
            for entry in context[:3]:
                citations.append(
                    {
                        "poi_id": entry.id,
                        "type": "poi",
                        "name": entry.name_en,
                        "t_begin": entry.t_begin_sec,
                    }
                )
                suggested_hotspots.append(entry.id)

            return Answer(
                answer=answer_text,
                lang=lang,
                citations=citations,
                suggested_hotspots=suggested_hotspots,
            )

        except httpx.HTTPStatusError as e:
            log.error("Groq API error: %s %s", e.response.status_code, e.response.text[:200])
            return await MockProvider().complete(query, context, lang)
        except httpx.HTTPError as e:
            log.error("Groq HTTP error: %s", e)
            return await MockProvider().complete(query, context, lang)
        except Exception as e:
            log.error("Groq unexpected error: %s", e)
            return await MockProvider().complete(query, context, lang)

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


def build_groq_provider() -> GroqProvider | None:
    """Build a Groq provider if GROQ_API_KEY is set."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        log.info("GROQ_API_KEY not set, Groq provider unavailable (using mock)")
        return None
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return GroqProvider(api_key=api_key, model=model)
