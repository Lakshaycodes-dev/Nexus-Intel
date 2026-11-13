"""Environment-driven configuration for the Playwright collection pipeline.

Every value has a safe default so the module can be imported in tests and in
environments where only ``MOCK_MODE`` is configured. Secrets are read from the
environment only and are never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _text(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


@dataclass(frozen=True)
class CollectionSettings:
    """Runtime settings for discovery, browser automation and tracking."""

    # Browser
    browser_name: str = "chromium"
    headless: bool = True
    navigation_timeout_ms: int = 30_000
    interaction_timeout_ms: int = 3_000
    page_settle_timeout_ms: int = 4_000
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 nexus-intel/2.0"
    )
    viewport_width: int = 1440
    viewport_height: int = 900
    block_resources: bool = True
    allow_static_fallback: bool = True

    # Crawling
    max_pages: int = 12
    max_depth: int = 2
    concurrency: int = 3
    request_timeout_seconds: float = 20.0
    crawl_interval_seconds: float = 0.25
    respect_robots: bool = True

    # Interaction
    max_interactions: int = 18
    capture_billing_states: bool = True

    # Tracking
    tracking_enabled: bool = True
    incremental_crawl: bool = True
    tracking_interval_hours: float = 12.0
    store_full_snapshot: bool = True

    # Domain resolution / search provider
    search_provider: str = ""  # "gemini" | "http" | ""
    search_api_url: str = ""
    search_api_key: str = field(default="", repr=False)
    search_max_results: int = 5
    gemini_model: str = "gemini-1.5-flash"

    # Safety
    max_html_chars: int = 600_000
    max_text_chars: int = 120_000
    allow_private_hosts: bool = False

    @classmethod
    def from_env(cls) -> "CollectionSettings":
        return cls(
            browser_name=_text("PLAYWRIGHT_BROWSER", "chromium"),
            headless=_bool("PLAYWRIGHT_HEADLESS", True),
            navigation_timeout_ms=_int("NAVIGATION_TIMEOUT_MS", 30_000),
            interaction_timeout_ms=_int("INTERACTION_TIMEOUT_MS", 3_000),
            page_settle_timeout_ms=_int("PAGE_SETTLE_TIMEOUT_MS", 4_000),
            user_agent=_text("PLAYWRIGHT_USER_AGENT", cls.user_agent),
            viewport_width=_int("PLAYWRIGHT_VIEWPORT_WIDTH", 1440),
            viewport_height=_int("PLAYWRIGHT_VIEWPORT_HEIGHT", 900),
            block_resources=_bool("PLAYWRIGHT_BLOCK_RESOURCES", True),
            allow_static_fallback=_bool("PLAYWRIGHT_ALLOW_STATIC_FALLBACK", True),
            max_pages=max(1, _int("MAX_PAGES_PER_COMPETITOR", 12)),
            max_depth=max(0, _int("CRAWL_MAX_DEPTH", 2)),
            concurrency=max(1, _int("CRAWL_CONCURRENCY", 3)),
            request_timeout_seconds=max(1.0, _float("CRAWL_REQUEST_TIMEOUT_SECONDS", 20.0)),
            crawl_interval_seconds=max(0.0, _float("CRAWL_INTERVAL_SECONDS", 0.25)),
            respect_robots=_bool("CRAWL_RESPECT_ROBOTS", True),
            max_interactions=max(0, _int("MAX_INTERACTIONS", 18)),
            capture_billing_states=_bool("CAPTURE_BILLING_STATES", True),
            tracking_enabled=_bool("TRACKING_ENABLED", True),
            incremental_crawl=_bool("TRACKING_INCREMENTAL_CRAWL", True),
            tracking_interval_hours=max(0.0, _float("TRACKING_INTERVAL_HOURS", 12.0)),
            store_full_snapshot=_bool("TRACKING_STORE_FULL_SNAPSHOT", True),
            search_provider=os.getenv("SEARCH_PROVIDER", "").strip().lower(),
            search_api_url=os.getenv("SEARCH_API_URL", "").strip(),
            search_api_key=os.getenv("SEARCH_API_KEY", "").strip(),
            search_max_results=max(1, _int("SEARCH_MAX_RESULTS", 5)),
            gemini_model=_text("GEMINI_MODEL", "gemini-1.5-flash"),
            max_html_chars=max(20_000, _int("COLLECTION_MAX_HTML_CHARS", 600_000)),
            max_text_chars=max(5_000, _int("COLLECTION_MAX_TEXT_CHARS", 120_000)),
            allow_private_hosts=_bool("COLLECTION_ALLOW_PRIVATE_HOSTS", False),
        )
