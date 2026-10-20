"""Pure helpers shared by the TinyFish Web Agent module.

The functions in this module perform no network I/O. They validate target URLs,
normalise untrusted API/page values, extract an API-provided session identifier,
and implement the retry/backoff rules used by the async client.
"""

from __future__ import annotations

import ipaddress
import json
import math
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, TypeVar
from urllib.parse import urljoin, urlparse, urlunparse

T = TypeVar("T")

CANONICAL_ACTIONS = frozenset(
    {
        "open_pricing_page",
        "dismiss_cookie_banner",
        "dismiss_marketing_popup",
        "select_annual_billing",
        "expand_feature_list",
        "expand_accordions",
        "expand_comparison_table",
        "wait_for_dynamic_content",
        "scroll_to_pricing",
    }
)

ACTION_ALIASES = {
    "open_pricing": "open_pricing_page",
    "navigate_to_pricing": "open_pricing_page",
    "go_to_pricing": "open_pricing_page",
    "find_pricing_page": "open_pricing_page",
    "close_cookie_banner": "dismiss_cookie_banner",
    "dismiss_cookie_banner": "dismiss_cookie_banner",
    "dismiss_cookies": "dismiss_cookie_banner",
    "accept_cookies": "dismiss_cookie_banner",
    "accept_all_cookies": "dismiss_cookie_banner",
    "reject_all_cookies": "dismiss_cookie_banner",
    "dismiss_cookie_consent": "dismiss_cookie_banner",
    "close_cookie_consent": "dismiss_cookie_banner",
    "dismiss_popup": "dismiss_marketing_popup",
    "close_popup": "dismiss_marketing_popup",
    "close_modal": "dismiss_marketing_popup",
    "dismiss_modal": "dismiss_marketing_popup",
    "close_newsletter_popup": "dismiss_marketing_popup",
    "close_chat_widget": "dismiss_marketing_popup",
    "select_annual": "select_annual_billing",
    "select_yearly": "select_annual_billing",
    "toggle_annual": "select_annual_billing",
    "toggle_annual_billing": "select_annual_billing",
    "click_annual": "select_annual_billing",
    "click_annual_billing": "select_annual_billing",
    "switch_to_annual": "select_annual_billing",
    "expand_features": "expand_feature_list",
    "expand_all_features": "expand_feature_list",
    "show_all_features": "expand_feature_list",
    "click_plus_icons": "expand_feature_list",
    "show_more_features": "expand_feature_list",
    "expand_plan_features": "expand_feature_list",
    "expand_faq": "expand_accordions",
    "open_accordions": "expand_accordions",
    "expand_all_accordions": "expand_accordions",
    "expand_comparison": "expand_comparison_table",
    "expand_compare_table": "expand_comparison_table",
    "compare_all_features": "expand_comparison_table",
    "wait": "wait_for_dynamic_content",
    "wait_for_load": "wait_for_dynamic_content",
    "wait_for_pricing": "wait_for_dynamic_content",
    "scroll": "scroll_to_pricing",
    "scroll_pricing_into_view": "scroll_to_pricing",
}

RETRYABLE_ERROR_CODES = frozenset(
    {
        "INTERNAL_ERROR",
        "RATE_LIMIT_EXCEEDED",
        "SERVICE_BUSY",
        "TIMEOUT",
        "MAX_STEPS_EXCEEDED",
        "SITE_BLOCKED",
        "BROWSER_CRASHED",
        "TASK_FAILED",
        "RETRY_REQUIRED",
    }
)

NON_RETRYABLE_ERROR_CODES = frozenset(
    {
        "INVALID_INPUT",
        "MISSING_API_KEY",
        "INVALID_API_KEY",
        "VAULT_RECONNECT_REQUIRED",
        "FORBIDDEN",
        "BILLING_REJECTED",
        "BILLING_FAILURE",
        "INSUFFICIENT_CREDITS",
        "CONTENT_POLICY_VIOLATION",
        "NOT_FOUND",
        "CANCELLED",
    }
)

_BLOCKED_SIGNALS = (
    "site_blocked",
    "captcha",
    "access denied",
    "bot detection",
    "cloudflare",
    "blocked by",
)

_DISALLOWED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "metadata",
        "metadata.google.internal",
        "instance-data",
    }
)

_SESSION_KEYS = frozenset({"session_id", "browser_session_id", "sessionid", "browsersessionid"})
_SESSION_CONTAINER_KEYS = frozenset({"data", "result", "run", "session", "browser"})


def _normalise_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _is_disallowed_host(host: str) -> bool:
    normalised = host.strip().rstrip(".").lower()
    if not normalised:
        return True
    if normalised in _DISALLOWED_HOSTNAMES:
        return True
    if normalised.endswith((".localhost", ".local", ".internal", ".home", ".lan")):
        return True

    candidate = normalised.strip("[]")
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        if candidate.isdigit():
            return True
        return False

    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def normalize_url(raw: str, *, allow_private: bool = False) -> str:
    """Validate an HTTP(S) URL and return a normalised form.

    Private, loopback, link-local, and cloud-metadata hosts are rejected by
    default to reduce SSRF risk. DNS resolution is intentionally not performed
    here; callers that need it must resolve the host separately.
    """

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("url must be a non-empty string")

    value = raw.strip()
    if any(ord(char) < 32 or char.isspace() for char in value):
        raise ValueError("url must not contain whitespace or control characters")
    if "://" not in value:
        value = f"https://{value}"

    try:
        parsed = urlparse(value)
    except ValueError as exc:
        raise ValueError(f"invalid url: {raw}") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("url must use http or https")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("url must include a valid host")
    if parsed.username or parsed.password:
        raise ValueError("credentials are not allowed in the target url")
    if not allow_private and _is_disallowed_host(parsed.hostname):
        raise ValueError("url must not target localhost or a private network address")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("url contains an invalid port") from exc
    if port == 0:
        raise ValueError("url must not use port 0")

    netloc = parsed.netloc.lower()
    return urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )


def normalize_source_url(value: Any, base_url: str = "") -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    candidate = value.strip()
    if base_url and not urlparse(candidate).netloc:
        candidate = urljoin(base_url, candidate)
    try:
        return normalize_url(candidate)
    except ValueError:
        return ""


def domain_from_url(url: str) -> str:
    host = (urlparse(normalize_url(url)).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def looks_like_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if text.startswith(("http://", "https://")):
        return True
    if any(char.isspace() for char in text):
        return False
    host = text.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return "." in host and not host.endswith(".")


def dedupe(items: Iterable[T]) -> tuple[T, ...]:
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def truncate(text: str, max_length: int = 500) -> str:
    if max_length <= 0:
        return ""
    if len(text) <= max_length:
        return text
    return f"{text[: max(0, max_length - 3)].rstrip()}..."


def sanitize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def as_text(value: Any, max_length: int = 500) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, (int, float, bool)):
        text = str(value)
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    return truncate(sanitize_text(text), max_length)


def as_string_list(
    value: Any,
    limit: int = 30,
    max_length: int = 300,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = as_text(value, max_length)
        return (text,) if text else ()
    if isinstance(value, Mapping):
        items: Iterable[Any] = (value,)
    elif isinstance(value, (list, tuple, set, frozenset)):
        items = value
    else:
        text = as_text(value, max_length)
        return (text,) if text else ()

    result: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            text = as_text(
                item.get("text")
                or item.get("value")
                or item.get("name")
                or item.get("message")
                or item,
                max_length,
            )
        else:
            text = as_text(item, max_length)
        if text:
            result.append(text)
        if len(result) >= limit:
            break
    return dedupe(result)


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised in {"true", "yes", "y", "1", "on", "ready", "completed", "success", "present"}:
            return True
        if normalised in {"false", "no", "n", "0", "off", "failed", "absent", "none", ""}:
            return False
    return default


def coerce_int(
    value: Any,
    default: int = 0,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool):
        parsed = int(value)
    elif isinstance(value, (int, float)):
        parsed = int(value) if math.isfinite(float(value)) else default
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
            parsed = int(numeric) if math.isfinite(numeric) else default
        except ValueError:
            parsed = default
    else:
        parsed = default

    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def normalize_action_name(name: Any) -> str:
    text = as_text(name, 120).lower()
    key = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if not key:
        return ""
    return ACTION_ALIASES.get(key, key)


def normalize_action_status(value: Any) -> str:
    text = as_text(value, 40).lower().strip(" .,;:")
    if text in {"completed", "complete", "success", "succeeded", "done", "clicked", "expanded", "selected", "ok"}:
        return "completed"
    if text in {
        "skipped",
        "skip",
        "not_present",
        "not_applicable",
        "not_found",
        "absent",
        "unavailable",
        "no_banner",
        "no_toggle",
    }:
        return "skipped"
    return "failed"


def normalize_billing_period(value: Any) -> str:
    text = as_text(value, 40).lower().strip(" .,;:")
    if text in {
        "annual",
        "annually",
        "yearly",
        "year",
        "per_year",
        "per year",
        "billed_annually",
        "billed annually",
        "annual_billing",
        "yearly_billing",
        "pa",
        "yr",
    }:
        return "annual"
    if "annual" in text or "yearly" in text or "per year" in text:
        return "annual"
    if text in {
        "monthly",
        "month",
        "per_month",
        "per month",
        "billed_monthly",
        "billed monthly",
        "month_to_month",
        "mo",
    }:
        return "monthly"
    if "monthly" in text or "per month" in text:
        return "monthly"
    if text in {"usage", "usage_based", "usage based", "metered", "pay_as_you_go", "pay as you go"}:
        return "usage"
    if "usage" in text or "metered" in text:
        return "usage"
    if text in {"custom", "custom_quote", "quote", "contact_sales", "contact sales", "enterprise"}:
        return "custom"
    if "custom" in text or "quote" in text:
        return "custom"
    return "unknown"


def normalize_run_status(value: Any) -> str:
    text = as_text(value, 40).upper()
    if text in {"COMPLETED", "FAILED", "CANCELLED", "PENDING", "RUNNING"}:
        return text
    return text or "UNKNOWN"


def normalize_extraction_status(
    value: Any,
    *,
    page_ready: bool = False,
    has_sources: bool = False,
    item_count: int = 0,
) -> str:
    text = as_text(value, 40).lower().strip(" .,;:")
    if not page_ready:
        return "failure"
    if text in {"success", "completed", "complete", "ready", "ok", "passed"}:
        return "success" if has_sources and item_count > 0 else "partial"
    if text in {"partial", "incomplete", "degraded", "some_actions_failed"}:
        return "partial"
    if text in {"failure", "failed", "error", "blocked", "unusable"}:
        return "failure"
    if has_sources and item_count > 0:
        return "success"
    return "partial"


def coerce_json_object(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
        except (TypeError, ValueError):
            return {}
        if isinstance(decoded, Mapping):
            return dict(decoded)
    return {}


def _valid_session_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > 256 or any(char.isspace() for char in candidate):
        return None
    return candidate


def extract_session_id(payload: Any, *, max_depth: int = 4) -> str | None:
    """Return an API-provided browser session identifier, if one exists.

    The current TinyFish Agent API returns a ``run_id`` and, while running, a
    ``streaming_url``; it does not document a browser ``session_id``. This helper
    therefore returns ``None`` unless a future response explicitly includes one.
    It never derives a session ID from ``run_id`` or other identifiers.
    """

    def walk(value: Any, depth: int) -> str | None:
        if depth > max_depth or not isinstance(value, Mapping):
            return None
        for key, item in value.items():
            if _normalise_key(key) in _SESSION_KEYS:
                session_id = _valid_session_value(item)
                if session_id:
                    return session_id
        for key, item in value.items():
            if _normalise_key(key) in _SESSION_CONTAINER_KEYS:
                found = walk(item, depth + 1)
                if found:
                    return found
        return None

    return walk(payload, 0)


def parse_retry_after(value: Any, default: float | None = None) -> float | None:
    if value is None or isinstance(value, bool):
        return default

    if isinstance(value, (int, float)):
        seconds = float(value)
        if math.isfinite(seconds):
            return clamp(seconds, 0.0, 600.0)
        return default

    if not isinstance(value, str):
        return default

    text = value.strip()
    if not text:
        return default

    try:
        seconds = float(text)
        if math.isfinite(seconds):
            return clamp(seconds, 0.0, 600.0)
        return default
    except ValueError:
        pass

    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return default
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    seconds = (parsed - datetime.now(timezone.utc)).total_seconds()
    return clamp(seconds, 0.0, 600.0)


def compute_backoff(
    attempt: int,
    base: float = 2.0,
    cap: float = 30.0,
    jitter_ratio: float = 0.25,
    rng: random.Random | None = None,
) -> float:
    safe_attempt = max(1, int(attempt))
    raw = min(max(0.0, cap), max(0.0, base) * (2 ** (safe_attempt - 1)))
    jitter = raw * clamp(jitter_ratio, 0.0, 1.0)
    generator = rng or random
    return round(max(0.0, min(cap, raw + generator.uniform(0.0, jitter))), 3)


def is_retryable_run_error(error: Mapping[str, Any] | None) -> bool:
    if not isinstance(error, Mapping) or not error:
        return True

    code = as_text(error.get("code"), 80).upper()
    category = as_text(error.get("category"), 40).upper()

    if category == "BILLING_FAILURE" or code in NON_RETRYABLE_ERROR_CODES:
        return False
    if code in RETRYABLE_ERROR_CODES:
        return True
    if category in {"SYSTEM_FAILURE", "UNKNOWN", "AGENT_FAILURE"}:
        return True
    return parse_retry_after(error.get("retry_after")) is not None


def contains_blocked_signal(*values: Any) -> bool:
    text = " ".join(as_text(value, 1000) for value in values if value is not None).lower()
    return any(signal in text for signal in _BLOCKED_SIGNALS)


def redact_secret(secret: str, visible: int = 4) -> str:
    if not secret:
        return ""
    if len(secret) <= visible * 2:
        return "*" * len(secret)
    return f"{secret[:visible]}...{secret[-visible:]}"


def redact_text(text: str, *secrets: str) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, redact_secret(secret))
    return redacted
