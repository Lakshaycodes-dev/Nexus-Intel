"""Offline tests for the Playwright-collection pipeline building blocks.

No browser binaries, network, MongoDB, or Gemini credentials are required.
Mock snapshots exercise the same classifier/extractor/report code as live runs.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.orchestrator_service import parse_sources  # noqa: E402
from schemas.pydantic_schemas import (  # noqa: E402
    ExtractionTarget,
    TARGET_SCHEMAS,
)
from services.collection.classifier import classify_page  # noqa: E402
from services.collection.config import CollectionSettings  # noqa: E402
from services.collection.domain_resolver import (  # noqa: E402
    DomainResolutionError,
    SearchProvider,
    SearchResult,
    resolve_official_domain,
)
from services.collection.extractors import to_schema_payload  # noqa: E402
from services.collection.models import PageCategory  # noqa: E402
from services.collection.pipeline import (  # noqa: E402
    collect_competitor,
    run_collection_pipeline,
)
from services.collection.tracking import (  # noqa: E402
    InMemoryTrackingStore,
    TrackingService,
    detect_changes,
)
from services.collection.url_utils import (  # noqa: E402
    UnsafeURLError,
    canonicalize_url,
    check_host_syntax,
)


def _settings(**overrides) -> CollectionSettings:
    return replace(CollectionSettings.from_env(), **overrides)


def test_classifier_unknown_page_is_general():
    classification = classify_page("https://example.com/")
    assert classification.primary is PageCategory.GENERAL
    assert classification.categories == [PageCategory.GENERAL]


def test_ssrf_guard_blocks_internal_hosts():
    for host in ("localhost", "127.0.0.1", "10.1.2.3", "169.254.169.254", "service.internal"):
        with pytest.raises(UnsafeURLError):
            check_host_syntax(host)
    check_host_syntax("example.com")
    check_host_syntax("8.8.8.8")


def test_canonicalize_removes_tracking_params_and_assets():
    cleaned = canonicalize_url(
        "https://example.com/blog",
        "https://example.com/pricing?utm_source=news&ref=abc&tier=pro#plans",
        keep_query=True,
    )
    assert cleaned == "https://example.com/pricing?tier=pro"
    assert canonicalize_url("https://example.com/", "/logo.png") is None
    assert canonicalize_url("https://example.com/", "mailto:hi@example.com") is None


def test_mock_collection_writes_compatible_report_and_sidecar(tmp_path):
    result = asyncio.run(
        collect_competitor(
            "stripe pricing",
            domain="stripe.com",
            mock=True,
            settings=_settings(),
            output_dir=tmp_path,
        )
    )
    report = Path(result.report_path)
    assert report.exists()
    markdown = report.read_text(encoding="utf-8")
    sources = parse_sources(markdown)
    assert "https://stripe.com/pricing" in sources
    assert "https://stripe.com/features" in sources
    assert "https://stripe.com/changelog" in sources
    assert markdown.count("## Source:") == len(sources) >= 4
    assert "### Structured intelligence" in markdown

    sidecar = tmp_path / "stripe_pricing_collection.json"
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["stats"]["crawled"] >= 4
    assert any(page["pricing"] for page in payload["pages"])

    pricing_pages = [page for page in result.pages if page.pricing]
    assert pricing_pages
    schema = TARGET_SCHEMAS[ExtractionTarget.PRICING_MATRIX]
    schema.model_validate(to_schema_payload(pricing_pages[0].pricing, "pricing_matrix"))
    billing_states = {
        snapshot.billing_state
        for page in pricing_pages
        for snapshot in page.snapshots
        if snapshot.status == "success"
    }
    assert {"monthly", "annual"} <= billing_states


def test_run_collection_pipeline_returns_report_path(tmp_path):
    path = asyncio.run(
        run_collection_pipeline(
            "stripe pricing",
            domain="stripe.com",
            mock=True,
            settings=_settings(),
            output_dir=tmp_path,
        )
    )
    assert isinstance(path, Path)
    assert path.exists()
    assert path.read_text(encoding="utf-8").lstrip().startswith("# Market Intelligence Report")


def test_tracking_reuses_recent_snapshot_and_records_no_changes(tmp_path):
    async def scenario():
        settings = _settings(tracking_enabled=True, incremental_crawl=True, tracking_interval_hours=12)
        store = InMemoryTrackingStore()
        service = TrackingService(store, settings=settings)
        first = await collect_competitor(
            "stripe pricing",
            domain="stripe.com",
            mock=True,
            settings=settings,
            tracking_store=store,
            output_dir=tmp_path,
        )
        second = await collect_competitor(
            "stripe pricing",
            domain="stripe.com",
            mock=True,
            settings=settings,
            tracking_store=store,
            output_dir=tmp_path,
        )
        return first, second, store

    first, second, store = asyncio.run(scenario())
    assert first.stats.crawled >= 4
    assert second.stats.reused_cached == first.stats.discovered
    assert second.stats.changes == 0
    assert len(store.pages) >= 4
    cached_pricing = [page for page in second.pages if page.pricing][0]
    cached_states = {
        snapshot.billing_state for snapshot in cached_pricing.snapshots
    }
    assert {"monthly", "annual"} <= cached_states


def test_tracking_service_processes_payload_and_detects_changes():
    service = TrackingService(InMemoryTrackingStore(), settings=_settings(tracking_enabled=True))

    def make(price: float):
        from services.collection.models import (
            ExtractedPlan,
            PageClassification,
            PageExtraction,
            PageSnapshot,
        )

        classification = PageClassification(PageCategory.PRICING, [PageCategory.PRICING], 1.0)
        snapshot = PageSnapshot(
            url="https://acme.test/pricing",
            final_url="https://acme.test/pricing",
            title="Pricing",
            text=f"Pro ${price}/mo",
            billing_state="monthly",
        )
        return PageExtraction(
            url="https://acme.test/pricing",
            categories=[PageCategory.PRICING],
            classification=classification,
            pricing={
                "target": "pricing_matrix",
                "plans": [
                    {
                        "name": "Pro",
                        "price": price,
                        "price_display": f"${price}/mo",
                        "currency": "USD",
                        "billing_period": "monthly",
                        "included_features": ["Analytics"],
                    }
                ],
                "usage_based_rates": [],
            },
            snapshots=[snapshot],
        )

    async def scenario():
        first = await service.process("acme.test", make(49.0))
        second = await service.process("acme.test", make(59.0))
        return first, second

    first, second = asyncio.run(scenario())
    assert first.status == "new"
    kinds = {event["change_type"] for event in second.changes}
    assert "price_changed" in kinds


def test_detect_changes_ignores_layout_only_text():
    previous = {
        "pricing": {"plans": [{"name": "Pro", "price": 49.0, "billing_period": "monthly", "included_features": ["A"]}]},
        "features": {},
        "news": {},
    }
    current = json.loads(json.dumps(previous))
    events = detect_changes(previous, current, competitor="acme.test", url="https://acme.test/pricing")
    assert events == []

    current["pricing"]["plans"][0]["price"] = 59.0
    events = detect_changes(previous, current, competitor="acme.test", url="https://acme.test/pricing")
    assert [event["change_type"] for event in events] == ["price_changed"]


class _FakeSearch(SearchProvider):
    def __init__(self, results):
        self.results = results
        self.queries: list[str] = []

    async def search(self, query: str, max_results: int):
        self.queries.append(query)
        return self.results[:max_results]


def test_domain_resolver_accepts_verified_public_domain():
    provider = _FakeSearch([SearchResult(url="https://www.stripe.com/pricing", title="Stripe")])
    resolved = asyncio.run(
        resolve_official_domain("Stripe", settings=_settings(), provider=provider)
    )
    assert resolved.domain == "stripe.com"
    assert resolved.url == "https://www.stripe.com"
    assert provider.queries


def test_domain_resolver_rejects_aggregators():
    provider = _FakeSearch([SearchResult(url="https://en.wikipedia.org/wiki/Stripe", title="Stripe")])
    with pytest.raises(DomainResolutionError):
        asyncio.run(resolve_official_domain("Stripe", settings=_settings(), provider=provider))


def test_domain_resolver_requires_provider_for_company_names():
    with pytest.raises(DomainResolutionError):
        asyncio.run(resolve_official_domain("Stripe", settings=_settings()))
