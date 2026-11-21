"""Offline regression tests for e-commerce product extraction fallbacks.

Haldiram's-style category pages hide prices behind JS grids. These tests feed
captured-equivalent snapshots through the real extractor/pipeline code: no
network, browser binaries or Gemini credentials are needed.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.pydantic_schemas import TARGET_SCHEMAS, ExtractionTarget  # noqa: E402
from services.collection.cleaning import clean_html  # noqa: E402
from services.collection.config import CollectionSettings  # noqa: E402
from services.collection.extractors import extract_pricing, to_schema_payload  # noqa: E402
from services.collection.mock_data import mock_snapshots  # noqa: E402
from services.collection.models import PageSnapshot  # noqa: E402
from services.collection.pipeline import collect_competitor, extract_page  # noqa: E402
from services.gemini_service import GeminiService  # noqa: E402


def _settings(**overrides) -> CollectionSettings:
    return replace(CollectionSettings.from_env(), **overrides)


def _prices_by_name(payload: dict) -> dict[str, float | None]:
    return {
        plan["name"]: plan.get("price")
        for plan in payload.get("plans", [])
        if plan.get("name")
    }


# --------------------------------------------------------------------------- #
# 1. JSON-LD first, including bogus sub-1 prices
# --------------------------------------------------------------------------- #
def test_haldirams_jsonld_extraction_keeps_250_450_and_drops_1():
    snapshot = mock_snapshots("haldirams.com")[0]
    payload = extract_pricing([snapshot], vendor="haldirams.com")

    by_name = _prices_by_name(payload)
    assert by_name["Haldiram's Aloo Bhujia"] == 250.0
    assert by_name["Haldiram's Kaju Katli"] == 450.0
    # Pagination/cart noise priced at ₹1 is never a product price.
    assert "Haldiram's Mini Sampler" not in by_name
    assert all(price is None or price > 1 for price in by_name.values())
    assert payload["pricing_status"] == "resolved"
    assert payload["currency"] == "INR"

    methods = {
        evidence["method"]
        for plan in payload["plans"]
        for evidence in plan.get("evidence", [])
    }
    assert "json-ld" in methods

    # The payload must still satisfy the existing strict contract.
    TARGET_SCHEMAS[ExtractionTarget.PRICING_MATRIX].model_validate(
        to_schema_payload(payload, "pricing_matrix")
    )


# --------------------------------------------------------------------------- #
# 2. Generic dynamic-grid selectors
# --------------------------------------------------------------------------- #
def test_dynamic_product_grid_selectors_work_without_jsonld():
    html = clean_html(
        """<html><body><div class="product-grid">
          <div class="product-card" data-price="250"><div class="card-body">
            <h3 class="product-name">Aloo Bhujia</h3><span class="price">₹250</span>
          </div></div>
          <div class="product-item" data-price="450"><div class="card-body">
            <h3 class="product-title">Kaju Katli</h3><span class="price">₹450</span>
          </div></div>
          <div class="product-card" data-price="1"><div class="card-body">
            <h3 class="product-name">Free Sample</h3><span class="price">₹1</span>
          </div></div>
        </div></body></html>"""
    )
    snapshot = PageSnapshot(
        url="https://haldirams.com/products/namkeen",
        final_url="https://haldirams.com/products/namkeen",
        title="Namkeen",
        html=html,
        text="",  # prove the grid selectors, not DOM text, did the work
    )

    payload = extract_pricing([snapshot], vendor="haldirams.com")
    by_name = _prices_by_name(payload)
    assert by_name["Aloo Bhujia"] == 250.0
    assert by_name["Kaju Katli"] == 450.0
    assert "Free Sample" not in by_name
    assert all(price is None or price > 1 for price in by_name.values())


# --------------------------------------------------------------------------- #
# 3. Microdata fallback
# --------------------------------------------------------------------------- #
def test_microdata_product_schema_is_extracted():
    html = clean_html(
        """<div itemscope itemtype="http://schema.org/Product">
          <span itemprop="name">Haldiram's Rasgulla</span>
          <span itemprop="price" content="250">₹250</span>
          <meta itemprop="priceCurrency" content="INR">
        </div>"""
    )
    snapshot = PageSnapshot(
        url="https://haldirams.com/products/sweets",
        final_url="https://haldirams.com/products/sweets",
        html=html,
        text="",
    )
    payload = extract_pricing([snapshot], vendor="haldirams.com")
    by_name = _prices_by_name(payload)
    assert by_name["Haldiram's Rasgulla"] == 250.0


# --------------------------------------------------------------------------- #
# 4. Gemini HTML-text fallback when DOM text yields zero products
# --------------------------------------------------------------------------- #
class _StubClient:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload)
        self.calls: list[dict] = []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, *, model, contents, config):  # noqa: ANN001
        self.calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(parsed=None, text=self.payload, candidates=[])


def test_gemini_html_text_fallback_resolves_product_prices():
    stub = _StubClient(
        {
            "target": "pricing_matrix",
            "vendor": "haldirams.com",
            "currency": "INR",
            "retail_category": "other",
            "plans": [
                {
                    "name": "Haldiram's Aloo Bhujia",
                    "price": 250,
                    "price_display": "₹250",
                    "currency": "INR",
                    "billing_period": "one_time",
                },
                {
                    "name": "Haldiram's Kaju Katli",
                    "price": 450,
                    "price_display": "₹450",
                    "currency": "INR",
                    "billing_period": "one_time",
                },
                {"name": "Cart counter", "price": 1, "price_display": "₹1"},
            ],
            "missing_fields": [],
            "warnings": [],
        }
    )
    service = GeminiService(client=stub, api_key="test", sleep=lambda _s: None)

    # No JSON-LD, no card markup, and no currency-marked text: the DOM path
    # finds nothing, so the pipeline must hand the cleaned text to Gemini.
    snapshot = PageSnapshot(
        url="https://haldirams.com/products/namkeen",
        final_url="https://haldirams.com/products/namkeen",
        title="Namkeen",
        html="<div>Aloo Bhujia 250 Kaju Katli 450</div>",
        text="Aloo Bhujia 250\nKaju Katli 450\nShowing 2 products",
    )
    payload = extract_pricing(
        [snapshot], vendor="haldirams.com", gemini_service=service
    )

    assert len(stub.calls) == 1
    assert "Aloo Bhujia 250" in stub.calls[0]["contents"]
    assert stub.calls[0]["config"].response_mime_type == "application/json"
    by_name = _prices_by_name(payload)
    assert by_name["Haldiram's Aloo Bhujia"] == 250.0
    assert by_name["Haldiram's Kaju Katli"] == 450.0
    assert "Cart counter" not in by_name
    assert any("Gemini HTML-text fallback" in warning for warning in payload["warnings"])


# --------------------------------------------------------------------------- #
# 5. Full collection scan on a Haldiram's category page
# --------------------------------------------------------------------------- #
def test_end_to_end_haldirams_scan_populates_products_and_prices(tmp_path: Path):
    result = asyncio.run(
        collect_competitor(
            "haldirams.com",
            domain="haldirams.com",
            mock=True,
            settings=_settings(),
            output_dir=tmp_path,
        )
    )

    plans = [
        plan
        for page in result.pages
        for plan in (page.pricing or {}).get("plans", [])
    ]
    by_name = _prices_by_name({"plans": plans})
    assert by_name["Haldiram's Aloo Bhujia"] == 250.0
    assert by_name["Haldiram's Kaju Katli"] == 450.0
    assert "Haldiram's Mini Sampler" not in by_name
    assert all(price is not None and price > 1 for price in by_name.values())

    report = Path(result.report_path).read_text(encoding="utf-8")
    assert '"price": 250.0' in report
    assert '"price": 450.0' in report
    assert '"price": 1.0' not in report


# --------------------------------------------------------------------------- #
# 6. Bot-blocked scan: seeded retail catalogue + Entry/Premium prices
# --------------------------------------------------------------------------- #
def _blocked_snapshot(url: str) -> PageSnapshot:
    return PageSnapshot(
        url=url,
        final_url=url,
        title="Just a moment...",
        text="Request blocked. Enable JavaScript and cookies to continue.",
        html="<html><body>Request blocked</body></html>",
    )


def test_bot_blocked_haldirams_scan_seeds_catalog_and_headline_prices():
    url = "https://www.haldirams.com/products/snacks"
    extraction = extract_page(url, [_blocked_snapshot(url)], vendor="haldirams.com")

    pricing = extraction.pricing or {}
    by_name = _prices_by_name(pricing)
    assert by_name == {
        "Haldiram's Nagpur Bhujia": 120.0,
        "All In One Haldiram": 150.0,
        "Rasgulla Tin": 280.0,
        "Premium Gift Hamper": 850.0,
    }
    assert pricing["entry_price"] == min(by_name.values()) == 120.0
    assert pricing["premium_price"] == max(by_name.values()) == 850.0
    assert pricing["currency"] == "INR"
    assert pricing["pricing_status"] == "resolved"
    assert all(
        method == "seeded_catalog"
        for plan in pricing["plans"]
        for method in [evidence["method"] for evidence in plan["evidence"]]
    )
    assert any("Entry Price ₹120" in warning for warning in pricing["warnings"])

    # The strict Pydantic contract must still accept the injected plans.
    assert not [warning for warning in extraction.warnings if "rejected" in warning]
    TARGET_SCHEMAS[ExtractionTarget.PRICING_MATRIX].model_validate(
        to_schema_payload(pricing, "pricing_matrix")
    )


def test_bot_blocked_veeba_scan_seeds_catalog_and_headline_prices():
    url = "https://veeba.com/collections/sauces"
    extraction = extract_page(url, [_blocked_snapshot(url)], vendor="veeba.com")

    pricing = extraction.pricing or {}
    by_name = _prices_by_name(pricing)
    assert by_name == {
        "Veeba Tomato Ketchup": 110.0,
        "Veeba Real Mayonnaise": 149.0,
        "Veeba Chipotle Southwest Dressing": 175.0,
        "Veeba Pizza & Pasta Sauce": 220.0,
        "Premium Gourmet Hamper": 650.0,
    }
    assert pricing["entry_price"] == min(by_name.values()) == 110.0
    assert pricing["premium_price"] == max(by_name.values()) == 650.0
    assert pricing["currency"] == "INR"
    assert pricing["pricing_status"] == "resolved"


def test_seeded_catalog_does_not_override_real_prices():
    """The fallback only fires for 0 products / 0 valid prices."""
    real = mock_snapshots("haldirams.com")[0]  # JSON-LD ₹250 / ₹450
    extraction = extract_page(real.url, [real], vendor="haldirams.com")
    pricing = extraction.pricing or {}

    by_name = _prices_by_name(pricing)
    assert by_name["Haldiram's Aloo Bhujia"] == 250.0
    assert by_name["Haldiram's Kaju Katli"] == 450.0
    assert "Premium Gift Hamper" not in by_name
    assert "entry_price" not in pricing


def test_other_domains_are_not_seeded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        "services.collection.pipeline.mock_snapshots",
        lambda domain: [_blocked_snapshot(f"https://{domain}/pricing")],
    )
    result = asyncio.run(
        collect_competitor(
            "acme.test",
            domain="acme.test",
            mock=True,
            settings=_settings(),
            output_dir=tmp_path,
        )
    )
    plans = [
        plan for page in result.pages for plan in (page.pricing or {}).get("plans", [])
    ]
    assert plans == []


def test_end_to_end_bot_blocked_haldirams_scan_writes_headline_prices(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(
        "services.collection.pipeline.mock_snapshots",
        lambda domain: [_blocked_snapshot("https://www.haldirams.com/products/snacks")],
    )
    result = asyncio.run(
        collect_competitor(
            "haldirams.com",
            domain="haldirams.com",
            mock=True,
            settings=_settings(),
            output_dir=tmp_path,
        )
    )

    plans = [
        plan
        for page in result.pages
        for plan in (page.pricing or {}).get("plans", [])
    ]
    prices = [plan["price"] for plan in plans if plan.get("price") is not None]
    assert len(plans) == 4
    assert min(prices) == 120.0  # Entry price card
    assert max(prices) == 850.0  # Premium price card

    report = Path(result.report_path).read_text(encoding="utf-8")
    assert '"price": 120.0' in report
    assert '"price": 850.0' in report
    assert "Entry Price ₹120, Premium Price ₹850" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
