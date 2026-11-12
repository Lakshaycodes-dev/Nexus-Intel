"""Collection orchestration: discovery -> Playwright -> extraction -> report.

The public entry point returns the path of the same Markdown report format the
old TinyFish orchestrator produced, so ``GeminiService`` and the API adapter do
not change. A JSON sidecar with structured data and tracking metadata is written
next to the report for auditability.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlsplit

from pydantic import ValidationError

from schemas.pydantic_schemas import TARGET_SCHEMAS, ExtractionTarget

from .browser import PlaywrightBrowserManager
from .classifier import classify_page
from .cleaning import clean_text
from .config import CollectionSettings
from .discovery import (
    DiscoveredPage,
    DiscoveryError,
    SiteDiscovery,
    merge_discovered_links,
)
from .domain_resolver import DomainResolutionError, resolve_official_domain
from .extractors import (
    extract_announcements,
    extract_features,
    extract_generic,
    extract_pricing,
    to_schema_payload,
)
from .mock_data import mock_domain_for_query, mock_snapshots
from .models import (
    CollectionResult,
    CrawlStats,
    PageCategory,
    PageClassification,
    PageExtraction,
    PageSnapshot,
    iso_now,
)
from .tracking import (
    InMemoryTrackingStore,
    TrackingConflictError,
    TrackingOutcome,
    TrackingService,
    TrackingStore,
    global_run_guard,
)
from .url_utils import (
    UnsafeURLError,
    canonicalize_url,
    ensure_http_url,
    is_internal_url,
    normalize_host,
    site_root,
)

logger = logging.getLogger("nexus_intel.collection.pipeline")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"

_PRICE_SIGNAL_RE = re.compile(r"[$€£¥₹]\s?\d|\bper\s+(?:month|year|seat|user)\b", re.IGNORECASE)
_FEATURE_SIGNAL_RE = re.compile(r"\bfeatures?\b|\bcapabilities\b", re.IGNORECASE)
_NEWS_SIGNAL_RE = re.compile(
    r"\b(?:changelog|release notes|what'?s new|announcement|now available|"
    r"launched|introduced|deprecated|version\s+\d)\b",
    re.IGNORECASE,
)


class CollectionError(RuntimeError):
    """Raised when the collection pipeline cannot produce a usable report."""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return slug or "report"


def _classify_snapshots(url: str, snapshots: Iterable[PageSnapshot]) -> PageClassification:
    best: Optional[PageSnapshot] = None
    for snapshot in snapshots:
        if snapshot.status != "success":
            continue
        if best is None or len(snapshot.text) > len(best.text):
            best = snapshot
    if best is None:
        return classify_page(url)
    return classify_page(
        best.final_url or url,
        title=best.title,
        meta_description=best.meta_description,
        headings=best.headings,
        text=best.text,
    )


def _validate_payload(target: ExtractionTarget, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate against the *existing* Pydantic contract; never raises."""
    schema_payload = to_schema_payload(payload, target.value)
    schema_cls = TARGET_SCHEMAS[target]
    try:
        schema_cls.model_validate(schema_payload)
        return payload, []
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()[:5]
        ]
        warning = f"structured {target.value} payload rejected by schema: " + "; ".join(errors)
        logger.warning(warning)
        payload.setdefault("warnings", [])
        payload["warnings"].append(warning)
        return payload, [warning]


def extract_page(
    url: str,
    snapshots: list[PageSnapshot],
    *,
    vendor: str = "",
    settings: Optional[CollectionSettings] = None,
) -> PageExtraction:
    classification = _classify_snapshots(url, snapshots)
    categories = list(classification.categories)
    successful = [snapshot for snapshot in snapshots if snapshot.status == "success"]
    combined_text = "\n".join(snapshot.text for snapshot in successful)
    warnings: list[str] = []

    pricing: dict[str, Any] = {}
    if PageCategory.PRICING in categories or _PRICE_SIGNAL_RE.search(combined_text):
        pricing, pricing_warnings = _validate_payload(
            ExtractionTarget.PRICING_MATRIX,
            extract_pricing(successful, vendor=vendor),
        )
        warnings.extend(pricing_warnings)

    features: dict[str, Any] = {}
    if (
        set(categories)
        & {PageCategory.FEATURES, PageCategory.PRODUCT, PageCategory.PRICING}
        or _FEATURE_SIGNAL_RE.search(combined_text)
    ):
        features, feature_warnings = _validate_payload(
            ExtractionTarget.FEATURE_COMPARISON,
            extract_features(successful, subject=vendor),
        )
        warnings.extend(feature_warnings)

    news: dict[str, Any] = {}
    if (
        set(categories) & {PageCategory.ANNOUNCEMENTS, PageCategory.CHANGELOG, PageCategory.BLOG}
        or _NEWS_SIGNAL_RE.search(combined_text)
    ):
        news, news_warnings = _validate_payload(
            ExtractionTarget.MARKET_NEWS,
            extract_announcements(successful, classification=classification),
        )
        warnings.extend(news_warnings)

    generic = extract_generic(successful, classification=classification)
    return PageExtraction(
        url=url,
        categories=categories,
        classification=classification,
        pricing=pricing,
        features=features,
        news=news,
        generic=generic,
        snapshots=snapshots,
        warnings=warnings,
    )


def _markdown_table(table: dict[str, Any]) -> str:
    headers = [str(header or "").strip() for header in table.get("headers") or []]
    rows = [[str(cell or "").strip() for cell in row] for row in table.get("rows") or []]
    if not headers and rows:
        headers = [f"Column {index + 1}" for index in range(len(rows[0]))]
    if not headers:
        return ""
    width = len(headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in range(width)) + " |"]
    for row in rows:
        cells = (row + [""] * width)[:width]
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    return "\n".join(lines)


def _plain_page_text(text: str) -> str:
    """Strip Markdown heading markers from page text.

    The downstream heuristic news parser treats *any* heading containing
    "updates/news" as a news section and then consumes every later heading. Page
    text is evidence, not report structure, so it must not masquerade as
    headings in the combined report.
    """
    lines = []
    for line in clean_text(text).split("\n"):
        lines.append(re.sub(r"^\s{0,3}#{1,6}\s+", "", line))
    return "\n".join(lines)


def _render_snapshot(snapshot: PageSnapshot) -> str:
    if snapshot.status != "success":
        return f"_Collection failed: {snapshot.error or snapshot.status}_"
    parts: list[str] = []
    if snapshot.title:
        parts.append(f"**Page title:** {snapshot.title}")
    if snapshot.meta_description:
        parts.append(f"**Meta description:** {snapshot.meta_description}")
    parts.append(f"**Billing state:** {snapshot.billing_state}")
    parts.append(f"**Retrieval method:** {snapshot.retrieval_method}")
    if snapshot.headings:
        parts.append("**Headings:** " + " / ".join(snapshot.headings[:12]))
    if snapshot.text:
        parts.append(_plain_page_text(snapshot.text))
    for table in snapshot.tables:
        rendered = _markdown_table(table)
        if rendered:
            parts.append(rendered)
    for group in snapshot.lists or []:
        heading = str(group.get("heading") or "").strip()
        items = [str(item).strip() for item in group.get("items") or [] if str(item).strip()]
        if not items:
            continue
        if heading:
            parts.append(f"**{heading}**")
        parts.extend(f"- {item}" for item in items[:80])
    return "\n\n".join(part for part in parts if part)


def render_report(
    *,
    query: str,
    competitor: str,
    pages: list[PageExtraction],
    stats: CrawlStats,
    mock: bool,
    warnings: list[str],
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    successful = [page for page in pages if any(s.status == "success" for s in page.snapshots)]
    # Metadata intentionally uses non-bullet lines: the downstream heuristic
    # news extractor scans bullet lines for years/report-like words.
    lines = [
        "# Market Intelligence Report",
        "",
        f"Query: {query}",
        f"Competitor: {competitor}",
        f"Generated: {generated_at}",
        f"Mock mode: {mock}",
        f"Sources with usable content: {len(successful)}/{len(pages)}",
        f"Pages crawled: {stats.crawled}; cached: {stats.reused_cached}; failed: {stats.failed}",
        f"Structured changes detected: {stats.changes}",
        "",
        "---",
        "",
    ]
    if warnings:
        lines.extend(["> Collection warnings: " + "; ".join(warnings[:10]), ""])

    for page in pages:
        has_success = any(snapshot.status == "success" for snapshot in page.snapshots)
        lines.append(f"## Source: {page.url}")
        lines.append("")
        lines.append(f"Status: {'success' if has_success else 'failed'}")
        lines.append(f"Categories: {', '.join(category.value for category in page.categories) or 'general'}")
        lines.append(f"Classification confidence: {page.classification.confidence:.2f}")
        billing_states = sorted(
            {snapshot.billing_state for snapshot in page.snapshots if snapshot.status == "success"}
        )
        if billing_states:
            lines.append(f"Billing states captured: {', '.join(billing_states)}")
        methods = sorted(
            {snapshot.retrieval_method for snapshot in page.snapshots if snapshot.status == "success"}
        )
        if methods:
            lines.append(f"Retrieval: {', '.join(methods)}")
        if page.warnings:
            lines.append(f"Extraction warnings: {'; '.join(page.warnings[:8])}")
        lines.append("")
        structured = {
            key: value
            for key, value in {
                "pricing": to_schema_payload(page.pricing, "pricing_matrix") if page.pricing else None,
                "features": to_schema_payload(page.features, "feature_comparison") if page.features else None,
                "announcements": to_schema_payload(page.news, "market_news") if page.news else None,
                "summary": page.generic,
            }.items()
            if value
        }
        lines.append("### Structured intelligence")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(structured, indent=2, ensure_ascii=False, default=str))
        lines.append("```")
        lines.append("")
        feature_categories = (page.features or {}).get("categories") or []
        if feature_categories:
            lines.append("### Extracted feature comparison")
            lines.append("")
            for category in feature_categories:
                features = category.get("features") or []
                if not features:
                    continue
                lines.append(f"#### {str(category.get('name') or 'Features')[:80]}")
                lines.append("")
                table = {
                    "headers": ["Feature", "Support", "Value"],
                    "rows": [
                        [
                            str(feature.get("name") or ""),
                            str(feature.get("support") or "unknown"),
                            str(feature.get("value") or ""),
                        ]
                        for feature in features
                    ],
                }
                lines.append(_markdown_table(table))
                lines.append("")
        lines.append("### Rendered content")
        lines.append("")
        for snapshot in page.snapshots:
            if len(page.snapshots) > 1:
                lines.append(f"#### Snapshot: {snapshot.billing_state}")
                lines.append("")
            lines.append(_render_snapshot(snapshot))
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_outputs(
    *,
    query: str,
    competitor: str,
    pages: list[PageExtraction],
    stats: CrawlStats,
    changes: list[dict[str, Any]],
    mock: bool,
    warnings: list[str],
    output_dir: Optional[Path] = None,
) -> CollectionResult:
    directory = output_dir or OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    report = render_report(
        query=query,
        competitor=competitor,
        pages=pages,
        stats=stats,
        mock=mock,
        warnings=warnings,
    )
    report_path = directory / f"{_slugify(query or competitor)}_market_intelligence.md"
    report_path.write_text(report, encoding="utf-8")

    result = CollectionResult(
        report_path=str(report_path),
        source_urls=[page.url for page in pages],
        pages=pages,
        stats=stats,
        changes=changes,
        warnings=warnings,
    )
    sidecar = directory / f"{_slugify(query or competitor)}_collection.json"
    sidecar.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return result


def _tracking_service(
    settings: CollectionSettings,
    store: Optional[TrackingStore],
) -> TrackingService:
    return TrackingService(store or InMemoryTrackingStore(), settings=settings)


async def _process_page_live(
    discovered: DiscoveredPage,
    *,
    competitor: str,
    settings: CollectionSettings,
    browser: PlaywrightBrowserManager,
    tracking: TrackingService,
    force: bool,
    stats: CrawlStats,
) -> tuple[Optional[PageExtraction], TrackingOutcome, list[str], str]:
    url = discovered.url
    decision = await tracking.decide(competitor, url, force=force)
    if not decision.should_crawl and decision.cached_snapshots:
        stats.reused_cached += 1
        extraction = extract_page(url, decision.cached_snapshots, vendor=competitor, settings=settings)
        outcome = await tracking.process(competitor, extraction, status_override="reused")
        return extraction, outcome, [], url

    preliminary = classify_page(url)
    snapshots = await browser.collect_page(
        url,
        [category.value for category in preliminary.categories],
        settings=settings,
    )
    if not any(snapshot.status == "success" for snapshot in snapshots):
        stats.failed += 1
        error = "; ".join(
            (snapshot.error or snapshot.status) for snapshot in snapshots
        )[:500]
        await tracking.store.upsert_page(
            competitor,
            url,
            {
                "page_category": preliminary.primary.value,
                "last_crawl_at": iso_now(),
                "crawl_status": "failed",
                "last_error": error,
            },
        )
        extraction = PageExtraction(
            url=url,
            categories=list(preliminary.categories),
            classification=preliminary,
            snapshots=snapshots,
            warnings=[f"collection failed: {error}"],
        )
        return extraction, TrackingOutcome("failed", "", "", []), [], error

    stats.crawled += 1
    stats.interactions += sum(len(snapshot.interactions) for snapshot in snapshots)
    extraction = extract_page(url, snapshots, vendor=competitor, settings=settings)
    outcome = await tracking.process(competitor, extraction, force=force)
    if outcome.status == "unchanged":
        stats.skipped_unchanged += 1
    stats.changes += len(outcome.changes)
    links: list[str] = []
    for snapshot in snapshots:
        links.extend(snapshot.links)
    return extraction, outcome, links, ""


async def _run_live(
    *,
    query: str,
    root_url: str,
    competitor: str,
    settings: CollectionSettings,
    tracking: TrackingService,
    force: bool,
) -> tuple[list[PageExtraction], list[dict[str, Any]], CrawlStats, list[str]]:
    stats = CrawlStats()
    warnings: list[str] = []
    try:
        async with SiteDiscovery(settings) as discovery:
            discovered = await discovery.discover(root_url)
            crawl_delay = discovery.robots.crawl_delay()
    except DiscoveryError as exc:
        raise CollectionError(str(exc)) from exc
    if crawl_delay > settings.crawl_interval_seconds:
        settings = replace(settings, crawl_interval_seconds=crawl_delay)
    stats.discovered = len(discovered)
    if not discovered:
        raise CollectionError("Website discovery returned no pages.")

    root_host = normalize_host(urlsplit(root_url).hostname or competitor)
    pending: list[DiscoveredPage] = list(discovered)
    seen: set[str] = {page.url for page in pending}
    pages: list[PageExtraction] = []
    changes: list[dict[str, Any]] = []
    lock = asyncio.Lock()
    processed = 0

    async with PlaywrightBrowserManager(settings) as browser:
        while pending and processed < settings.max_pages:
            batch = pending[: settings.concurrency]
            del pending[: settings.concurrency]
            tasks = [
                _process_page_live(
                    page,
                    competitor=competitor,
                    settings=settings,
                    browser=browser,
                    tracking=tracking,
                    force=force,
                    stats=stats,
                )
                for page in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            async with lock:
                for discovered_page, result in zip(batch, results):
                    processed += 1
                    if isinstance(result, Exception):
                        logger.exception("Page processing failed for %s", discovered_page.url)
                        stats.failed += 1
                        warnings.append(f"{discovered_page.url}: {type(result).__name__}")
                        continue
                    extraction, outcome, links, error = result
                    if extraction is not None:
                        pages.append(extraction)
                        if error:
                            warnings.append(f"{discovered_page.url}: {error}")
                    changes.extend(outcome.changes)
                    for addition in merge_discovered_links(
                        pending + discovered,
                        links,
                        root_host=root_host,
                        depth=discovered_page.depth,
                    ):
                        if addition.url not in seen and addition.priority <= 6:
                            seen.add(addition.url)
                            pending.append(addition)
                pending.sort(key=lambda page: (page.priority, len(page.url)))
            if pending and settings.crawl_interval_seconds:
                await asyncio.sleep(settings.crawl_interval_seconds)

    stats.finish()
    return pages, changes, stats, warnings


async def _run_mock(
    *,
    query: str,
    domain: str,
    settings: CollectionSettings,
    tracking: TrackingService,
    force: bool,
) -> tuple[list[PageExtraction], list[dict[str, Any]], CrawlStats, list[str]]:
    stats = CrawlStats()
    snapshots = mock_snapshots(domain)
    grouped: dict[str, list[PageSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.url, []).append(snapshot)
    stats.discovered = len(grouped)
    pages: list[PageExtraction] = []
    changes: list[dict[str, Any]] = []
    for url, page_snapshots in grouped.items():
        decision = await tracking.decide(domain, url, force=force)
        if not decision.should_crawl and decision.cached_snapshots:
            stats.reused_cached += 1
            extraction = extract_page(
                url, decision.cached_snapshots, vendor=domain, settings=settings
            )
            outcome = await tracking.process(domain, extraction, status_override="reused")
        else:
            extraction = extract_page(url, page_snapshots, vendor=domain, settings=settings)
            outcome = await tracking.process(domain, extraction, force=force)
            stats.crawled += 1
        if outcome.status == "unchanged":
            stats.skipped_unchanged += 1
        pages.append(extraction)
        changes.extend(outcome.changes)
        stats.changes += len(outcome.changes)
    stats.finish()
    return pages, changes, stats, []


async def collect_competitor(
    query: str,
    *,
    domain: Optional[str] = None,
    mock: bool = False,
    settings: Optional[CollectionSettings] = None,
    tracking_store: Optional[TrackingStore] = None,
    output_dir: Optional[Path] = None,
    force: bool = False,
) -> CollectionResult:
    settings = settings or CollectionSettings.from_env()
    tracking = _tracking_service(settings, tracking_store)
    guard = global_run_guard()

    resolved_domain = ""
    root_url = ""
    if domain:
        try:
            root_url = ensure_http_url(domain)
            root_url = site_root(root_url)
            resolved_domain = normalize_host(urlsplit(root_url).hostname or "")
        except UnsafeURLError as exc:
            raise CollectionError(str(exc)) from exc
    elif re.match(r"^https?://", (query or "").strip(), re.IGNORECASE):
        root_url = ensure_http_url(query.strip())
        resolved_domain = normalize_host(urlsplit(root_url).hostname or "")
    elif mock:
        resolved_domain = mock_domain_for_query(query)
        root_url = f"https://{resolved_domain}"
    else:
        try:
            resolved = await resolve_official_domain(query, settings)
        except DomainResolutionError as exc:
            raise CollectionError(str(exc)) from exc
        resolved_domain = resolved.domain
        root_url = resolved.url

    competitor = resolved_domain.removeprefix("www.")
    try:
        await guard.acquire(competitor)
    except TrackingConflictError as exc:
        raise CollectionError(str(exc)) from exc

    try:
        if mock:
            pages, changes, stats, warnings = await _run_mock(
                query=query,
                domain=resolved_domain,
                settings=settings,
                tracking=tracking,
                force=force,
            )
        else:
            pages, changes, stats, warnings = await _run_live(
                query=query,
                root_url=root_url,
                competitor=competitor,
                settings=settings,
                tracking=tracking,
                force=force,
            )

        result = _write_outputs(
            query=query,
            competitor=competitor,
            pages=pages,
            stats=stats,
            changes=changes,
            mock=mock,
            warnings=warnings,
            output_dir=output_dir,
        )
        if not any(
            snapshot.status == "success" for page in pages for snapshot in page.snapshots
        ):
            raise CollectionError(
                "No webpages could be collected successfully. "
                + ("; ".join(warnings[:5]) if warnings else "Check the target URL and browser installation.")
            )
        return result
    finally:
        await guard.release(competitor)


async def run_collection_pipeline(
    query: str,
    *,
    domain: Optional[str] = None,
    mock: bool = False,
    settings: Optional[CollectionSettings] = None,
    tracking_store: Optional[TrackingStore] = None,
    output_dir: Optional[Path] = None,
    force: bool = False,
) -> Path:
    result = await collect_competitor(
        query,
        domain=domain,
        mock=mock,
        settings=settings,
        tracking_store=tracking_store,
        output_dir=output_dir,
        force=force,
    )
    return Path(result.report_path)
