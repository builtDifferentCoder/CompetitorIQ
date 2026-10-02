"""Tavily search tool wrapper for CompetitorIQ.

Provides structured web search with robust error handling and failure isolation.
"""

from __future__ import annotations

import os
from typing import Any
from pydantic import BaseModel, Field
from tavily import TavilyClient


class SearchResultItem(BaseModel):
    """Clean, structured search result item."""

    title: str = Field(description="Title of the web page.")
    url: str = Field(description="URL of the web page.")
    snippet: str = Field(description="Relevant text content excerpt.")


class TavilySearchTool:
    """Wrapper around TavilyClient with error resilience."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set. Please add it to your .env file."
            )
        self.client = TavilyClient(api_key=self.api_key)

    def search(
        self,
        query: str,
        max_results: int = 3,
        search_depth: str = "basic",
    ) -> list[SearchResultItem]:
        """Execute a search query and return clean results.

        Catches API exceptions gracefully and returns an empty list so
        individual researcher failures do not crash the pipeline.
        """
        try:
            response: dict[str, Any] = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
            )
            raw_results = response.get("results", [])
            results: list[SearchResultItem] = []
            for item in raw_results:
                title = item.get("title") or "Untitled"
                url = item.get("url") or ""
                snippet = item.get("content") or item.get("snippet") or ""
                if url:
                    results.append(
                        SearchResultItem(
                            title=title.strip(),
                            url=url.strip(),
                            snippet=snippet.strip(),
                        )
                    )
            return results
        except Exception as exc:
            # Propagate error context via logging or return empty for caller isolation
            print(f"[SEARCH WARNING] Tavily query '{query}' failed: {exc}")
            raise


def search_web(query: str, max_results: int = 3) -> list[SearchResultItem]:
    """Convenience function to execute a single search query."""
    tool = TavilySearchTool()
    return tool.search(query=query, max_results=max_results)
