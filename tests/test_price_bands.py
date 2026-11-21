"""Regression tests for the shared retail price-band policy.

These cover the three layers that previously disagreed about what counts as a
price: the Pydantic contract, the deterministic collector extractors and the
frontend adapter. A bogus ``₹0`` / ``₹1`` / ``0.74`` must be dropped everywhere.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.pydantic_schemas import PricingMatrix  # noqa: E402
from services.collection.extractors import extract_pricing  # noqa: E402
from services.collection.models import PageSnapshot  # noqa: E402
from services.collection.url_utils import (  # noqa: E402
    canonicalize_crawl_url,
    is_catalog_url,
    is_editorial_url,
)
from utils.price_bands import (  # noqa: E402
    NO_PRICE_BANDS_MESSAGE,
    is_plausible_price,
)


# --------------------------------------------------------------------------- #
# Policy helper
# --------------------------------------------------------------------------- #
def test_sub_ten_amounts_are_never_prices():
    for amount in (0, 0.0, 1, 0.74, 0.88, 9.99):
        assert not is_plausible_price(amount), amount


def test_electronics_band_rejects_tiny_and_absurd_prices():
    assert is_plausible_price(49990, currency="INR", display="₹49,990", category="electronics")
    assert not is_plausible_price(199, currency="INR", display="₹199", category="electronics")
    assert not is_plausible_price(750000, currency="INR", display="₹7,50,000", category="electronics")


def test_general_inr_retail_keeps_genuine_low_prices():
    assert is_plausible_price(30, currency="INR", display="₹30", category="other")


# --------------------------------------------------------------------------- #
# Pydantic contract
# --------------------------------------------------------------------------- #
def test_schema_drops_zero_one_and_fractional_prices():
    model = PricingMatrix.model_validate(
        {
            "vendor": "Croma",
            "currency": "INR",
            "retail_category": "electronics",
            "plans": [
                {"name": "Counter", "price": 0, "price_display": "₹0"},
                {"name": "Badge", "price": 1, "price_display": "₹1"},
                {"name": "Blog stat", "price": 0.74, "price_display": "0.74"},
            ],
        }
    )
    assert [plan.price for plan in model.plans] == [None, None, None]
    assert [plan.price_display for plan in model.plans] == [None, None, None]
    assert model.pricing_status == "no_public_price_bands"
    assert model.pricing_status_note == NO_PRICE_BANDS_MESSAGE


def test_schema_keeps_valid_plan_prices():
    model = PricingMatrix.model_validate(
        {
            "vendor": "TinyFish",
            "currency": "USD",
            "plans": [
                {"name": "Starter", "price": 12.5, "price_display": "$12.50/mo"},
                {"name": "Pro", "price": 49, "price_display": "$49/mo"},
                {"name": "Scale", "price": 199, "price_display": "$199/mo"},
            ],
        }
    )
    assert [plan.price for plan in model.plans] == [12.5, 49.0, 199.0]
    assert model.pricing_status == "resolved"


def test_schema_electronics_band_rejects_implausible_inr_prices():
    model = PricingMatrix.model_validate(
        {
            "vendor": "Vijay Sales",
            "currency": "INR",
            "retail_category": "electronics",
            "plans": [
                {"name": "HDMI cable", "price": 199, "price_display": "₹199"},
                {"name": "55-inch QLED", "price": 54990, "price_display": "₹54,990"},
                {"name": "Commercial display", "price": 750000, "price_display": "₹7,50,000"},
            ],
        }
    )
    assert [plan.price for plan in model.plans] == [None, 54990.0, None]
    assert model.pricing_status == "resolved"


def test_schema_usage_rates_legitimately_sit_below_the_floor():
    model = PricingMatrix.model_validate(
        {
            "vendor": "TinyFish",
            "currency": "USD",
            "plans": [],
            "usage_based_rates": [
                {
                    "metric": "Input tokens",
                    "price": 0.5,
                    "price_display": "$0.50",
                    "unit": "per 1M tokens",
                }
            ],
        }
    )
    assert model.usage_based_rates[0].price == 0.5
    assert model.pricing_status == "resolved"


# --------------------------------------------------------------------------- #
# Deterministic extractor
# --------------------------------------------------------------------------- #
def _snapshot(url: str, title: str, *, text: str = "", tables=None) -> PageSnapshot:
    return PageSnapshot(
        url=url,
        final_url=url,
        title=title,
        text=text,
        tables=tables or [],
    )


def test_extractor_filters_storefront_counters_from_catalogue_table():
    snapshot = _snapshot(
        "https://www.croma.com/collections/televisions/c/1",
        "Televisions - Croma",
        tables=[
            {
                "headers": ["Product", "Price"],
                "rows": [
                    ["55-inch QLED", "₹54,990"],
                    ["Pagination", "₹1"],
                    ["Cart badge", "₹0"],
                ],
            }
        ],
    )
    result = extract_pricing([snapshot], vendor="Croma")
    assert result["retail_category"] == "electronics"
    assert [plan["price"] for plan in result["plans"]] == [54990.0]
    assert result["pricing_status"] == "resolved"
    assert any("rejected non-retail price" in warning for warning in result["warnings"])


def test_extractor_returns_clean_status_when_only_bogus_prices_found():
    snapshot = _snapshot(
        "https://www.croma.com/collections/televisions/c/1",
        "Televisions - Croma",
        text="Pagination ₹1\nCart badge ₹0",
    )
    result = extract_pricing([snapshot], vendor="Croma")
    assert result["plans"] == []
    assert result["pricing_status"] == "no_public_price_bands"
    assert result["pricing_status_note"] == NO_PRICE_BANDS_MESSAGE
    assert NO_PRICE_BANDS_MESSAGE in result["warnings"]


# --------------------------------------------------------------------------- #
# Discovery URL policy
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "url",
    [
        "https://www.croma.com/blog/best-tv-deals",
        "https://www.croma.com/about-us",
        "https://www.croma.com/press/quarterly-results",
        "https://www.croma.com/newsroom/expansion",
    ],
)
def test_editorial_urls_are_excluded(url: str):
    assert is_editorial_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.croma.com/collections/televisions/c/1",
        "https://www.vijaysales.com/category/air-conditioners",
        "https://www.reliancedigital.in/product/apple-iphone-15",
        "https://www.croma.com/p/123456",
    ],
)
def test_catalogue_urls_are_recognised(url: str):
    assert is_catalog_url(url)
    assert not is_editorial_url(url)


def test_crawl_canonicalisation_preserves_pagination_and_drops_tracking():
    cleaned = canonicalize_crawl_url(
        "https://www.croma.com",
        "/collections/televisions?page=2&utm_source=ad&sort=price-asc",
    )
    assert cleaned == "https://www.croma.com/collections/televisions?page=2&sort=price-asc"

    cleaned = canonicalize_crawl_url(
        "https://www.croma.com",
        "/collections/televisions?page=all&utm_campaign=spring",
    )
    assert cleaned == "https://www.croma.com/collections/televisions"
