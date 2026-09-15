from __future__ import annotations

import os
from typing import Any

import requests

from tools._travel import INTERNAL_ID_PATTERN, contains_sensitive_data


TAVILY_SEARCH_URL = "https://api.tavily.com/search"

ALLOWED_CATEGORIES = {
    "general",
    "attraction",
    "food",
    "hotel",
    "transport",
    "event",
}


def search_travel_info(
    query: str,
    destination: str = "",
    category: str = "general",
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Search current travel information using Tavily.

    Args:
        query: What the user wants to know.
        destination: City, region, or country related to the request.
        category: general, attraction, food, hotel, transport, or event.
        max_results: Number of web results, from 1 to 10.

    Returns:
        Structured travel search results for the chatbot.
    """

    query = query.strip()
    destination = destination.strip()
    category = category.strip().lower()

    if not query:
        return {
            "error": "missing_query",
            "message": "A search query is required.",
        }

    if category not in ALLOWED_CATEGORIES:
        return {
            "error": "invalid_category",
            "message": (
                f"Unsupported category '{category}'. "
                f"Use one of: {sorted(ALLOWED_CATEGORIES)}"
            ),
        }

    # Privacy boundary: internal IDs and secrets never leave the system.
    if INTERNAL_ID_PATTERN.search(f"{query} {destination}"):
        return {
            "error": "restricted_internal_identifier",
            "message": "Remove customer IDs, booking codes and tour IDs before searching the public web.",
        }
    if contains_sensitive_data(f"{query} {destination}"):
        return {
            "error": "restricted_sensitive_data",
            "message": "Remove card numbers, OTP, passwords and ID numbers before searching the public web.",
        }

    max_results = max(1, min(int(max_results), 10))

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "error": "missing_api_key",
            "message": "TAVILY_API_KEY is not configured.",
        }

    # Add travel context so Tavily searches specifically for travel information.
    search_parts = [query]

    if destination:
        search_parts.append(f"in {destination}")

    search_query = " ".join(search_parts)

    payload = {
        "query": search_query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_usage": True,
    }

    try:
        response = requests.post(
            TAVILY_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        return {
            "error": "tavily_request_failed",
            "message": str(exc),
        }

    results = []

    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
                "score": item.get("score"),
            }
        )

    return {
        "query": query,
        "search_query": search_query,
        "destination": destination or None,
        "category": category,
        "answer": data.get("answer"),
        "results": results,
        "result_count": len(results),
        "response_time": data.get("response_time"),
        "usage": data.get("usage"),
    }