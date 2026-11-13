"""Company-name -> official-domain resolution via a pluggable search provider.

Playwright is a browser automation tool, not a web search engine. This module is
deliberately separate from the browser engine: it only answers "which official
domain belongs to this company name?" and never crawls the site.

Two providers are supported, both optional and configured via environment:

* ``SEARCH_PROVIDER=gemini`` - Gemini Search Grounding through the installed
  ``google-genai`` SDK (the SDK surface is inspected defensively at runtime).
* ``SEARCH_PROVIDER=http`` - a generic JSON search API configured with
  ``SEARCH_API_URL`` / ``SEARCH_API_KEY`` (Serper-compatible response shapes are
  understood).

When neither is configured, callers receive a clear configuration error asking
for a website URL.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlsplit

import httpx

from .config import CollectionSettings
from .url_utils import (
    UnsafeURLError,
    canonicalize_url,
    check_host_syntax,
    clean_text_urls,
    ensure_http_url,
    normalize_host,
)

logger = logging.getLogger("nexus_intel.collection.discovery")

_AGGREGATOR_HOSTS = frozenset(
    {
        "wikipedia.org", "linkedin.com", "facebook.com", "twitter.com", "x.com",
        "instagram.com", "youtube.com", "crunchbase.com", "g2.com", "capterra.com",
        "glassdoor.com", "bloomberg.com", "reuters.com", "forbes.com", "techcrunch.com",
        "producthunt.com", "github.com", "reddit.com", "medium.com", "quora.com",
        "owler.com", "pitchbook.com", "zaubacorp.com", "dnb.com", "trustpilot.com",
        "apps.apple.com", "play.google.com", "amazon.com", "yelp.com",
    }
)
_LEGAL_SUFFIXES = {
    "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation",
    "gmbh", "ag", "plc", "sa", "sas", "bv", "pty", "co", "company", "group",
    "holdings", "technologies", "technology", "labs", "software", "systems",
}
_GENERIC_NAME_TOKENS = {
    "the", "a", "an", "and", "of", "for", "ai", "app", "cloud", "platform",
    "software", "solutions", "services", "global", "official", "website", "site",
}


class DomainResolutionError(RuntimeError):
    """Raised when no official domain can be resolved safely."""


@dataclass
class SearchResult:
    url: str
    title: str = ""
    snippet: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"url": self.url, "title": self.title, "snippet": self.snippet}


@dataclass
class ResolvedDomain:
    query: str
    domain: str
    url: str
    candidates: list[SearchResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "domain": self.domain,
            "url": self.url,
            "candidates": [c.to_dict() for c in self.candidates],
            "evidence": list(self.evidence),
        }


class SearchProvider:
    async def search(self, query: str, max_results: int) -> list[SearchResult]:  # pragma: no cover
        raise NotImplementedError


class GeminiGroundedSearch(SearchProvider):
    """Gemini Search Grounding provider (optional dependency)."""

    def __init__(self, *, api_key: Optional[str], model: str) -> None:
        self.api_key = api_key or ""
        self.model = model

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.api_key:
            raise DomainResolutionError(
                "SEARCH_PROVIDER=gemini requires GEMINI_API_KEY to be configured."
            )
        return await asyncio.to_thread(self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency is in requirements
            raise DomainResolutionError(
                "google-genai is not installed; install requirements to use Gemini search."
            ) from exc

        client = genai.Client(api_key=self.api_key)
        prompt = (
            f"Find the official website of the company named {query!r}. "
            "Answer with the official domain only, and do not choose directories, "
            "review sites, social media pages or similarly named companies."
        )
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.0,
        )
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        results: list[SearchResult] = []
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                uri = getattr(web, "uri", None) if web is not None else None
                title = getattr(web, "title", None) if web is not None else None
                if uri:
                    results.append(SearchResult(url=uri, title=title or ""))
        text = getattr(response, "text", None) or ""
        for raw in re.findall(r"https?://[^\s)\]\"'>]+", text):
            results.append(SearchResult(url=raw))
        # De-duplicate and cap.
        seen: set[str] = set()
        unique: list[SearchResult] = []
        for result in results:
            if result.url not in seen:
                seen.add(result.url)
                unique.append(result)
        return unique[:max_results]


class HttpSearchProvider(SearchProvider):
    """Generic JSON search API provider (Serper/Bing-style response shapes)."""

    def __init__(self, *, url: str, api_key: str = "", timeout: float = 20.0) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.url:
            raise DomainResolutionError(
                "SEARCH_PROVIDER=http requires SEARCH_API_URL to be configured."
            )
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"q": query, "query": query, "limit": max_results, "num": max_results}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise DomainResolutionError(f"Search provider request failed: {exc}") from exc
        except ValueError as exc:
            raise DomainResolutionError("Search provider returned invalid JSON.") from exc
        return _parse_http_results(body)[:max_results]


def _parse_http_results(body: Any) -> list[SearchResult]:
    raw_items: list[Any] = []
    if isinstance(body, list):
        raw_items = body
    elif isinstance(body, dict):
        for key in ("organic", "results", "data", "items", "web", "value"):
            value = body.get(key)
            if isinstance(value, list):
                raw_items = value
                break
        if not raw_items:
            for key in ("url", "link", "href"):
                if isinstance(body.get(key), str):
                    raw_items = [body]
                    break
    results: list[SearchResult] = []
    for item in raw_items:
        if isinstance(item, str):
            results.append(SearchResult(url=item))
        elif isinstance(item, dict):
            url = item.get("url") or item.get("link") or item.get("href")
            if not url:
                continue
            results.append(
                SearchResult(
                    url=str(url),
                    title=str(item.get("title") or item.get("name") or ""),
                    snippet=str(item.get("snippet") or item.get("description") or ""),
                )
            )
    return results


def provider_from_settings(
    settings: CollectionSettings,
    *,
    provider: Optional[SearchProvider] = None,
) -> Optional[SearchProvider]:
    if provider is not None:
        return provider
    name = (settings.search_provider or "").strip().lower()
    if name == "gemini":
        import os

        return GeminiGroundedSearch(
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            model=settings.gemini_model,
        )
    if name in {"http", "serper", "custom"}:
        return HttpSearchProvider(
            url=settings.search_api_url,
            api_key=settings.search_api_key,
            timeout=settings.request_timeout_seconds,
        )
    return None


def _name_tokens(name: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    return [
        token for token in tokens
        if token not in _LEGAL_SUFFIXES and token not in _GENERIC_NAME_TOKENS and len(token) > 1
    ]


def _is_aggregator(host: str) -> bool:
    return any(host == blocked or host.endswith("." + blocked) for blocked in _AGGREGATOR_HOSTS)


def _verify_candidate(result: SearchResult, name: str) -> Optional[tuple[str, str]]:
    try:
        url = ensure_http_url(result.url)
        host = normalize_host(urlsplit(url).hostname)
    except UnsafeURLError:
        return None
    if _is_aggregator(host):
        return None
    tokens = _name_tokens(name)
    host_labels = host.replace("www.", "").split(".")
    label_blob = "".join(host_labels[:-1]) if len(host_labels) > 1 else host_labels[0]
    if not tokens:
        return None
    matches = [token for token in tokens if token in label_blob]
    if not matches:
        # Accept only if the full normalised name appears in the title/snippet.
        blob = f"{result.title} {result.snippet}".lower()
        compact = re.sub(r"[^a-z0-9]+", "", name.lower())
        if not compact or compact not in re.sub(r"[^a-z0-9]+", "", blob):
            return None
        matches = tokens[:1]
    try:
        check_host_syntax(host)
    except UnsafeURLError:
        return None
    root = f"{urlsplit(url).scheme.lower()}://{host}"
    return host.removeprefix("www."), root


async def resolve_official_domain(
    company_name: str,
    settings: Optional[CollectionSettings] = None,
    *,
    provider: Optional[SearchProvider] = None,
) -> ResolvedDomain:
    """Resolve a company name to an official domain, never guessing blindly."""
    settings = settings or CollectionSettings.from_env()
    name = " ".join((company_name or "").split())
    if not name:
        raise DomainResolutionError("A company name or website URL is required.")

    # Already a URL / domain: validate and use it directly.
    if re.match(r"^https?://", name, re.IGNORECASE) or re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(?:/.*)?$", name, re.IGNORECASE):
        try:
            url = ensure_http_url(name)
            host = normalize_host(urlsplit(url).hostname)
            check_host_syntax(host, allow_private=settings.allow_private_hosts)
            root = f"{urlsplit(url).scheme.lower()}://{host}"
            return ResolvedDomain(
                query=name,
                domain=host.removeprefix("www."),
                url=root,
                evidence=["input was already a website URL/domain"],
            )
        except UnsafeURLError as exc:
            raise DomainResolutionError(str(exc)) from exc

    search = provider_from_settings(settings, provider=provider)
    if search is None:
        raise DomainResolutionError(
            "A company name was supplied but no search provider is configured. "
            "Provide a website URL or set SEARCH_PROVIDER (gemini/http) with its "
            "credentials (GEMINI_API_KEY or SEARCH_API_URL/SEARCH_API_KEY)."
        )

    query = f"{name} official website"
    try:
        results = await search.search(query, settings.search_max_results)
    except DomainResolutionError:
        raise
    except Exception as exc:  # provider-specific failure
        raise DomainResolutionError(f"Search provider failed: {type(exc).__name__}") from exc

    allowed = set(clean_text_urls([r.url for r in results]))
    candidates = [r for r in results if r.url in allowed]
    evidence: list[str] = []
    for result in candidates:
        verified = _verify_candidate(result, name)
        if verified:
            domain, root = verified
            evidence.append(
                f"search result {result.url!r} matched company name tokens"
            )
            return ResolvedDomain(
                query=name,
                domain=domain,
                url=root,
                candidates=candidates,
                evidence=evidence,
            )
        evidence.append(f"rejected candidate {result.url!r} (name/domain mismatch)")

    raise DomainResolutionError(
        "Could not verify an official domain for the supplied company name. "
        "Provide the website URL explicitly."
    )
