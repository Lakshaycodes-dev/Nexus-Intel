"""Typed value objects shared by discovery, browser, extraction and tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utcnow().replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PageCategory(str, Enum):
    PRICING = "pricing"
    FEATURES = "features"
    PRODUCT = "product"
    ANNOUNCEMENTS = "announcements"
    CHANGELOG = "changelog"
    BLOG = "blog"
    COMPANY = "company"
    GENERAL = "general"


# Categories in crawl-priority order (lower index = higher priority).
CATEGORY_PRIORITY: dict[PageCategory, int] = {
    PageCategory.PRICING: 0,
    PageCategory.CHANGELOG: 1,
    PageCategory.ANNOUNCEMENTS: 2,
    PageCategory.FEATURES: 3,
    PageCategory.PRODUCT: 4,
    PageCategory.COMPANY: 6,
    PageCategory.BLOG: 7,
    PageCategory.GENERAL: 9,
}


@dataclass
class DiscoveredPage:
    url: str
    source: str = "link"  # sitemap | link | seed
    depth: int = 0
    priority: int = 50
    categories: list[PageCategory] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source": self.source,
            "depth": self.depth,
            "priority": self.priority,
            "categories": [c.value for c in self.categories],
        }


@dataclass
class PageClassification:
    primary: PageCategory
    categories: list[PageCategory]
    confidence: float
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary.value,
            "categories": [c.value for c in self.categories],
            "confidence": round(self.confidence, 3),
            "signals": list(self.signals),
        }


@dataclass
class PageSnapshot:
    """One rendered state of a page (monthly, annual, expanded, ...)."""

    url: str
    final_url: str
    title: str = ""
    meta_description: str = ""
    headings: list[str] = field(default_factory=list)
    text: str = ""
    html: str = ""
    links: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    lists: list[dict[str, Any]] = field(default_factory=list)
    billing_state: str = "default"  # default | monthly | annual
    interactions: list[str] = field(default_factory=list)
    status: str = "success"  # success | failed | blocked
    error: Optional[str] = None
    retrieval_method: str = "playwright"
    retrieved_at: str = field(default_factory=iso_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "meta_description": self.meta_description,
            "headings": list(self.headings),
            "text": self.text,
            "html_length": len(self.html or ""),
            "links": list(self.links),
            "tables": list(self.tables),
            "lists": list(self.lists),
            "billing_state": self.billing_state,
            "interactions": list(self.interactions),
            "status": self.status,
            "error": self.error,
            "retrieval_method": self.retrieval_method,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class Evidence:
    source_url: str
    snippet: str
    method: str
    retrieved_at: str = field(default_factory=iso_now)

    def to_dict(self) -> dict[str, str]:
        return {
            "source_url": self.source_url,
            "snippet": self.snippet,
            "method": self.method,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class ExtractedPlan:
    name: str
    price: Optional[float] = None
    price_display: Optional[str] = None
    currency: Optional[str] = None
    billing_period: str = "other"
    seats: Optional[int] = None
    included_features: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "price_display": self.price_display,
            "currency": self.currency,
            "billing_period": self.billing_period,
            "seats": self.seats,
            "included_features": list(self.included_features),
            "notes": self.notes,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class ExtractedFeature:
    name: str
    category: str = ""
    description: str = ""
    support: str = "unknown"
    plans: list[str] = field(default_factory=list)
    value: Optional[str] = None
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "support": self.support,
            "plans": list(self.plans),
            "value": self.value,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class ExtractedAnnouncement:
    title: str
    summary: str = ""
    date: Optional[str] = None
    date_raw: Optional[str] = None
    url: Optional[str] = None
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "date": self.date,
            "date_raw": self.date_raw,
            "url": self.url,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class PageExtraction:
    url: str
    categories: list[PageCategory]
    classification: PageClassification
    pricing: dict[str, Any] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    news: dict[str, Any] = field(default_factory=dict)
    generic: dict[str, Any] = field(default_factory=dict)
    snapshots: list[PageSnapshot] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def structured_payload(self) -> dict[str, Any]:
        """Compact, deterministic payload used for tracking/hash comparison."""
        return {
            "pricing": _strip_evidence(self.pricing),
            "features": _strip_evidence(self.features),
            "news": _strip_evidence(self.news),
            "generic": self.generic,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "categories": [c.value for c in self.categories],
            "classification": self.classification.to_dict(),
            "pricing": self.pricing,
            "features": self.features,
            "news": self.news,
            "generic": self.generic,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "warnings": list(self.warnings),
        }


def _strip_evidence(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_evidence(v) for k, v in value.items() if k != "evidence"}
    if isinstance(value, list):
        return [_strip_evidence(v) for v in value]
    return value


@dataclass
class CrawlStats:
    discovered: int = 0
    crawled: int = 0
    skipped_unchanged: int = 0
    reused_cached: int = 0
    failed: int = 0
    changes: int = 0
    interactions: int = 0
    start_time: str = field(default_factory=iso_now)
    end_time: Optional[str] = None

    def finish(self) -> None:
        self.end_time = iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovered": self.discovered,
            "crawled": self.crawled,
            "skipped_unchanged": self.skipped_unchanged,
            "reused_cached": self.reused_cached,
            "failed": self.failed,
            "changes": self.changes,
            "interactions": self.interactions,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class CollectionResult:
    report_path: str
    source_urls: list[str]
    pages: list[PageExtraction]
    stats: CrawlStats
    changes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_path": self.report_path,
            "source_urls": list(self.source_urls),
            "pages": [page.to_dict() for page in self.pages],
            "stats": self.stats.to_dict(),
            "changes": list(self.changes),
            "warnings": list(self.warnings),
        }
