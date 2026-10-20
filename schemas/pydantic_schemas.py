"""Strict Pydantic schemas for every extraction target.

The schemas in this module are the single source of truth for the JSON contract
enforced on Gemini. They are passed directly to the Google GenAI SDK as
``response_schema`` so the model is constrained to generate valid JSON, and they
are re-validated on the client side because the API-side constraint is a
best-effort guarantee, not a hard one.

Design rules
------------
* ``extra="forbid"`` everywhere: unexpected keys are a hard failure so that a
  layout change on the source page surfaces as a validation error instead of
  silently producing garbage.
* Deliberately *lenient* value coercion (``"$49/mo"`` -> ``49.0``): the model
  often echoes the raw display string, and a full strict-typed mode would turn
  harmless formatting noise into a failed extraction.
* Every target carries ``missing_fields`` and ``warnings`` so that partially
  successful extractions remain useful and auditable instead of being dropped.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

__all__ = [
    "ExtractionTarget",
    "SentimentLabel",
    "FeatureSupport",
    "BillingPeriod",
    "Money",
    "PlanTier",
    "UsageBasedRate",
    "FreeTier",
    "PricingMatrix",
    "FeatureItem",
    "FeatureCategory",
    "FeatureComparison",
    "NewsItem",
    "MarketNews",
    "AspectSentiment",
    "SentimentScore",
    "TARGET_SCHEMAS",
    "ExtractionModel",
]


# --------------------------------------------------------------------------- #
# Shared base
# --------------------------------------------------------------------------- #
class ExtractionModel(BaseModel):
    """Common configuration and contract shared by every extraction schema."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
        # Emit ``null`` explicitly so the model learns the full shape.
        json_schema_serialization_defaults_required=False,
    )

    missing_fields: Annotated[
        list[str],
        Field(
            description=(
                "Names of fields that the schema requires but that were NOT "
                "present in the source markdown. Use dotted paths, e.g. "
                "'plans[2].price'. Never guess a value to fill a gap."
            ),
            default_factory=list,
        ),
    ]

    warnings: Annotated[
        list[str],
        Field(
            description=(
                "Non-fatal issues encountered while parsing, e.g. "
                "'unrecognised table layout', 'date could not be parsed'."
            ),
            default_factory=list,
        ),
    ]


class ExtractionTarget(str, Enum):
    """Every artifact this pipeline can produce."""

    PRICING_MATRIX = "pricing_matrix"
    FEATURE_COMPARISON = "feature_comparison"
    MARKET_NEWS = "market_news"
    SENTIMENT_SCORE = "sentiment_score"


# --------------------------------------------------------------------------- #
# Primitives / value objects
# --------------------------------------------------------------------------- #
class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class FeatureSupport(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    NOT_SUPPORTED = "not_supported"
    UNKNOWN = "unknown"


class BillingPeriod(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"
    PER_TOKEN = "per_token"
    PER_REQUEST = "per_request"
    USAGE = "usage"
    OTHER = "other"


_MONEY_RE = re.compile(
    r"""(?P<currency>[$€£¥]|USD|EUR|GBP|JPY|INR|CHF|CAD|AUD)?\s*
        (?P<amount>-?\d[\d,_]*(?:\.\d+)?)""",
    re.VERBOSE | re.IGNORECASE,
)
_PERIOD_RE = re.compile(
    r"/\s*(mo(?:nth)?|yr|year|day|hr|hour|token|request|1k|1m|million)\b"
    r"|per\s+(month|year|day|hour|token|request|seat|user|million)\b"
    r"|(?:monthly|annually|yearly|hourly|daily)\b",
    re.IGNORECASE,
)

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR"}


def _coerce_money(value: Any) -> Optional[float]:
    """Turn ``"$1,299.50"``, ``"1299"``, ``1299`` ... into a ``float``.

    Returns ``None`` when no numeric amount can be recovered, which is the
    schema's signal for "not stated in the source".
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool is an int subclass; never a price
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = _MONEY_RE.search(text.replace("\u00a0", " "))
    if not match:
        return None
    try:
        return float(match.group("amount").replace(",", "").replace("_", ""))
    except ValueError:
        return None


def _coerce_percent(value: Any) -> Optional[float]:
    """``"45%"`` / ``0.45`` -> ``45.0`` (percent points, 0-100 scale)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
        if not match:
            return None
        number = float(match.group(0))
    # Heuristics: 0-1 fractions written with a % sign, or bare fractions.
    text = str(value)
    if "%" not in text and 0 < abs(number) <= 1:
        number *= 100
    return round(number, 6)


def _coerce_currency(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in _CURRENCY_SYMBOLS:
        return _CURRENCY_SYMBOLS[text]
    if len(text) <= 3 and text.isalpha():
        return text.upper()
    return None


_PERIOD_MAP = {
    "hour": BillingPeriod.HOURLY,
    "hr": BillingPeriod.HOURLY,
    "day": BillingPeriod.DAILY,
    "month": BillingPeriod.MONTHLY,
    "mo": BillingPeriod.MONTHLY,
    "year": BillingPeriod.YEARLY,
    "yr": BillingPeriod.YEARLY,
    "seat": BillingPeriod.MONTHLY,
    "user": BillingPeriod.MONTHLY,
    "token": BillingPeriod.PER_TOKEN,
    "request": BillingPeriod.PER_REQUEST,
    "1k": BillingPeriod.PER_TOKEN,
    "1m": BillingPeriod.PER_TOKEN,
    "million": BillingPeriod.PER_TOKEN,
}


def _coerce_billing_period(value: Any) -> BillingPeriod:
    if isinstance(value, BillingPeriod):
        return value
    if value is None:
        return BillingPeriod.OTHER
    text = str(value).strip().lower().replace("_", " ")
    for alias, period in (
        ("monthly", BillingPeriod.MONTHLY),
        ("month", BillingPeriod.MONTHLY),
        ("per month", BillingPeriod.MONTHLY),
        ("/month", BillingPeriod.MONTHLY),
        ("yearly", BillingPeriod.YEARLY),
        ("annual", BillingPeriod.YEARLY),
        ("annually", BillingPeriod.YEARLY),
        ("year", BillingPeriod.YEARLY),
        ("per year", BillingPeriod.YEARLY),
        ("hourly", BillingPeriod.HOURLY),
        ("daily", BillingPeriod.DAILY),
        ("one time", BillingPeriod.ONE_TIME),
        ("one-time", BillingPeriod.ONE_TIME),
        ("once", BillingPeriod.ONE_TIME),
        ("usage", BillingPeriod.USAGE),
        ("pay as you go", BillingPeriod.USAGE),
    ):
        if alias in text:
            return period
    match = _PERIOD_RE.search(text)
    if match:
        token = next((g for g in match.groups() if g), None)
        if token and token.lower() in _PERIOD_MAP:
            return _PERIOD_MAP[token.lower()]
    if text in _PERIOD_MAP:
        return _PERIOD_MAP[text]
    return BillingPeriod.OTHER


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d %B %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y-%m-%dT%H:%M:%S",
)


def _coerce_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    iso = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    if iso:
        try:
            return date.fromisoformat(iso.group(1))
        except ValueError:
            pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Target 1: PricingMatrix
# --------------------------------------------------------------------------- #
class Money(BaseModel):
    """A single monetary value plus the exact string shown in the source."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    amount: Optional[float] = Field(
        default=None,
        description="Numeric amount with no currency symbol, or null if absent.",
    )
    display: Optional[str] = Field(
        default=None,
        description="The exact pricing string as written in the source markdown.",
    )
    currency: Optional[str] = Field(
        default=None, description="ISO 4217 code inferred from the source, e.g. USD."
    )


class PlanTier(ExtractionModel):
    """One published plan / SKU from the pricing table."""

    name: str = Field(description="Exact plan name as written in the source.")
    price: Optional[float] = Field(
        default=None,
        description=(
            "Numeric price per billing period, currency symbol removed. "
            "null when the source says 'Contact sales' or omits the price."
        ),
    )
    price_display: Optional[str] = Field(
        default=None, description="Exact price cell text from the source."
    )
    currency: Optional[str] = Field(default=None, description="ISO 4217 code.")
    billing_period: BillingPeriod = Field(
        default=BillingPeriod.OTHER,
        description="How the price repeats: monthly, yearly, one_time, usage, other.",
    )
    seats: Optional[int] = Field(
        default=None, description="Seat/user count this price applies to, if stated."
    )
    included_features: list[str] = Field(
        default_factory=list,
        description="Feature bullets listed under this plan, verbatim.",
    )
    notes: Optional[str] = Field(
        default=None, description="Footnotes, limits or caveats for this plan."
    )


    @field_validator("price", mode="before")
    @classmethod
    def _normalize_price(cls, value: Any) -> Optional[float]:
        return _coerce_money(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> Optional[str]:
        return _coerce_currency(value)

    @field_validator("billing_period", mode="before")
    @classmethod
    def _normalize_period(cls, value: Any) -> BillingPeriod:
        return _coerce_billing_period(value)


class UsageBasedRate(ExtractionModel):
    """Metered / overage pricing row."""

    metric: str = Field(
        description="What is metered, e.g. 'input tokens', 'requests', 'GB'."
    )
    price: Optional[float] = Field(default=None, description="Numeric rate.")
    price_display: Optional[str] = Field(default=None, description="Exact source text.")
    currency: Optional[str] = Field(default=None, description="ISO 4217 code.")
    unit: str = Field(
        default="", description="Denominator, e.g. 'per 1M tokens', 'per request'."
    )
    billing_period: BillingPeriod = Field(default=BillingPeriod.USAGE)
    included_quantity: Optional[str] = Field(
        default=None, description="Free allowance before billing starts, if stated."
    )

    @field_validator("price", mode="before")
    @classmethod
    def _normalize_price(cls, value: Any) -> Optional[float]:
        return _coerce_money(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> Optional[str]:
        return _coerce_currency(value)

    @field_validator("billing_period", mode="before")
    @classmethod
    def _normalize_period(cls, value: Any) -> BillingPeriod:
        return _coerce_billing_period(value)


class FreeTier(ExtractionModel):
    """Free / trial offering if the source describes one."""

    available: Optional[bool] = Field(
        default=None, description="null when the source does not say."
    )
    description: Optional[str] = Field(default=None)
    limits: list[str] = Field(default_factory=list)


class PricingMatrix(ExtractionModel):
    """Structured pricing scraped from a vendor's pricing page."""

    target: Literal["pricing_matrix"] = "pricing_matrix"
    vendor: Optional[str] = Field(
        default=None, description="Vendor / product name the pricing belongs to."
    )
    source_url: Optional[str] = Field(default=None, description="Canonical page URL.")
    currency: Optional[str] = Field(
        default=None, description="Default ISO 4217 currency of the page."
    )
    plans: list[PlanTier] = Field(
        default_factory=list, description="Published plans, in source order."
    )
    usage_based_rates: list[UsageBasedRate] = Field(
        default_factory=list, description="Metered or overage rates."
    )
    free_tier: Optional[FreeTier] = Field(default=None)
    enterprise_note: Optional[str] = Field(
        default=None, description="Text about enterprise / custom pricing."
    )

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> Optional[str]:
        return _coerce_currency(value)

    @model_validator(mode="after")
    def _flag_missing_pricing(self) -> "PricingMatrix":
        if not self.plans and not self.usage_based_rates:
            if "plans" not in self.missing_fields:
                self.missing_fields.append("plans")
        return self


# --------------------------------------------------------------------------- #
# Target 2: FeatureComparison
# --------------------------------------------------------------------------- #
class FeatureItem(ExtractionModel):
    """A single capability row."""

    name: str = Field(description="Exact feature name from the source.")
    support: FeatureSupport = Field(
        default=FeatureSupport.UNKNOWN,
        description=(
            "supported / partial / not_supported. Use 'unknown' when the cell "
            "contains no explicit signal (blank, '—', '?')."
        ),
    )
    value: Optional[str] = Field(
        default=None,
        description="Quantified value when the cell is a number/limit, e.g. '10 GB'.",
    )
    notes: Optional[str] = Field(
        default=None, description="Footnote or qualifier attached to this cell."
    )

    @field_validator("support", mode="before")
    @classmethod
    def _normalize_support(cls, value: Any) -> Any:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            truth = {"yes": True, "y": True, "✓": True, "true": True, "supported": True,
                     "no": False, "n": False, "✗": False, "false": False, "not supported": False}
            if cleaned in truth:
                return "supported" if truth[cleaned] else "not_supported"
            aliases = {
                "partial": "partial", "limited": "partial", "basic": "partial",
                "add-on": "partial", "addon": "partial", "paid": "partial",
                "-": "unknown", "—": "unknown", "": "unknown", "n/a": "unknown",
                "?": "unknown", "unknown": "unknown",
            }
            return aliases.get(cleaned, cleaned)
        return value


class FeatureCategory(ExtractionModel):
    """A group of features, usually a table or a heading with bullets."""

    name: str = Field(description="Category heading as written in the source.")
    features: list[FeatureItem] = Field(default_factory=list)


class FeatureComparison(ExtractionModel):
    """Capability matrix for one or more compared products."""

    target: Literal["feature_comparison"] = "feature_comparison"
    subject: Optional[str] = Field(
        default=None, description="Product(s) being compared, verbatim."
    )
    source_url: Optional[str] = Field(default=None)
    categories: list[FeatureCategory] = Field(default_factory=list)

    @model_validator(mode="after")
    def _flag_missing_features(self) -> "FeatureComparison":
        if not self.categories:
            if "categories" not in self.missing_fields:
                self.missing_fields.append("categories")
        return self


# --------------------------------------------------------------------------- #
# Target 3: MarketNews
# --------------------------------------------------------------------------- #
class NewsItem(ExtractionModel):
    """One article / announcement discovered in the markdown."""

    title: str = Field(description="Exact headline from the source.")
    url: Optional[str] = Field(default=None, description="Absolute link if present.")
    source: Optional[str] = Field(default=None, description="Publisher or byline.")
    published_date: Optional[date] = Field(
        default=None, description="Publication date, null when unparseable."
    )
    published_date_raw: Optional[str] = Field(
        default=None, description="Raw date text exactly as written in the source."
    )
    summary: Optional[str] = Field(
        default=None, description="One or two sentence summary drawn from the source."
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Companies, products or people mentioned in the item.",
    )
    sentiment_hint: Optional[SentimentLabel] = Field(
        default=None,
        description="Explicit sentiment stated or clearly implied by the item.",
    )

    @field_validator("sentiment_hint", mode="before")
    @classmethod
    def _normalize_hint(cls, value: Any) -> Any:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            for token, label in (
                ("pos", "positive"), ("neg", "negative"), ("neu", "neutral"),
                ("mixed", "mixed"),
            ):
                if token in cleaned:
                    return label
        return value

    @model_validator(mode="before")
    @classmethod
    def _keep_unparsed_dates(cls, data: Any) -> Any:
        """Never lose the raw date: move unparseable strings aside."""
        if isinstance(data, dict):
            raw = data.get("published_date")
            parsed = _coerce_date(raw)
            if raw not in (None, "") and parsed is None:
                data.setdefault("published_date_raw", None)
                if not data.get("published_date_raw"):
                    data["published_date_raw"] = str(raw)
                data["published_date"] = None
            elif parsed is not None:
                data["published_date"] = parsed
                data.setdefault("published_date_raw", None)
        return data


class MarketNews(ExtractionModel):
    """News / announcements relevant to a market segment."""

    target: Literal["market_news"] = "market_news"
    market_segment: Optional[str] = Field(
        default=None, description="Segment the news covers, e.g. 'AI APIs'."
    )
    source_url: Optional[str] = Field(default=None)
    items: list[NewsItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _flag_missing_items(self) -> "MarketNews":
        if not self.items and "items" not in self.missing_fields:
            self.missing_fields.append("items")
        return self


# --------------------------------------------------------------------------- #
# Target 4: SentimentScore
# --------------------------------------------------------------------------- #
class AspectSentiment(ExtractionModel):
    """Sentiment for one sub-topic (pricing, support, latency, ...)."""

    aspect: str = Field(description="Sub-topic label.")
    score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Aspect sentiment from -1 (very negative) to 1 (very positive).",
    )
    rationale: Optional[str] = Field(
        default=None, description="Short justification grounded in the source text."
    )


class SentimentScore(ExtractionModel):
    """Aggregate sentiment of a subject described by the markdown."""

    target: Literal["sentiment_score"] = "sentiment_score"
    subject: Optional[str] = Field(
        default=None, description="What the sentiment is about, e.g. a brand name."
    )
    source_url: Optional[str] = Field(default=None)
    overall_score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Overall sentiment from -1 to 1. 0 when evidence is absent.",
    )
    label: SentimentLabel = Field(
        description="positive / neutral / negative / mixed.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How much evidence supports the score; low for sparse input.",
    )
    sample_size: int = Field(
        ge=0,
        default=0,
        description="Number of statements/sentences the judgement is based on.",
    )
    aspects: list[AspectSentiment] = Field(default_factory=list)

    @field_validator("overall_score", mode="before")
    @classmethod
    def _clamp_score(cls, value: Any) -> Any:
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:\.\d+)?", value)
            if not match:
                return 0.0
            value = float(match.group(0))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(-1.0, min(1.0, float(value)))
        return 0.0

    @field_validator("label", mode="before")
    @classmethod
    def _normalize_label(cls, value: Any) -> Any:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            aliases = {
                "pos": "positive",
                "optimistic": "positive",
                "favoured": "positive",
                "favored": "positive",
                "neg": "negative",
                "pessimistic": "negative",
                "neu": "neutral",
                "balanced": "neutral",
                "mixed/neutral": "mixed",
            }
            value = aliases.get(cleaned, cleaned)
        return value


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
TARGET_SCHEMAS: dict[ExtractionTarget, type[ExtractionModel]] = {
    ExtractionTarget.PRICING_MATRIX: PricingMatrix,
    ExtractionTarget.FEATURE_COMPARISON: FeatureComparison,
    ExtractionTarget.MARKET_NEWS: MarketNews,
    ExtractionTarget.SENTIMENT_SCORE: SentimentScore,
}
