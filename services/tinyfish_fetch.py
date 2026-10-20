"""Asynchronous TinyFish Fetch API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import (
    TINYFISH_API_KEY,
    TINYFISH_FETCH_URL,
    TINYFISH_TIMEOUT_SECONDS,
)
from utils.navigation_helpers import normalize_url

logger = logging.getLogger(__name__)

_MOCK_MARKDOWN_TEMPLATE = """# Mock Competitor Pricing Page

> **MOCK DATA** - no request was sent to TinyFish.

Source: {url}
Browser session: {session_id}

## Plans

| Plan | Monthly price | Included seats | Notes |
| --- | ---: | ---: | --- |
| Starter | $0 | 1 | Basic dashboard and email support |
| Growth | $49 | 10 | Advanced analytics and priority support |
| Scale | $199 | 50 | SSO, audit logs, and dedicated support |

## Positioning

The mock competitor emphasizes transparent usage-based pricing, a generous free tier,
and annual discounts. Procurement teams should compare overage rates, contract terms,
and migration costs before selecting a plan.
"""


class TinyFishFetchError(RuntimeError):
    """Raised when the TinyFish Fetch API cannot return page content."""


def _extract_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()

    if isinstance(payload, list):
        for item in payload:
            text = _extract_text(item)
            if text:
                return text
        return ""

    if not isinstance(payload, dict):
        return ""

    for key in ("markdown", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for key in ("results", "data", "result"):
        if key in payload:
            text = _extract_text(payload[key])
            if text:
                return text

    return ""


def _extract_error(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""

    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        messages: list[str] = []
        for error in errors:
            if isinstance(error, dict):
                message = error.get("message") or error.get("error") or error.get("detail")
                messages.append(str(message or error))
            else:
                messages.append(str(error))
        return "; ".join(messages)[:500]

    for key in ("message", "error", "detail"):
        value = payload.get(key)
        if value:
            return str(value)[:500]

    return ""


def _headers() -> dict[str, str]:
    if not TINYFISH_API_KEY:
        raise TinyFishFetchError(
            "TINYFISH_API_KEY is not set. Add it to .env or keep MOCK_MODE=True."
        )
    return {
        "X-API-Key": TINYFISH_API_KEY,
        "Authorization": f"Bearer {TINYFISH_API_KEY}",
        "Accept": "application/json",
    }


async def fetch_markdown(
    url: str,
    mock: bool,
    session_id: str | None = None,
) -> str:
    """Fetch one URL and return Markdown.

    ``session_id`` is accepted for orchestrator compatibility, but the public
    TinyFish Fetch API is stateless and does not accept an Agent browser session.
    """

    url = normalize_url(url)

    if session_id is not None:
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("session_id must not be blank when provided")
        logger.warning(
            "Ignoring session_id for Fetch; TinyFish Fetch does not accept Agent sessions"
        )

    if mock:
        logger.info(
            "Mock fetch for %s using session %s",
            url,
            session_id or "fresh_page",
        )
        return _MOCK_MARKDOWN_TEMPLATE.format(
            url=url,
            session_id=session_id or "fresh_page",
        )

    headers = _headers()
    payload: dict[str, Any] = {
        "urls": [url],
        "format": "markdown",
        "purpose": "Competitor pricing, feature, product, and announcement research",
    }

    try:
        async with httpx.AsyncClient(
            timeout=TINYFISH_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            response = await client.post(
                TINYFISH_FETCH_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.TimeoutException as exc:
        raise TinyFishFetchError(f"TinyFish Fetch timed out for {url}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[:500]
        raise TinyFishFetchError(
            f"TinyFish Fetch returned HTTP {exc.response.status_code} for {url}: {detail}"
        ) from exc
    except httpx.RequestError as exc:
        raise TinyFishFetchError(f"Could not reach TinyFish Fetch for {url}: {exc}") from exc
    except httpx.InvalidURL as exc:
        raise TinyFishFetchError(f"Invalid URL for TinyFish Fetch: {exc}") from exc
    except ValueError as exc:
        raise TinyFishFetchError(f"TinyFish Fetch returned invalid JSON for {url}") from exc

    markdown = _extract_text(body)
    if not markdown:
        detail = _extract_error(body)
        suffix = f": {detail}" if detail else ""
        raise TinyFishFetchError(f"TinyFish Fetch returned no Markdown for {url}{suffix}")

    return markdown
