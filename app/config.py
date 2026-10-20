"""Runtime configuration for the Nexus-Intel FastAPI backend.

Follows the repository convention (see the root ``config.py``): values are read
from environment variables with ``os.getenv`` after ``python-dotenv`` loads the
project ``.env`` file. Secrets are never hard-coded and never logged.

New backend-specific variables (placeholders only in ``.env.example``):

* ``MONGODB_URI``                  - MongoDB connection string.
* ``MONGODB_DATABASE``             - Database name.
* ``MONGODB_COLLECTION``           - Collection holding analysis records.
* ``MONGODB_SERVER_SELECTION_TIMEOUT_MS`` - Driver timeout used for the
  startup connectivity probe (keeps the app bootable when MongoDB is down).
* ``CORS_ORIGINS``                 - Comma-separated list of allowed origins
  for the frontend dev server.
* ``ANALYSIS_TIMEOUT_SECONDS``     - Hard timeout around one pipeline run.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Single source of truth for the pipeline default lives in the existing config.
from config import MOCK_MODE  # noqa: E402  (must run after load_dotenv)

API_TITLE = "Nexus-Intel API"
API_VERSION = "1.0.0"
API_DESCRIPTION = (
    "Backend for the Nexus-Intel competitor intelligence pipeline. "
    "POST /api/v1/analyze triggers the existing orchestrator pipeline, "
    "persists the run in MongoDB, and returns structured competitor data."
)


def _as_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --- MongoDB --------------------------------------------------------------- #

MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017").strip()
MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "nexus_intel").strip()
MONGODB_COLLECTION: str = os.getenv("MONGODB_COLLECTION", "analyses").strip()
MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = _as_int(
    os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2000"), 2000
)

# --- HTTP / CORS ----------------------------------------------------------- #

_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS: bool = _as_bool(os.getenv("CORS_ALLOW_CREDENTIALS", "false"))

# --- Pipeline -------------------------------------------------------------- #

ANALYSIS_TIMEOUT_SECONDS: float = _as_float(
    os.getenv("ANALYSIS_TIMEOUT_SECONDS", "300"), 300.0
)
