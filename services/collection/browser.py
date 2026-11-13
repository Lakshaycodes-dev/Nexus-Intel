"""Asynchronous Playwright browser engine with a safe static fallback.

The browser is launched once per collection run, pages are fetched in isolated
contexts, and every context/page is closed in ``finally`` blocks so cancellation
cannot leak browser resources. Navigation is validated before it starts and the
final URL is re-validated after redirects.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import httpx

from .cleaning import (
    clean_html,
    clean_text,
    content_hash,
    extract_headings,
    extract_meta_description,
    html_to_text,
    parse_html_tables,
    stable_text,
    truncate,
)
from .config import CollectionSettings
from .interactions import interact_for_page
from .models import PageSnapshot
from .url_utils import (
    UnsafeURLError,
    canonicalize_url,
    check_host_syntax,
    extract_links_from_html,
    normalize_host,
    validate_public_url,
)

logger = logging.getLogger("nexus_intel.collection.browser")

try:  # pragma: no cover - exercised only when Playwright is installed
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:  # ImportError or binary-level failure
    async_playwright = None  # type: ignore[assignment]
    _PLAYWRIGHT_AVAILABLE = False


class PlaywrightUnavailableError(RuntimeError):
    """Raised when Playwright cannot be used and static fallback is disabled."""


_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

_EXTRACT_JS = r"""
() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const meta = document.querySelector('meta[name="description"]');
  const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4'))
    .map((el) => clean(el.innerText)).filter(Boolean).slice(0, 120);
  const tables = Array.from(document.querySelectorAll('table')).slice(0, 30).map((table) => {
    const rows = Array.from(table.querySelectorAll('tr')).map((tr) =>
      Array.from(tr.querySelectorAll('th,td')).map((cell) => clean(cell.innerText))
    ).filter((row) => row.some((cell) => cell));
    return {headers: rows[0] || [], rows: rows.slice(1)};
  }).filter((table) => table.rows.length > 0);
  const lists = Array.from(document.querySelectorAll('ul,ol')).slice(0, 25).map((list) => {
    let heading = '';
    let node = list.previousElementSibling;
    let hops = 0;
    while (node && hops < 4) {
      if (/^H[1-4]$/.test(node.tagName)) { heading = clean(node.innerText); break; }
      node = node.previousElementSibling; hops += 1;
    }
    if (!heading) {
      const section = list.closest('section,article');
      const h = section ? section.querySelector('h1,h2,h3,h4') : null;
      if (h) heading = clean(h.innerText);
    }
    const items = Array.from(list.querySelectorAll(':scope > li'))
      .map((li) => clean(li.innerText)).filter((text) => text.length > 2);
    return {heading, items: items.slice(0, 120)};
  }).filter((group) => group.items.length >= 2 && group.items.join(' ').length > 60);
  const links = Array.from(document.querySelectorAll('a[href]'))
    .map((a) => a.href).filter((href) => /^https?:/i.test(href));
  return {
    title: document.title || '',
    url: location.href,
    description: meta ? (meta.content || '') : '',
    text: document.body ? document.body.innerText : '',
    html: document.documentElement ? document.documentElement.outerHTML : '',
    headings,
    tables,
    lists,
    links,
  };
}
"""


def _snapshot_from_data(
    url: str,
    data: dict[str, Any],
    *,
    settings: CollectionSettings,
    billing_state: str,
    interactions: list[str],
    retrieval_method: str,
) -> PageSnapshot:
    text, _ = truncate(clean_text(data.get("text") or ""), settings.max_text_chars)
    html, _ = truncate(clean_html(data.get("html") or ""), settings.max_html_chars)
    links: list[str] = []
    seen: set[str] = set()
    for raw in data.get("links") or []:
        candidate = canonicalize_url(url, str(raw))
        if candidate and candidate not in seen:
            seen.add(candidate)
            links.append(candidate)
    tables = data.get("tables") or parse_html_tables(html)
    if not tables:
        tables = parse_html_tables(html)
    return PageSnapshot(
        url=url,
        final_url=url,
        title=clean_text(data.get("title") or ""),
        meta_description=clean_text(data.get("description") or extract_meta_description(html)),
        headings=[clean_text(h) for h in (data.get("headings") or extract_headings(html)) if clean_text(h)],
        text=text,
        html=html,
        links=links,
        tables=tables,
        lists=data.get("lists") or [],
        billing_state=billing_state,
        interactions=interactions,
        retrieval_method=retrieval_method,
    )


class PlaywrightBrowserManager:
    """One reusable browser; isolated context/page per target URL."""

    def __init__(self, settings: Optional[CollectionSettings] = None) -> None:
        self.settings = settings or CollectionSettings.from_env()
        self._playwright: Any = None
        self._browser: Any = None
        self._started = False
        self._static_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "PlaywrightBrowserManager":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def has_playwright(self) -> bool:
        return self._started and self._browser is not None

    async def start(self) -> None:
        if self._started:
            return
        if not _PLAYWRIGHT_AVAILABLE:
            logger.warning(
                "Playwright is not installed; using static HTTP fallback. "
                "Install with: pip install playwright && playwright install chromium"
            )
            return
        try:
            self._playwright = await async_playwright().start()
            browser_type = getattr(self._playwright, self.settings.browser_name)
            self._browser = await browser_type.launch(headless=self.settings.headless)
            self._started = True
            logger.info("Playwright %s browser started", self.settings.browser_name)
        except Exception as exc:
            logger.warning("Could not start Playwright (%s); static fallback enabled", exc)
            await self._stop_playwright()
            self._started = False

    async def _stop_playwright(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def close(self) -> None:
        await self._stop_playwright()
        self._started = False
        if self._static_client is not None and not self._static_client.is_closed:
            await self._static_client.aclose()
        self._static_client = None

    async def collect_page(
        self,
        url: str,
        categories: list[str],
        *,
        settings: Optional[CollectionSettings] = None,
    ) -> list[PageSnapshot]:
        settings = settings or self.settings
        try:
            await validate_public_url(url, allow_private=settings.allow_private_hosts)
        except UnsafeURLError as exc:
            return [
                PageSnapshot(
                    url=url,
                    final_url=url,
                    status="blocked",
                    error=str(exc),
                    retrieval_method="validation",
                )
            ]

        if self.has_playwright:
            snapshots = await self._collect_with_retry(url, categories, settings)
            if snapshots and any(s.status == "success" for s in snapshots):
                return snapshots
            if not settings.allow_static_fallback:
                return snapshots
            logger.info("Playwright produced no usable content for %s; trying static fallback", url)

        if not settings.allow_static_fallback:
            raise PlaywrightUnavailableError(
                "Playwright is not available. Install browser binaries with "
                "`playwright install chromium` or enable PLAYWRIGHT_ALLOW_STATIC_FALLBACK."
            )
        snapshot = await self._collect_static(url, settings)
        return [snapshot]

    async def _collect_with_retry(
        self,
        url: str,
        categories: list[str],
        settings: CollectionSettings,
        *,
        attempts: int = 2,
    ) -> list[PageSnapshot]:
        last: list[PageSnapshot] = []
        for attempt in range(1, attempts + 1):
            last = await self._collect_once(url, categories, settings)
            if any(snapshot.status == "success" for snapshot in last):
                return last
            if attempt < attempts:
                await asyncio.sleep(min(3.0, 1.0 * attempt))
        return last

    async def _collect_once(
        self,
        url: str,
        categories: list[str],
        settings: CollectionSettings,
    ) -> list[PageSnapshot]:
        context = None
        page = None
        snapshots: list[PageSnapshot] = []
        try:
            context = await self._browser.new_context(
                user_agent=settings.user_agent,
                viewport={"width": settings.viewport_width, "height": settings.viewport_height},
                locale="en-US",
                ignore_https_errors=False,
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(settings.navigation_timeout_ms)
            page.set_default_timeout(settings.navigation_timeout_ms)

            async def route_handler(route: Any) -> None:
                request = route.request
                try:
                    if settings.block_resources and request.resource_type in _BLOCKED_RESOURCE_TYPES:
                        await route.abort()
                        return
                    host = normalize_host(urlsplit(request.url).hostname)
                    check_host_syntax(host, allow_private=settings.allow_private_hosts)
                except Exception:
                    await route.abort()
                    return
                await route.continue_()

            await page.route("**/*", route_handler)
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.navigation_timeout_ms,
                referer=None,
            )
            final_url = page.url or url
            try:
                await validate_public_url(final_url, allow_private=settings.allow_private_hosts)
            except UnsafeURLError as exc:
                return [
                    PageSnapshot(
                        url=url,
                        final_url=final_url,
                        status="blocked",
                        error=str(exc),
                        retrieval_method="playwright",
                    )
                ]

            if response is not None and response.status >= 400:
                return [
                    PageSnapshot(
                        url=url,
                        final_url=final_url,
                        status="failed",
                        error=f"HTTP {response.status}",
                        retrieval_method="playwright",
                    )
                ]

            try:
                await page.wait_for_load_state("networkidle", timeout=min(settings.page_settle_timeout_ms, 8_000))
            except Exception:
                pass
            try:
                await page.wait_for_function(
                    "() => document.body && document.body.innerText.trim().length > 30",
                    timeout=settings.page_settle_timeout_ms,
                )
            except Exception:
                pass

            async def capture(state: str, actions: list[str]) -> None:
                data = await page.evaluate(_EXTRACT_JS)
                snapshot = _snapshot_from_data(
                    final_url,
                    data,
                    settings=settings,
                    billing_state=state,
                    interactions=actions,
                    retrieval_method="playwright",
                )
                snapshots.append(snapshot)

            actions, _ = await interact_for_page(
                page,
                settings,
                categories,
                on_snapshot=capture,
            )
            if not snapshots:
                await capture("default", actions)

            # Deduplicate identical states, preserving monthly/annual captures.
            unique: list[PageSnapshot] = []
            seen: set[tuple[str, str]] = set()
            for snapshot in snapshots:
                key = (snapshot.billing_state, content_hash(stable_text(snapshot.text), snapshot.title))
                if key in seen:
                    continue
                seen.add(key)
                unique.append(snapshot)
            return unique or snapshots
        except Exception as exc:
            logger.warning("Playwright navigation failed for %s: %s", url, exc)
            return [
                PageSnapshot(
                    url=url,
                    final_url=url,
                    status="failed",
                    error=f"{type(exc).__name__}: {str(exc)[:300]}",
                    retrieval_method="playwright",
                )
            ]
        finally:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

    async def _collect_static(self, url: str, settings: CollectionSettings) -> PageSnapshot:
        """HTTP-only fallback: no JavaScript, clearly marked in the report."""
        if self._static_client is None or self._static_client.is_closed:
            self._static_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.request_timeout_seconds),
                follow_redirects=False,
                headers={"User-Agent": settings.user_agent, "Accept": "text/html,*/*"},
            )
        current = url
        for _ in range(6):
            try:
                await validate_public_url(current, allow_private=settings.allow_private_hosts)
            except UnsafeURLError as exc:
                return PageSnapshot(
                    url=url, final_url=current, status="blocked", error=str(exc), retrieval_method="httpx_static"
                )
            try:
                response = await self._static_client.get(current)
            except httpx.HTTPError as exc:
                return PageSnapshot(
                    url=url,
                    final_url=current,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    retrieval_method="httpx_static",
                )
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                next_url = canonicalize_url(current, location, keep_query=True) if location else None
                if not next_url:
                    return PageSnapshot(
                        url=url, final_url=current, status="failed", error="invalid redirect", retrieval_method="httpx_static"
                    )
                current = next_url
                continue
            if response.status_code >= 400:
                return PageSnapshot(
                    url=url,
                    final_url=current,
                    status="failed",
                    error=f"HTTP {response.status_code}",
                    retrieval_method="httpx_static",
                )
            html = response.text
            text, _ = truncate(html_to_text(html), settings.max_text_chars)
            html, _ = truncate(clean_html(html), settings.max_html_chars)
            links = [
                candidate
                for raw in extract_links_from_html(html)
                if (candidate := canonicalize_url(current, raw))
            ]
            return PageSnapshot(
                url=url,
                final_url=current,
                title=clean_text(_extract_title(html)),
                meta_description=extract_meta_description(html),
                headings=extract_headings(html),
                text=text,
                html=html,
                links=list(dict.fromkeys(links)),
                tables=parse_html_tables(html),
                lists=_lists_from_text(text),
                billing_state="default",
                interactions=[],
                retrieval_method="httpx_static",
            )
        return PageSnapshot(
            url=url, final_url=current, status="failed", error="too many redirects", retrieval_method="httpx_static"
        )


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.IGNORECASE | re.DOTALL)
    return clean_text(re.sub(r"<[^>]+>", " ", match.group(1))) if match else ""


def _lists_from_text(text: str) -> list[dict[str, Any]]:
    """Crude heading + bullet grouping for the static fallback only."""
    groups: list[dict[str, Any]] = []
    heading = ""
    items: list[str] = []
    for line in (text or "").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 90 and not re.match(r"^[-*•]", stripped):
            if items:
                groups.append({"heading": heading, "items": items})
                items = []
            heading = stripped
        elif re.match(r"^[-*•]", stripped):
            item = re.sub(r"^[-*•]\s*", "", stripped).strip()
            if item:
                items.append(item)
    if items:
        groups.append({"heading": heading, "items": items})
    return [group for group in groups if len(group["items"]) >= 2]
