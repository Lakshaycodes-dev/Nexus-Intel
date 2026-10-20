"""Asynchronous TinyFish Search API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import (
    TINYFISH_API_KEY,
    TINYFISH_MAX_RESULTS,
    TINYFISH_SEARCH_METHOD,
    TINYFISH_SEARCH_URL,
    TINYFISH_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

_MOCK_URLS: tuple[str, ...] = (
    "https://stripe.com/pricing",
    "https://www.paddle.com/pricing",
    "https://www.chargebee.com/pricing",
)


class TinyFishSearchError(RuntimeError):
    """Raised when the TinyFish Search API cannot return results."""


def _extract_urls(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload] if payload.startswith(("http://", "https://")) else []

    if isinstance(payload, list):
        urls: list[str] = []
        for item in payload:
            urls.extend(_extract_urls(item))
        return urls

    if not isinstance(payload, dict):
        return []

    for key in ("results", "data", "items", "urls"):
        if key in payload:
            urls = _extract_urls(payload[key])
            if urls:
                return urls

    for key in ("url", "link", "href"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return [value]

    return []


def _dedupe(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _headers() -> dict[str, str]:
    if not TINYFISH_API_KEY:
        raise TinyFishSearchError(
            "TINYFISH_API_KEY is not set. Add it to .env or keep MOCK_MODE=True."
        )
    return {
        "X-API-Key": TINYFISH_API_KEY,
        "Authorization": f"Bearer {TINYFISH_API_KEY}",
        "Accept": "application/json",
    }


async def search_web(query: str, mock: bool) -> list[str]:
    """Search the web and return a de-duplicated list of result URLs."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    if mock:
        logger.info("Mock search for %r", query)
        return list(_MOCK_URLS[:TINYFISH_MAX_RESULTS])

    payload = {"query": query, "limit": TINYFISH_MAX_RESULTS}
    headers = _headers()

    try:
        async with httpx.AsyncClient(
            timeout=TINYFISH_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            if TINYFISH_SEARCH_METHOD == "GET":
                response = await client.get(
                    TINYFISH_SEARCH_URL,
                    params={"query": query},
                    headers=headers,
                )
            else:
                response = await client.post(
                    TINYFISH_SEARCH_URL,
                    json=payload,
                    headers=headers,
                )
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise TinyFishSearchError("TinyFish Search request timed out") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[:500]
        raise TinyFishSearchError(
            f"TinyFish Search returned HTTP {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.RequestError as exc:
        raise TinyFishSearchError(f"Could not reach TinyFish Search: {exc}") from exc
    except httpx.InvalidURL as exc:
        raise TinyFishSearchError(f"Invalid TinyFish Search URL: {exc}") from exc
    except ValueError as exc:
        raise TinyFishSearchError("TinyFish Search returned invalid JSON") from exc

    urls = _dedupe(_extract_urls(payload))[:TINYFISH_MAX_RESULTS]
    if not urls:
        logger.warning("TinyFish Search returned no URLs for %r", query)
    return urls
