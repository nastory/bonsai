"""Tavily-backed web search and page-fetch tools for the retrieval agent.

Per the PRD: module generation grounds material in the public web via
Tavily, rather than the model's training data alone. Mirrors llm.py's
LLM_TEST_MODE convention: with it on, these return canned results instead
of making a real network call, so retrieval never costs Tavily credits
during day-to-day development or the test suite.
"""

import requests
from flask import current_app

SEARCH_URL = "https://api.tavily.com/search"
EXTRACT_URL = "https://api.tavily.com/extract"

REQUEST_TIMEOUT_SECONDS = 15


class RetrievalError(Exception):
    """Raised when a Tavily search or page-fetch call fails."""


def web_search(query: str, api_key: str, max_results: int = 5, search_depth: str = "basic") -> list[dict]:
    """Search the public web for material relevant to a query.

    Args:
        query: The search query.
        api_key: The learner's Tavily API key.
        max_results: Maximum number of results to return.
        search_depth: Tavily's "basic" (default, faster) or "advanced"
            (slower, more thorough) search mode. See UserSettings.deep_search_enabled.

    Returns:
        A list of {"title": str, "url": str, "content": str} dicts.

    Raises:
        RetrievalError: If the Tavily API call fails.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return [
            {
                "title": f"[MOCK] Result for '{query}'",
                "url": "https://example.com/mock-result",
                "content": f"[MOCK] Canned search content relevant to '{query}'.",
            }
        ]

    try:
        response = requests.post(
            SEARCH_URL,
            json={"api_key": api_key, "query": query, "max_results": max_results, "search_depth": search_depth},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RetrievalError(f"Tavily search failed: {e}") from e

    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in data.get("results", [])
    ]


def fetch_page(url: str, api_key: str) -> dict:
    """Fetch the full text content of a specific web page.

    Args:
        url: The page to fetch.
        api_key: The learner's Tavily API key.

    Returns:
        {"url": str, "content": str}.

    Raises:
        RetrievalError: If the Tavily API call fails, or returns no content.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return {"url": url, "content": f"[MOCK] Canned page content for {url}."}

    try:
        response = requests.post(
            EXTRACT_URL,
            json={"api_key": api_key, "urls": [url]},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RetrievalError(f"Tavily page fetch failed: {e}") from e

    results = data.get("results", [])
    if not results:
        raise RetrievalError(f"Tavily returned no content for {url}")
    return {"url": url, "content": results[0].get("raw_content", "")}


def image_search(query: str, api_key: str) -> list[dict]:
    """Search the public web for images relevant to a query.

    Uses the same Tavily /search endpoint as web_search(), with image
    inclusion turned on, rather than a separate endpoint - Tavily returns
    an "images" field alongside the normal text results when asked.

    Args:
        query: The image-search query.
        api_key: The learner's Tavily API key.

    Returns:
        A list of {"url": str, "description": str} dicts, best match first.

    Raises:
        RetrievalError: If the Tavily API call fails.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return [{"url": "https://example.com/mock-image.jpg", "description": f"[MOCK] Image for '{query}'"}]

    try:
        response = requests.post(
            SEARCH_URL,
            json={
                "api_key": api_key,
                "query": query,
                "max_results": 1,
                "include_images": True,
                "include_image_descriptions": True,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RetrievalError(f"Tavily image search failed: {e}") from e

    # Tavily can return a real "description" key with a null value (seen
    # live for some results, e.g. Facebook/Instagram-hosted images it
    # can't describe) - `or ""` catches that; a plain .get(key, "") default
    # only covers the key being absent entirely, not present-but-null.
    return [
        {"url": img.get("url") or "", "description": img.get("description") or ""}
        for img in data.get("images", [])
    ]
