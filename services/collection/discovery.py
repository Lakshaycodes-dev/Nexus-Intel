"""Static website discovery: robots.txt, sitemaps and internal links.

Playwright renders pages; discovery only needs HTTP because ``robots.txt`` and
sitemaps are static resources. The browser engine also reports internal links
from rendered DOM, which the pipeline merges in for JavaScript-heavy sites.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from typing import Iterable, Optional
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser

import httpx

from .classifier import classify_page
from .config import CollectionSettings
from .models import CATEGORY_PRIORITY, DiscoveredPage, PageCategory
from .url_utils import (
    UnsafeURLError,
    canonicalize_url,
    dedupe_urls,
    ensure_http_url,
    extract_links_from_html,
    is_internal_url,
    normalize_host,
    parse_sitemap,
    site_root,
    validate_public_url,
)

logger = logging.getLogger("nexus_intel.collection.discovery")

_SITEMAP_CANDIDATES = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemaps/sitemap.xml",
    "/wp-sitemap.xml",
)

_HIGH_PRIORITY_URL = re.compile(
    r"pricing|plans?|packages?|cost|changelog|release-notes|whats-new|"
    r"features?|product|announcements?|press|news",
    re.IGNORECASE,
)
_LOW_PRIORITY_URL = re.compile(
    r"privacy|terms|legal|cookie|gdpr|security|status|support/help|"
    r"login|signin|sign-in|signup|register|cart|checkout|account|"
    r"unsubscribe|sitemap|feed|rss",
    re.IGNORECASE,
)


class DiscoveryError(RuntimeError):
    """Raised when the seed site cannot be discovered at all."""


class RobotsPolicy:
    """Thin wrapper around ``RobotFileParser`` with a permissive fallback."""

    def __init__(self) -> None:
        self._parser: Optional[RobotFileParser] = None

    def parse(self, text: str) -> None:
        parser = RobotFileParser()
        parser.parse((text or "").splitlines())
        self._parser = parser

    def can_fetch(self, url: str) -> bool:
        if self._parser is None:
            return True
        try:
            return self._parser.can_fetch("*", url)
        except Exception:
            return True

    def crawl_delay(self) -> float:
        if self._parser is None:
            return 0.0
        try:
            return float(self._parser.crawl_delay("*") or 0.0)
        except Exception:
            return 0.0

    def sitemaps(self) -> list[str]:
        if self._parser is None:
            return []
        try:
            return list(self._parser.site_maps() or [])
        except Exception:
            return []


class SiteDiscovery:
    def __init__(
        self,
        settings: Optional[CollectionSettings] = None,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.settings = settings or CollectionSettings.from_env()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.request_timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": self.settings.user_agent, "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,*/*"},
        )
        self.robots = RobotsPolicy()

    async def __aenter__(self) -> "SiteDiscovery":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client and not self._client.is_closed:
            await self._client.aclose()

    async def _get(self, url: str, *, max_redirects: int = 6) -> Optional[httpx.Response]:
        current = url
        for _ in range(max_redirects + 1):
            try:
                await validate_public_url(
                    current, allow_private=self.settings.allow_private_hosts
                )
            except UnsafeURLError as exc:
                logger.warning("Blocked discovery request to %s: %s", current, exc)
                return None
            try:
                response = await self._client.get(current)
            except httpx.HTTPError as exc:
                logger.warning("Discovery request failed for %s: %s", current, exc)
                return None
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    return response
                next_url = canonicalize_url(current, location, keep_query=True)
                if not next_url:
                    return None
                current = next_url
                continue
            return response
        return None

    async def _load_robots(self, root: str) -> None:
        if not self.settings.respect_robots:
            return
        response = await self._get(urljoin(root + "/", "robots.txt"))
        if response is not None and response.status_code == 200:
            self.robots.parse(response.text)
            logger.info("Loaded robots.txt for %s", root)
        else:
            self.robots.parse("")

    async def _sitemap_locations(self, root: str, seed_url: str) -> list[DiscoveredPage]:
        candidates: list[str] = list(self.robots.sitemaps())
        for path in _SITEMAP_CANDIDATES:
            candidates.append(urljoin(root + "/", path.lstrip("/")))
        candidates = dedupe_urls(candidates)

        discovered: list[DiscoveredPage] = []
        seen_sitemaps: set[str] = set()
        queue: deque[tuple[str, int]] = deque((url, 0) for url in candidates)
        processed = 0
        while queue and processed < 10:
            url, depth = queue.popleft()
            if url in seen_sitemaps or depth > 2:
                continue
            seen_sitemaps.add(url)
            if not is_internal_url(url, normalize_host(urlsplit(root).hostname or "")):
                continue
            response = await self._get(url)
            if response is None or response.status_code != 200:
                continue
            content_type = response.headers.get("content-type", "")
            if "html" in content_type and "<urlset" not in response.text[:2000].lower():
                continue
            locations, is_index = parse_sitemap(response.text)
            if not locations:
                continue
            processed += 1
            if is_index:
                for loc in locations:
                    candidate = canonicalize_url(url, loc)
                    if candidate:
                        queue.append((candidate, depth + 1))
                continue
            for loc in locations:
                candidate = canonicalize_url(url, loc)
                if candidate:
                    discovered.append(
                        DiscoveredPage(
                            url=candidate,
                            source="sitemap",
                            depth=0,
                            priority=_priority_for_url(candidate),
                        )
                    )
            if len(discovered) >= self.settings.max_pages * 20:
                break
        return discovered

    async def _link_discovery(self, seed_url: str, root_host: str) -> list[DiscoveredPage]:
        discovered: list[DiscoveredPage] = []
        queue: deque[tuple[str, int]] = deque([(seed_url, 0)])
        visited: set[str] = set()
        fetches = 0
        while queue and fetches < max(3, self.settings.max_pages):
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            if depth > self.settings.max_depth:
                continue
            if not self.robots.can_fetch(url):
                logger.info("robots.txt disallows %s", url)
                continue
            response = await self._get(url)
            fetches += 1
            if response is None or response.status_code >= 400:
                continue
            if "html" not in response.headers.get("content-type", "").lower():
                continue
            html = response.text
            for raw in extract_links_from_html(html):
                candidate = canonicalize_url(url, raw)
                if not candidate or not is_internal_url(candidate, root_host):
                    continue
                if candidate in visited:
                    continue
                page = DiscoveredPage(
                    url=candidate,
                    source="link",
                    depth=depth + 1,
                    priority=_priority_for_url(candidate),
                )
                discovered.append(page)
                if depth + 1 < self.settings.max_depth:
                    queue.append((candidate, depth + 1))
        return discovered

    async def discover(self, seed_url: str, *, max_pages: Optional[int] = None) -> list[DiscoveredPage]:
        max_pages = max_pages or self.settings.max_pages
        seed = ensure_http_url(seed_url)
        seed = canonicalize_url(seed, seed, keep_query=False) or seed
        try:
            await validate_public_url(seed, allow_private=self.settings.allow_private_hosts)
        except UnsafeURLError as exc:
            raise DiscoveryError(str(exc)) from exc
        root = site_root(seed)
        root_host = normalize_host(urlsplit(root).hostname or "")

        await self._load_robots(root)
        sitemap_pages = await self._sitemap_locations(root, seed)
        link_pages = await self._link_discovery(seed, root_host)

        pages: list[DiscoveredPage] = [
            DiscoveredPage(url=seed, source="seed", depth=0, priority=_priority_for_url(seed))
        ]
        for page in sitemap_pages + link_pages:
            if _is_relevant_url(page.url):
                pages.append(page)

        unique: dict[str, DiscoveredPage] = {}
        for page in pages:
            if not is_internal_url(page.url, root_host):
                continue
            if self.settings.respect_robots and not self.robots.can_fetch(page.url):
                continue
            existing = unique.get(page.url)
            if existing is None or page.priority < existing.priority:
                unique[page.url] = page

        ordered = sorted(
            unique.values(),
            key=lambda page: (
                page.priority,
                0 if page.source == "seed" else 1,
                len(page.url),
            ),
        )
        if self.robots.crawl_delay() and self.settings.crawl_interval_seconds < self.robots.crawl_delay():
            self.settings = _replace_interval(self.settings, self.robots.crawl_delay())
        return ordered[:max_pages]


def _replace_interval(settings: CollectionSettings, interval: float) -> CollectionSettings:
    from dataclasses import replace

    return replace(settings, crawl_interval_seconds=interval)


def _is_relevant_url(url: str) -> bool:
    if _LOW_PRIORITY_URL.search(url):
        return False
    return True


def _priority_for_url(url: str) -> int:
    """Lower is crawled first; URL patterns only set the initial hint."""
    path = urlsplit(url).path or "/"
    if _LOW_PRIORITY_URL.search(path):
        return 80
    classification = classify_page(url)
    if classification.primary != PageCategory.GENERAL:
        return CATEGORY_PRIORITY[classification.primary]
    if _HIGH_PRIORITY_URL.search(path):
        return 5
    if path in {"", "/"}:
        return 2
    return 50


def merge_discovered_links(
    existing: Iterable[DiscoveredPage],
    links: Iterable[str],
    *,
    root_host: str,
    depth: int,
) -> list[DiscoveredPage]:
    """Add browser-discovered internal links that are not already scheduled."""
    known = {page.url for page in existing}
    additions: list[DiscoveredPage] = []
    for raw in links:
        candidate = canonicalize_url(f"https://{root_host}/", raw)
        if not candidate or candidate in known:
            continue
        if not is_internal_url(candidate, root_host):
            continue
        if _LOW_PRIORITY_URL.search(candidate):
            continue
        known.add(candidate)
        additions.append(
            DiscoveredPage(
                url=candidate,
                source="rendered_link",
                depth=depth + 1,
                priority=_priority_for_url(candidate),
            )
        )
    return additions
