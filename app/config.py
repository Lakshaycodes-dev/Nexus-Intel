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
* ``IN_MEMORY_PERSISTENCE``         - Use an in-process analysis/tracking store
  when MongoDB is unavailable (defaults to mock mode).
* ``CORS_ORIGINS``                 - Comma-separated list of allowed origins
  for the frontend dev server.
* ``ANALYSIS_TIMEOUT_SECONDS``     - Hard timeout around one pipeline run.

Additive voice-briefing settings (server-side only; never sent to the browser):

* ``ELEVENLABS_API_KEY``           - ElevenLabs API key.
* ``ELEVENLABS_VOICE_ID``          - Voice used for the spoken briefing.
* ``ELEVENLABS_MODEL_ID``          - TTS model (defaults to ``eleven_flash_v2_5``).
* ``ELEVENLABS_API_URL``           - Optional API base override.
* ``ELEVENLABS_TIMEOUT_SECONDS``   - HTTP timeout for one synthesis request.
* ``BRIEFING_MAX_SCRIPT_CHARS``    - Upper bound on the spoken script length.
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
# Tracking collections (minimal additive change; existing collections preserved).
MONGODB_PAGE_REGISTRY_COLLECTION: str = os.getenv(
    "MONGODB_PAGE_REGISTRY_COLLECTION", "page_registry"
).strip()
MONGODB_SNAPSHOTS_COLLECTION: str = os.getenv(
    "MONGODB_SNAPSHOTS_COLLECTION", "page_snapshots"
).strip()
MONGODB_CHANGE_EVENTS_COLLECTION: str = os.getenv(
    "MONGODB_CHANGE_EVENTS_COLLECTION", "change_events"
).strip()
# Local/demo fallback: keep analysis records in-process when MongoDB is down.
# Defaults to mock-mode behaviour; set explicitly to override.
IN_MEMORY_PERSISTENCE: bool = _as_bool(
    os.getenv("IN_MEMORY_PERSISTENCE", "true" if MOCK_MODE else "false"),
    default=MOCK_MODE,
)

# --- HTTP / CORS ----------------------------------------------------------- #

_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS: bool = _as_bool(os.getenv("CORS_ALLOW_CREDENTIALS", "false"))

# --- Auth ------------------------------------------------------------------ #

# Signing key for access tokens. An ephemeral key is generated when unset, but
# sessions then die on restart - always set this in real deployments.
JWT_SECRET: str = os.getenv("JWT_SECRET", "").strip()
JWT_EXPIRES_MINUTES: int = max(
    5, _as_int(os.getenv("JWT_EXPIRES_MINUTES", "10080"), 10080)  # 7 days
)
MONGODB_USERS_COLLECTION: str = os.getenv("MONGODB_USERS_COLLECTION", "users").strip()
PASSWORD_MIN_LENGTH: int = max(8, _as_int(os.getenv("PASSWORD_MIN_LENGTH", "8"), 8))
ALLOW_REGISTRATION: bool = _as_bool(os.getenv("ALLOW_REGISTRATION", "true"), True)

# --- Pipeline -------------------------------------------------------------- #

ANALYSIS_TIMEOUT_SECONDS: float = _as_float(
    os.getenv("ANALYSIS_TIMEOUT_SECONDS", "300"), 300.0
)

# --- ElevenLabs voice briefing --------------------------------------------- #

# Secrets stay in the root ``.env``; they are read here and used only by
# server-side code. The dashboard never receives the key or the raw voice ID.
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "").strip()
# Free ElevenLabs plans can speak premade voices through the API; library
# voices return HTTP 402. Set a premade voice ID unless the plan is paid.
ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
ELEVENLABS_MODEL_ID: str = (
    os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()
    or "eleven_flash_v2_5"
)
ELEVENLABS_API_URL: str = os.getenv(
    "ELEVENLABS_API_URL", "https://api.elevenlabs.io/v1"
).rstrip("/")
ELEVENLABS_TIMEOUT_SECONDS: float = _as_float(
    os.getenv("ELEVENLABS_TIMEOUT_SECONDS", "45"), 45.0
)
BRIEFING_MAX_SCRIPT_CHARS: int = max(
    200, _as_int(os.getenv("BRIEFING_MAX_SCRIPT_CHARS", "4000"), 4000)
)
