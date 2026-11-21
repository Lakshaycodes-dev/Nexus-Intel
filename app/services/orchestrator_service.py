"""Adapter between the HTTP API and the collection pipeline.

The pipeline's real entry point (see ``orchestrator.py``) is::

    async def run_pipeline(query: str, mock: bool = MOCK_MODE, *, domain=None) -> Path

It performs website discovery -> Playwright collection -> deterministic
extraction and returns the path of a combined Markdown report written to
``output/``. This module:

1. awaits ``run_pipeline`` (it is already async - the event loop is never
   blocked, and no extra thread is needed for the pipeline itself);
2. reads the Markdown report and runs the existing ``GeminiService`` extractors
   over it (they are synchronous, so they run in a worker thread via
   ``asyncio.to_thread``);
3. maps the strict Pydantic extraction schemas onto the frontend's
   ``CompetitorData`` contract (``domain, pricing, offsiteNews, capabilities,
   executionTimeSec``).

No existing module is modified - this is a pure adapter, and every function is
module-level so tests can monkeypatch ``run_pipeline``/``GeminiService``.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Import the *existing* pipeline entry point - now backed by Playwright.
from orchestrator import run_pipeline
from schemas.pydantic_schemas import TARGET_SCHEMAS, ExtractionTarget
from services.collection.pipeline import CollectionError
from services.gemini_service import GeminiService, ExtractionError
from utils import parser_helpers as ph
from utils.price_bands import detect_retail_category, is_plausible_price

from app import database
from app.errors import PipelineExecutionError
from app.schemas import AnalysisParameters

logger = logging.getLogger("nexus_intel.pipeline")

_SOURCE_HEADING_RE = re.compile(r"^## Source: (\S+)\s*$", re.MULTILINE)

_SENTIMENT_MAP = {
    "positive": "positive",
    "negative": "threat",
    "neutral": "neutral",
    "mixed": "neutral",
}


@dataclass
class ExtractionResult:
    """Outcome of one extraction target over the report Markdown."""

    target: str
    provenance: Optional[str] = None
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    model: Any = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "provenance": self.provenance,
            "missing_fields": list(self.missing_fields),
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass
class AnalysisOutcome:
    """Everything the API layer needs after one pipeline run."""

    report_path: str
    sources: list[str]
    extractions: list[ExtractionResult]
    data: dict[str, Any]
    execution_time_sec: float


def parse_sources(report_markdown: str) -> list[str]:
    """Extract the ``## Source: <url>`` sections written by the orchestrator."""
    return _SOURCE_HEADING_RE.findall(report_markdown or "")


def _provenance_for(warnings: list[str]) -> str:
    """Classify an extraction as LLM-backed or heuristic.

    The fallback builders in ``utils.parser_helpers`` tag their output with a
    warning that starts with ``fallback:``; anything else came from Gemini.
    """
    return (
        "fallback"
        if any(warning.lower().startswith("fallback:") for warning in warnings)
        else "gemini"
    )


def _run_extraction(
    service: GeminiService,
    target: ExtractionTarget,
    markdown: str,
    source_url: Optional[str],
) -> ExtractionResult:
    """Run one extraction target, degrading like ``GeminiService`` itself.

    ``GeminiService.extract`` already falls back to the heuristic extractors
    when the LLM is unavailable; this adds a last-resort guard so a fallback
    failure for one target never sinks the whole analysis.
    """
    schema_cls = TARGET_SCHEMAS[target]
    try:
        instance = service.extract(target, markdown, source_url=source_url)
    except (ExtractionError, ValueError) as exc:
        logger.warning("Extraction %s failed: %s", target.value, type(exc).__name__)
        return ExtractionResult(target=target.value, error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected extraction failure for %s", target.value)
        return ExtractionResult(target=target.value, error=type(exc).__name__)

    warnings = list(getattr(instance, "warnings", []) or [])
    return ExtractionResult(
        target=target.value,
        provenance=_provenance_for(warnings),
        missing_fields=list(getattr(instance, "missing_fields", []) or []),
        warnings=warnings,
        error=None,
        model=instance,
    )


def extract_structured_data(
    report_markdown: str,
    parameters: AnalysisParameters,
    source_url: Optional[str] = None,
    service: Optional[GeminiService] = None,
) -> list[ExtractionResult]:
    """Synchronous extraction pass (run inside ``asyncio.to_thread``).

    Only the targets enabled by the request's feature flags are executed.
    """
    service = service or GeminiService()
    targets: list[ExtractionTarget] = []
    if parameters.pricing_tiers:
        targets.append(ExtractionTarget.PRICING_MATRIX)
    if parameters.feature_accordions:
        targets.append(ExtractionTarget.FEATURE_COMPARISON)
    if parameters.offsite_mentions:
        targets.append(ExtractionTarget.MARKET_NEWS)

    return [
        _run_extraction(service, target, report_markdown, source_url)
        for target in targets
    ]


def _model_dump(instance: Any) -> dict[str, Any]:
    if instance is None:
        return {}
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    return dict(instance)


def _money_display(*values: Any) -> str:
    for value in values:
        if value:
            return str(value)
    return ""


_MONEY_IN_TEXT_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _display_amount(display: str) -> Optional[float]:
    """Best-effort numeric value from a price cell (``₹49,990`` -> 49990)."""
    match = _MONEY_IN_TEXT_RE.search(display or "")
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:  # pragma: no cover - regex guarantees a number
        return None


def _map_pricing(pricing_model: Any) -> list[dict[str, Any]]:
    """PricingMatrix -> frontend ``pricing`` rows.

    Monthly and annual snapshots are merged into one row per tier so the
    frontend receives both prices instead of duplicate plans. The heuristic
    fallback parser can emit non-enum ``billing_period`` values (e.g. the raw
    price cell), so the display text is also inspected.

    This is a final defence-in-depth layer: even if an older extractor or a
    malformed model slips a ``₹0`` / ``₹1`` / blog statistic through, the API
    response never exposes it as a plan price.
    """
    dump = _model_dump(pricing_model)
    category = dump.get("retail_category") or detect_retail_category(
        dump.get("vendor"), dump.get("source_url")
    )
    default_currency = dump.get("currency")
    rows: dict[str, dict[str, Any]] = {}
    for plan in dump.get("plans") or []:
        raw_display = _money_display(plan.get("price_display"), plan.get("price"))
        amount = plan.get("price")
        if amount is None:
            amount = _display_amount(raw_display)
        # "Contact sales" has no number and is still a valid, unpriced plan.
        if amount is not None and not is_plausible_price(
            amount,
            currency=plan.get("currency") or default_currency,
            display=raw_display,
            category=category,
        ):
            continue
        if not raw_display:
            continue
        display = raw_display
        billing = (plan.get("billing_period") or "").lower()
        annual = billing in {"annual", "yearly"} or bool(
            re.search(r"/\s*(?:yr|year)\b|per\s+year|annually", str(display), re.IGNORECASE)
        )

        name = plan.get("name") or "Unnamed tier"
        row = rows.setdefault(
            str(name).strip().lower(),
            {"tier": name, "monthly": "", "annual": "", "features": []},
        )
        if annual:
            row["annual"] = display
        else:
            row["monthly"] = display

        # The fallback parser may echo the price/seats cells into
        # ``included_features``; drop entries identical to the price display.
        for feature in plan.get("included_features") or []:
            text = str(feature).strip()
            if not text or text == display:
                continue
            if text not in row["features"]:
                row["features"].append(text)
    return list(rows.values())


def _map_news(news_model: Any) -> list[dict[str, Any]]:
    """MarketNews -> frontend ``offsiteNews`` rows."""
    dump = _model_dump(news_model)
    rows: list[dict[str, Any]] = []
    for item in dump.get("items") or []:
        hint = (item.get("sentiment_hint") or "neutral").lower()
        rows.append(
            {
                "title": item.get("title") or "Untitled mention",
                "source": item.get("source") or "unknown",
                "url": item.get("url"),
                "sentiment": _SENTIMENT_MAP.get(hint, "neutral"),
            }
        )
    return rows


def _map_capabilities(
    features_model: Any,
    *,
    plan_names: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """FeatureComparison -> frontend ``capabilities`` rows.

    The frontend compares "traditional scraper" vs "Nexus-Intel"; anything the
    pipeline actually extracted is marked as handled by Nexus-Intel. Pricing
    tables can be misread as feature tables by the heuristic fallback, so plan
    names are filtered out.
    """
    dump = _model_dump(features_model)
    rows: list[dict[str, Any]] = []
    excluded = plan_names or set()
    seen: set[str] = set()
    for category in dump.get("categories") or []:
        for feature in category.get("features") or []:
            name = feature.get("name")
            if not name:
                continue
            key = str(name).strip().lower()
            if key in excluded or key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "name": name,
                    "traditionalScraper": False,
                    "nexusIntel": True,
                }
            )
    return rows


def build_competitor_data(
    domain: str,
    extractions: list[ExtractionResult],
    execution_time_sec: float,
) -> dict[str, Any]:
    """Assemble the ``CompetitorData`` payload validated by the frontend."""
    pricing: list[dict[str, Any]] = []
    offsite_news: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    provenance: dict[str, str] = {}
    plan_names: set[str] = set()

    for result in extractions:
        if result.model is None:
            continue
        if result.provenance:
            provenance[result.target] = result.provenance
        if result.target == ExtractionTarget.PRICING_MATRIX.value:
            pricing = _map_pricing(result.model)
            plan_names = {row["tier"].strip().lower() for row in pricing if row.get("tier")}
        elif result.target == ExtractionTarget.MARKET_NEWS.value:
            offsite_news = _map_news(result.model)

    for result in extractions:
        if result.model is None:
            continue
        if result.target == ExtractionTarget.FEATURE_COMPARISON.value:
            capabilities = _map_capabilities(result.model, plan_names=plan_names)
            break

    return {
        "domain": domain,
        "pricing": pricing,
        "offsiteNews": offsite_news,
        "capabilities": capabilities,
        "executionTimeSec": round(execution_time_sec, 2),
        "provenance": provenance,
    }


def _translate_pipeline_error(exc: Exception) -> PipelineExecutionError:
    """Map pipeline exceptions to a safe client-facing message (no internals)."""
    if isinstance(exc, CollectionError):
        message = str(exc) or "The collection pipeline could not gather competitor pages."
        return PipelineExecutionError(message)
    if isinstance(exc, RuntimeError):
        return PipelineExecutionError(str(exc))
    logger.exception("Unexpected pipeline failure: %s", type(exc).__name__)
    return PipelineExecutionError("The analysis pipeline failed unexpectedly.")


async def run_analysis(
    domain: str,
    query: str,
    parameters: AnalysisParameters,
    mock: bool,
) -> AnalysisOutcome:
    """Run the real orchestrator pipeline and shape its output for the API.

    Raises :class:`PipelineExecutionError` on failure so the router can persist
    the failure and return a consistent 502 envelope.
    """
    started = time.perf_counter()
    tracking_store = database.get_tracking_store()

    try:
        report_path: Path = await run_pipeline(
            query,
            mock=mock,
            domain=domain,
            tracking_store=tracking_store,
        )
    except (CollectionError, RuntimeError, ValueError) as exc:
        raise _translate_pipeline_error(exc) from exc

    report_markdown = report_path.read_text(encoding="utf-8")
    sources = parse_sources(report_markdown)

    # GeminiService is synchronous (network + parsing): keep it off the loop.
    extractions = await asyncio.to_thread(
        extract_structured_data,
        report_markdown,
        parameters,
        sources[0] if sources else None,
    )

    execution_time_sec = time.perf_counter() - started
    data = build_competitor_data(domain, extractions, execution_time_sec)

    return AnalysisOutcome(
        report_path=str(report_path),
        sources=sources,
        extractions=extractions,
        data=data,
        execution_time_sec=execution_time_sec,
    )
