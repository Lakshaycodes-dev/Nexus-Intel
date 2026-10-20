"""Runtime configuration for the TinyFish Search and Fetch pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


MOCK_MODE: bool = _as_bool(os.getenv("MOCK_MODE", "true"), default=True)

TINYFISH_API_KEY: str = os.getenv("TINYFISH_API_KEY", "").strip()
TINYFISH_SEARCH_URL: str = os.getenv(
    "TINYFISH_SEARCH_URL",
    "https://api.tinyfish.com/v1/search",
)
TINYFISH_FETCH_URL: str = os.getenv(
    "TINYFISH_FETCH_URL",
    "https://api.tinyfish.com/v1/fetch",
)
TINYFISH_SEARCH_METHOD: str = os.getenv("TINYFISH_SEARCH_METHOD", "POST").strip().upper()
TINYFISH_TIMEOUT_SECONDS: float = _as_float(
    os.getenv("TINYFISH_TIMEOUT_SECONDS", "30"),
    30.0,
)
TINYFISH_MAX_RESULTS: int = max(
    1,
    _as_int(os.getenv("TINYFISH_MAX_RESULTS", "5"), 5),
)

if TINYFISH_SEARCH_METHOD not in {"GET", "POST"}:
    TINYFISH_SEARCH_METHOD = "POST"
