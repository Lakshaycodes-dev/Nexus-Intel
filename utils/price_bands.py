"""Shared retail price-band guards.

The crawler, deterministic extractors, LLM prompt and Pydantic contracts all
need to agree on one question: *is this number a real retail price, or is it a
pagination counter / cart badge / filter slider value / blog statistic?*

Keeping the policy in one module prevents the layers from drifting apart. The
bands are intentionally conservative:

* no plan price below ``MIN_PLAN_PRICE`` (drops ``0``, ``1``, ``0.74`` ...);
* Indian electronics/appliances must sit inside ``INR_RETAIL_MIN`` ..
  ``INR_RETAIL_MAX`` (₹500 .. ₹5,00,000);
* other Indian retail verticals only need to clear the generic floor, so a
  genuine ₹30 snack pack is not misclassified as a bogus price.

Usage-based / metered rates (per-token, per-request) are *not* plan prices and
must not be passed through :func:`is_plausible_price`; they legitimately sit
below the retail floor.
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional

__all__ = [
    "MIN_PLAN_PRICE",
    "INR_RETAIL_MIN",
    "INR_RETAIL_MAX",
    "INR_GENERAL_MIN",
    "INR_GENERAL_MAX",
    "NO_PRICE_BANDS_MESSAGE",
    "detect_retail_category",
    "is_inr_context",
    "is_plausible_price",
    "price_band_for",
    "rejection_note",
]

# Any plan/SKU price below this is treated as UI noise, not money.
MIN_PLAN_PRICE = 10.0

# Indian consumer electronics & appliance retail band (₹500 .. ₹5,00,000).
INR_RETAIL_MIN = 500.0
INR_RETAIL_MAX = 500_000.0

# Other INR retail verticals (grocery, beauty, ...) still need a sanity floor.
INR_GENERAL_MIN = 10.0
INR_GENERAL_MAX = 5_000_000.0

NO_PRICE_BANDS_MESSAGE = "No public price bands resolved"

_INR_RE = re.compile(r"(?:₹|\bINR\b|\bRs\.?\s*\d)", re.IGNORECASE)

# Hosts of the retailers this product was built for. Matching the host is the
# strongest signal because it survives pages that never print "electronics".
_ELECTRONICS_DOMAIN_RE = re.compile(
    r"(?:croma|vijaysales|reliancedigital|reliance-?digital|bajajelectronics|"
    r"bajaj-?electronics|sathya|girias|paiinternational|vasanthandco|"
    r"adishwarestore|electronics?|appliances?|mobiles?|laptops?)",
    re.IGNORECASE,
)
_ELECTRONICS_RE = re.compile(
    r"\b(?:electronics?|mobiles?|smartphones?|laptops?|tvs?|televisions?|"
    r"air[-\s]?conditioners?|refrigerators?|washing[-\s]?machines?|"
    r"microwaves?|dishwashers?|chimneys?|water\s+purifiers?|cameras?|"
    r"headphones?|earbuds?|smartwatches?|tablets?|monitors?|printers?|"
    r"gaming|home\s+appliances?|kitchen\s+appliances?|consumer\s+electronics)\b",
    re.IGNORECASE,
)
_APPLIANCE_RE = re.compile(
    r"\b(?:appliances?|air[-\s]?conditioners?|refrigerators?|"
    r"washing[-\s]?machines?|microwaves?|dishwashers?|chimneys?|"
    r"water\s+purifiers?)\b",
    re.IGNORECASE,
)

# Blog/article statistics that frequently look like prices (0.74, 88%, ...).
_BLOG_STAT_RE = re.compile(
    r"\b(?:readers?|respondents?|visitors?|sur(?:vey|veys)|statistics?|stats?|"
    r"percent|percentage|share|conversion|traffic|growth|rating|reviews?|"
    r"votes?|likes?|followers?|subscribers?|discount|off)\b",
    re.IGNORECASE,
)


def is_inr_context(*values: Any) -> bool:
    """Return ``True`` when any supplied value carries an INR marker."""
    for value in values:
        if value is None:
            continue
        if _INR_RE.search(str(value)):
            return True
    return False


def detect_retail_category(*values: Any) -> str:
    """Classify the page as ``electronics``, ``appliances`` or ``other``.

    Accepts any mix of URL, title, vendor and page text. The check is
    deliberately cheap and deterministic so the schema, extractor and API
    adapter all reach the same band.
    """
    text = " ".join(str(value) for value in values if value)
    if not text.strip():
        return "other"
    if _ELECTRONICS_DOMAIN_RE.search(text):
        return "electronics"
    if _APPLIANCE_RE.search(text):
        return "appliances"
    if _ELECTRONICS_RE.search(text):
        return "electronics"
    return "other"


def price_band_for(
    category: str,
    *,
    currency: Any = None,
    display: Any = None,
) -> Optional[tuple[float, float]]:
    """Return the ``(min, max)`` band for an INR price, else ``None``."""
    if not is_inr_context(currency, display):
        return None
    normalized = (category or "other").strip().lower()
    if normalized in {"electronics", "appliances"}:
        return INR_RETAIL_MIN, INR_RETAIL_MAX
    return INR_GENERAL_MIN, INR_GENERAL_MAX


def is_plausible_price(
    amount: Any,
    *,
    currency: Any = None,
    display: Any = None,
    category: str = "other",
) -> bool:
    """Validate a *plan/SKU* price against the retail bands.

    ``None`` means "price not stated" and is considered acceptable; callers
    decide whether an unpriced plan should be kept (e.g. "Contact sales").
    Usage-based rates must bypass this helper.
    """
    if amount is None:
        return True
    if isinstance(amount, bool):
        return False
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(value):
        return False
    if value < MIN_PLAN_PRICE:
        return False
    band = price_band_for(category, currency=currency, display=display)
    if band is not None and not (band[0] <= value <= band[1]):
        return False
    # A bare single-digit / tiny fraction beside blog wording is never a price.
    if value < 10 and _BLOG_STAT_RE.search(str(display or "")):
        return False
    return True


def rejection_note(
    amount: Any,
    *,
    currency: Any = None,
    display: Any = None,
    category: str = "other",
) -> str:
    """Human-readable, audit-friendly reason for dropping a price."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        value = 0.0
    band = price_band_for(category, currency=currency, display=display)
    if band is not None:
        return (
            f"price {value:,.2f} outside the ₹{band[0]:,.0f}–₹{band[1]:,.0f} "
            f"{category} retail band"
        )
    if value < MIN_PLAN_PRICE:
        return (
            f"price {value:,.2f} rejected as a pagination/cart/blog counter, "
            "not a retail price"
        )
    return f"price {value:,.2f} rejected by the retail price guard"
