"""ElevenLabs voice briefings: deterministic change digest + server-side TTS.

This module is additive. It reads the *existing* persisted analysis records and
never touches the scraping pipeline or the Gemini extraction schemas. The digest
is built deterministically from stored pricing/news snapshots, then ElevenLabs
speaks the resulting script when the user asks for audio.

Credentials come from ``app.config`` (sourced from the root ``.env``) and are
never returned to the browser, embedded in the script, or written to logs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import httpx

from app import config
from app.schemas import BriefingChange, BriefingSummary

logger = logging.getLogger("nexus_intel.briefing")

# Public window keys accepted by the API and the dashboard.
WINDOWS: dict[str, tuple[timedelta, str]] = {
    "24h": (timedelta(hours=24), "last 24 hours"),
    "7d": (timedelta(days=7), "last 7 days"),
}

_MAX_CHANGES_PER_DOMAIN = 6
_MAX_SCRIPT_DOMAINS = 12
_MAX_SCRIPT_CHANGES_PER_DOMAIN = 4
_PRESENTATION_CHANGE_CAP = 60
_MATERIAL_CHANGE_TYPES = frozenset({"pricing", "news", "capability"})
_SENTIMENTS = frozenset({"positive", "threat", "neutral"})


class VoiceBriefingError(RuntimeError):
    """The ElevenLabs synthesis step failed or could not be reached."""


class VoiceBriefingUnavailable(VoiceBriefingError):
    """Credentials/voice configuration is missing, so audio cannot be made."""


# --------------------------------------------------------------------------- #
# Time / text helpers
# --------------------------------------------------------------------------- #
def _as_utc(value: Any) -> Optional[datetime]:
    """Coerce datetimes/ISO strings (including Mongo's naive UTC) to aware UTC."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_window(window: str) -> tuple[timedelta, str]:
    """Return ``(lookback_delta, human_label)`` for a public window key."""
    try:
        return WINDOWS[window]
    except KeyError:
        supported = ", ".join(sorted(WINDOWS))
        raise ValueError(
            f"Unsupported briefing window {window!r}; use one of: {supported}."
        ) from None


def since_for(window: str, *, now: Optional[datetime] = None) -> datetime:
    """Start of the look-back window as an aware UTC datetime."""
    delta, _label = normalize_window(window)
    reference = _as_utc(now) or datetime.now(timezone.utc)
    return reference - delta


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _plural(count: int, singular: str, plural: Optional[str] = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def _spoken_domain(domain: str) -> str:
    return _clean(domain).replace(".", " dot ")


# --------------------------------------------------------------------------- #
# Snapshot extraction
# --------------------------------------------------------------------------- #
def _pricing_map(data: dict[str, Any]) -> dict[str, str]:
    prices: dict[str, str] = {}
    rows = data.get("pricing") or []
    if not isinstance(rows, list):
        return prices
    for row in rows:
        if not isinstance(row, dict):
            continue
        tier = _clean(row.get("tier"))
        if not tier:
            continue
        monthly = _clean(row.get("monthly"))
        annual = _clean(row.get("annual"))
        prices[tier] = monthly or annual or "no listed price"
    return prices


def _news_items(data: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    rows = data.get("offsiteNews") or []
    if not isinstance(rows, list):
        return items
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = _clean(row.get("title"))
        if not title:
            continue
        source = _clean(row.get("source"))
        sentiment = _clean(row.get("sentiment")).lower()
        items.append(
            {
                "title": title,
                "source": source,
                "sentiment": sentiment if sentiment in _SENTIMENTS else "neutral",
            }
        )
    return items


def _news_key(title: str) -> str:
    return _clean(title).casefold()


def _pricing_changes(
    domain: str, latest: dict[str, str], previous: dict[str, str], has_previous: bool
) -> list[BriefingChange]:
    changes: list[BriefingChange] = []
    if not has_previous:
        return changes

    for tier, price in latest.items():
        if tier in previous:
            old_price = previous[tier]
            if old_price != price:
                changes.append(
                    BriefingChange(
                        domain=domain,
                        change_type="pricing",
                        title=f"{tier} price changed",
                        detail=f"{tier} moved from {old_price} to {price}.",
                        sentiment="neutral",
                    )
                )
        else:
            changes.append(
                BriefingChange(
                    domain=domain,
                    change_type="pricing",
                    title=f"New {tier} tier",
                    detail=f"{tier} was added at {price}.",
                    sentiment="neutral",
                )
            )

    for tier, old_price in previous.items():
        if tier not in latest:
            changes.append(
                BriefingChange(
                    domain=domain,
                    change_type="pricing",
                    title=f"{tier} tier removed",
                    detail=f"{tier} is no longer listed (was {old_price}).",
                    sentiment="threat",
                )
            )
    return changes


def _news_changes(
    domain: str, latest_news: list[dict[str, str]], previous_news: list[dict[str, str]]
) -> list[BriefingChange]:
    seen = {_news_key(item["title"]) for item in previous_news}
    changes: list[BriefingChange] = []
    for item in latest_news:
        if _news_key(item["title"]) in seen:
            continue
        detail = (
            f"{item['source']} reported: {item['title']}"
            if item["source"]
            else item["title"]
        )
        changes.append(
            BriefingChange(
                domain=domain,
                change_type="news",
                title=item["title"],
                detail=detail.rstrip(".") + ".",
                sentiment=item["sentiment"],  # type: ignore[arg-type]
            )
        )
    return changes


def _changes_for_domain(
    domain: str, runs: list[dict[str, Any]]
) -> list[BriefingChange]:
    """Compare the two most recent snapshots for one competitor."""
    latest = runs[-1]
    latest_data = latest.get("data") or {}
    previous = runs[-2] if len(runs) > 1 else None
    previous_data = (previous or {}).get("data") or {}

    latest_prices = _pricing_map(latest_data)
    previous_prices = _pricing_map(previous_data)
    latest_news = _news_items(latest_data)
    previous_news = _news_items(previous_data)
    has_previous = previous is not None and bool(previous_data)

    changes = _pricing_changes(domain, latest_prices, previous_prices, has_previous)
    changes.extend(_news_changes(domain, latest_news, previous_news))

    if changes:
        return changes[:_MAX_CHANGES_PER_DOMAIN]

    # Nothing moved (or this is the first snapshot): give the listener a useful
    # baseline instead of dropping the competitor from the briefing entirely.
    tiers = ", ".join(
        f"{tier} at {price}" for tier, price in list(latest_prices.items())[:4]
    )
    if has_previous:
        title = "No material change detected"
        detail = "No pricing or news movement since the previous snapshot."
    else:
        title = "Baseline captured"
        detail = "First tracked snapshot in this window."
    if tiers:
        detail = f"{detail} Current tiers: {tiers}."

    return [
        BriefingChange(
            domain=domain,
            change_type="tracked",
            title=title,
            detail=detail,
            sentiment="neutral",
        )
    ]


# --------------------------------------------------------------------------- #
# Digest / script
# --------------------------------------------------------------------------- #
def _build_script(
    grouped: dict[str, list[dict[str, Any]]],
    changes_by_domain: dict[str, list[BriefingChange]],
    *,
    label: str,
    record_count: int,
    activity_count: int,
) -> str:
    if not grouped:
        return (
            f"Here is your Nexus Intel market briefing for the {label}. "
            "No completed competitor analyses were recorded in this window. "
            "Run a new scan to start tracking competitor movement."
        )

    domains = list(grouped)
    domain_count = len(domains)
    intro = f"Here is your Nexus Intel market briefing for the {label}. "

    if activity_count:
        intro += (
            f"I reviewed {record_count} competitor "
            f"{_plural(record_count, 'update')} across {domain_count} "
            f"{_plural(domain_count, 'competitor')} and found {activity_count} "
            f"notable {_plural(activity_count, 'change')}. "
        )
    else:
        intro += (
            f"I reviewed {record_count} recorded "
            f"{_plural(record_count, 'update')} across {domain_count} "
            f"{_plural(domain_count, 'competitor')}, and no material pricing or "
            "news changes were detected. "
        )

    sections: list[str] = []
    for domain in domains[:_MAX_SCRIPT_DOMAINS]:
        domain_changes = changes_by_domain.get(domain, [])
        material = [
            change for change in domain_changes if change.change_type != "tracked"
        ]
        spoken = [change for change in (material or domain_changes)]
        if not spoken:
            continue
        sentences = [f"{_spoken_domain(domain)}."]
        for change in spoken[:_MAX_SCRIPT_CHANGES_PER_DOMAIN]:
            if change.change_type == "news":
                sentences.append(f"{change.title.rstrip('.')}.")
            else:
                sentences.append(change.detail)
        sections.append(" ".join(sentences))

    return (
        intro
        + " ".join(sections)
        + " That is all for this briefing. Open the dashboard for the full details."
    )


def build_briefing(
    records: Iterable[dict[str, Any]],
    *,
    window: str,
    now: Optional[datetime] = None,
) -> BriefingSummary:
    """Build a deterministic briefing for the selected look-back window.

    ``records`` are raw analysis documents (as stored by ``AnalysisRepository``).
    Only completed runs with usable ``data`` inside the window are considered;
    each competitor is compared against its previous snapshot in that window.
    """
    delta, label = normalize_window(window)
    reference = _as_utc(now) or datetime.now(timezone.utc)
    cutoff = reference - delta

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("status") not in (None, "completed"):
            continue
        data = record.get("data")
        if not isinstance(data, dict):
            continue
        created = _as_utc(record.get("created_at"))
        if created is None or created < cutoff:
            continue
        domain = _clean(data.get("domain") or record.get("domain"))
        if not domain:
            continue
        grouped.setdefault(domain, []).append({**record, "_created": created})

    for runs in grouped.values():
        runs.sort(key=lambda item: item["_created"])

    changes_by_domain: dict[str, list[BriefingChange]] = {
        domain: _changes_for_domain(domain, runs)
        for domain, runs in sorted(grouped.items())
    }

    changes: list[BriefingChange] = []
    for domain_changes in changes_by_domain.values():
        changes.extend(domain_changes)
    changes = changes[:_PRESENTATION_CHANGE_CAP]

    domains = sorted(grouped)
    record_count = sum(len(runs) for runs in grouped.values())
    activity_count = sum(
        1 for change in changes if change.change_type in _MATERIAL_CHANGE_TYPES
    )
    has_activity = activity_count > 0

    if not grouped:
        headline = f"No competitor activity in the {label}"
    elif has_activity:
        headline = (
            f"{activity_count} {_plural(activity_count, 'change')} across "
            f"{len(domains)} {_plural(len(domains), 'competitor')} in the {label}"
        )
    else:
        headline = (
            f"No material changes across {len(domains)} "
            f"{_plural(len(domains), 'competitor')} in the {label}"
        )

    script = _build_script(
        grouped,
        changes_by_domain,
        label=label,
        record_count=record_count,
        activity_count=activity_count,
    )
    max_chars = max(200, int(config.BRIEFING_MAX_SCRIPT_CHARS))
    if len(script) > max_chars:
        trimmed = script[: max_chars - 64].rsplit(" ", 1)[0].rstrip(" ,.;")
        script = f"{trimmed}. That is all for this briefing."

    return BriefingSummary(
        window=window,  # type: ignore[arg-type]
        window_label=label,
        headline=headline,
        script=script,
        generated_at=reference,
        domains=domains,
        record_count=record_count,
        changes=changes,
        has_activity=has_activity,
    )


# --------------------------------------------------------------------------- #
# ElevenLabs text-to-speech
# --------------------------------------------------------------------------- #
def _friendly_status(status_code: int) -> str:
    if status_code in (401, 403):
        return (
            "The voice service rejected the credentials. Check ELEVENLABS_API_KEY "
            "in the backend .env file."
        )
    if status_code == 402:
        return (
            "The ElevenLabs account cannot use the configured voice on its current "
            "plan. Library voices require a paid subscription; upgrade the plan or "
            "set ELEVENLABS_VOICE_ID to a voice this account can use."
        )
    if status_code == 429:
        return "The voice service is rate limited right now. Please retry shortly."
    if status_code == 422:
        return "The voice service rejected the briefing text. Please retry."
    return f"The voice service could not generate the briefing (HTTP {status_code})."


async def synthesize_speech(
    text: str,
    *,
    api_key: Optional[str] = None,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    voice_settings: Optional[dict[str, Any]] = None,
) -> bytes:
    """Convert the briefing script into MP3 bytes via ElevenLabs.

    Raises :class:`VoiceBriefingUnavailable` when credentials are missing and
    :class:`VoiceBriefingError` for transport/upstream failures. Upstream
    response bodies are never echoed, so a rejected key cannot leak.
    """
    key = (api_key if api_key is not None else config.ELEVENLABS_API_KEY).strip()
    voice = (voice_id if voice_id is not None else config.ELEVENLABS_VOICE_ID).strip()
    if not key or not voice:
        raise VoiceBriefingUnavailable(
            "Voice briefings are not configured. Add ELEVENLABS_API_KEY and "
            "ELEVENLABS_VOICE_ID to the backend .env file."
        )

    spoken = _clean(text)
    if not spoken:
        raise VoiceBriefingError("There is no briefing text to synthesize.")

    url = f"{config.ELEVENLABS_API_URL}/text-to-speech/{voice}"
    body: dict[str, Any] = {
        "text": spoken,
        "model_id": (model_id or config.ELEVENLABS_MODEL_ID),
        "voice_settings": voice_settings
        or {"stability": 0.45, "similarity_boost": 0.75},
    }
    headers = {
        "xi-api-key": key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=config.ELEVENLABS_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning(
            "ElevenLabs synthesis request failed: %s", type(exc).__name__
        )
        raise VoiceBriefingError(
            "The voice service could not be reached. Please try again shortly."
        ) from exc

    if response.status_code >= 400:
        logger.warning(
            "ElevenLabs synthesis rejected with status %s", response.status_code
        )
        raise VoiceBriefingError(_friendly_status(response.status_code))

    audio = response.content
    if not audio:
        raise VoiceBriefingError("The voice service returned an empty audio stream.")
    return audio


__all__ = [
    "WINDOWS",
    "VoiceBriefingError",
    "VoiceBriefingUnavailable",
    "build_briefing",
    "normalize_window",
    "since_for",
    "synthesize_speech",
]
