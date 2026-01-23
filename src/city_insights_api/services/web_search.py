"""Wrapper around OpenAI's web_search tool."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WebSearchResult:
    query: str
    summary: str
    sources: List[str]


class WebSearchTool:
    """Lightweight helper invoking OpenAI's native web_search tool."""

    def __init__(
        self,
        *,
        model: str = "gpt-4.1-mini",
        max_output_tokens: int = 400,
        client: Optional[OpenAI] = None,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = client or OpenAI()

    def search(self, query: str) -> WebSearchResult:
        prompt = (
            "Utilise la recherche web native pour trouver des informations actuelles et fiables. "
            "Réponds en français avec un paragraphe synthétique suivi d'une courte liste de faits clés."
        )
        logger.debug("Executing web search for query: %s", query)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"{prompt}\nQuestion utilisateur : {query}",
                        }
                    ],
                }
            ],
            tools=[{"type": "web_search"}],
            max_output_tokens=self.max_output_tokens,
        )
        summary = self._extract_output_text(response).strip()
        sources = self._extract_sources(response)
        return WebSearchResult(query=query, summary=summary, sources=sources)

    def _extract_output_text(self, response: Any) -> str:
        try:
            data = response.model_dump()
        except AttributeError:
            data = {}

        texts: List[str] = []
        for block in data.get("output", []):
            for content in block.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if text:
                        texts.append(text)
        if texts:
            return "\n".join(texts)

        fallback = getattr(response, "output_text", None)
        if isinstance(fallback, str):
            return fallback
        return str(response)

    def _extract_sources(self, response: Any) -> List[str]:
        try:
            data = response.model_dump()
        except AttributeError:
            data = {}

        urls: List[str] = []

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                url = node.get("url")
                if isinstance(url, str):
                    urls.append(url)
                for value in node.values():
                    _walk(value)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(data)

        unique_urls: List[str] = []
        for url in urls:
            if url not in unique_urls:
                unique_urls.append(url)
        return unique_urls[:5]


__all__ = ["WebSearchTool", "WebSearchResult"]
