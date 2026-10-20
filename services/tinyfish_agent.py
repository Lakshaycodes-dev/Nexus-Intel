"""Asynchronous TinyFish Web Agent client for competitor intelligence.

The client starts a TinyFish Agent run asynchronously, polls it to completion,
parses the structured result, and retries with a different prompt when the
result is incomplete. It only uses documented TinyFish endpoints:

* ``POST /v1/automation/run-async``
* ``GET /v1/runs/{run_id}?screenshots=none``
* ``POST /v1/runs/{run_id}/cancel``

The Agent API returns ``run_id`` and, while running, ``streaming_url``. It does
not currently document a browser ``session_id``. The result therefore exposes
``session_id`` as ``None`` with an explicit reason when the API does not provide
one; it never substitutes ``run_id`` or invents a session identifier.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from services.agent_prompts import (
    ActionStatus,
    DEFAULT_OBJECTIVE,
    FocusArea,
    WebAgentPlan,
    build_prompt_spec,
)
from utils.navigation_helpers import (
    as_string_list,
    as_text,
    clamp,
    coerce_bool,
    coerce_int,
    coerce_json_object,
    compute_backoff,
    contains_blocked_signal,
    dedupe,
    extract_session_id,
    is_retryable_run_error,
    looks_like_url,
    normalize_action_name,
    normalize_action_status,
    normalize_billing_period,
    normalize_extraction_status,
    normalize_run_status,
    normalize_source_url,
    normalize_url,
    parse_retry_after,
    redact_text,
)

logger = logging.getLogger(__name__)

DEFAULT_AGENT_BASE_URL = "https://agent.tinyfish.ai"
RUN_ASYNC_PATH = "/v1/automation/run-async"
TERMINAL_RUN_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
_RETRYABLE_HTTP_STATUSES = frozenset({408, 425, 429})
SESSION_MISSING_REASON = (
    "The TinyFish Agent API did not return a browser session_id. "
    "Use run_id to correlate the run; Fetch starts a separate render and does "
    "not accept an Agent session identifier."
)
MOCK_SESSION_MISSING_REASON = "Mock mode does not create a TinyFish browser session."


class TinyFishAgentError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after


TinyFishError = TinyFishAgentError


class TinyFishConfigError(TinyFishAgentError):
    pass


class TinyFishAuthError(TinyFishAgentError):
    pass


class TinyFishValidationError(TinyFishAgentError):
    pass


class TinyFishRateLimitError(TinyFishAgentError):
    pass


class TinyFishServerError(TinyFishAgentError):
    pass


class TinyFishNetworkError(TinyFishAgentError):
    pass


class TinyFishTimeoutError(TinyFishAgentError):
    pass


class TinyFishRunError(TinyFishAgentError):
    pass


@dataclass(frozen=True, slots=True)
class TinyFishSettings:
    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_AGENT_BASE_URL
    http_timeout: float = 30.0
    poll_interval: float = 2.0
    run_timeout: float = 300.0
    max_attempts: int = 3
    browser_profile: str = "lite"
    max_duration_seconds: int = 240
    use_proxy: bool = False
    country_code: str = "US"
    enable_stealth_escalation: bool = True
    retry_base_seconds: float = 2.0
    retry_cap_seconds: float = 30.0
    user_agent: str = "nexus-intel-web-agent/1.0"
    mock: bool = False

    def __post_init__(self) -> None:
        api_key = self.api_key.strip() if isinstance(self.api_key, str) else ""
        if not api_key and not self.mock:
            raise TinyFishConfigError("TINYFISH_API_KEY is required")
        object.__setattr__(self, "api_key", api_key)

        try:
            base_url = normalize_url(self.base_url).rstrip("/")
        except ValueError as exc:
            raise TinyFishConfigError(f"invalid TINYFISH_AGENT_BASE_URL: {exc}") from exc
        object.__setattr__(self, "base_url", base_url)

        object.__setattr__(self, "http_timeout", clamp(float(self.http_timeout), 1.0, 120.0))
        object.__setattr__(self, "poll_interval", clamp(float(self.poll_interval), 0.01, 30.0))
        object.__setattr__(self, "run_timeout", clamp(float(self.run_timeout), 0.1, 540.0))
        object.__setattr__(self, "max_attempts", max(1, min(5, int(self.max_attempts))))
        object.__setattr__(self, "max_duration_seconds", max(30, min(540, int(self.max_duration_seconds))))
        object.__setattr__(self, "retry_base_seconds", clamp(float(self.retry_base_seconds), 0.0, 60.0))
        object.__setattr__(self, "retry_cap_seconds", clamp(float(self.retry_cap_seconds), 0.0, 120.0))

        profile = (self.browser_profile or "lite").strip().lower()
        if profile not in {"lite", "stealth"}:
            raise TinyFishConfigError("TINYFISH_BROWSER_PROFILE must be 'lite' or 'stealth'")
        object.__setattr__(self, "browser_profile", profile)

        country = (self.country_code or "US").strip().upper()
        if len(country) != 2 or not country.isalpha():
            country = "US"
        object.__setattr__(self, "country_code", country)

        object.__setattr__(
            self,
            "user_agent",
            as_text(self.user_agent, 120) or "nexus-intel-web-agent/1.0",
        )

    @classmethod
    def from_env(cls, *, mock: bool | None = None) -> TinyFishSettings:
        def env_text(name: str, default: str) -> str:
            raw = os.getenv(name)
            return default if raw is None or not raw.strip() else raw.strip()

        def env_float(name: str, default: float) -> float:
            raw = os.getenv(name)
            if raw is None or not raw.strip():
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        def env_int(name: str, default: int) -> int:
            raw = os.getenv(name)
            if raw is None or not raw.strip():
                return default
            try:
                return int(raw)
            except ValueError:
                return default

        def env_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None or not raw.strip():
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        resolved_mock = mock if mock is not None else env_bool("MOCK_MODE", True)
        http_timeout_default = env_float(
            "TINYFISH_TIMEOUT_SECONDS",
            env_float("TINYFISH_HTTP_TIMEOUT_SECONDS", 30.0),
        )

        return cls(
            api_key=os.getenv("TINYFISH_API_KEY", "").strip(),
            base_url=env_text("TINYFISH_AGENT_BASE_URL", DEFAULT_AGENT_BASE_URL),
            http_timeout=env_float("TINYFISH_HTTP_TIMEOUT_SECONDS", http_timeout_default),
            poll_interval=env_float("TINYFISH_POLL_INTERVAL_SECONDS", 2.0),
            run_timeout=env_float("TINYFISH_RUN_TIMEOUT_SECONDS", 300.0),
            max_attempts=env_int("TINYFISH_MAX_ATTEMPTS", 3),
            browser_profile=env_text("TINYFISH_BROWSER_PROFILE", "lite"),
            max_duration_seconds=env_int("TINYFISH_MAX_DURATION_SECONDS", 240),
            use_proxy=env_bool("TINYFISH_USE_PROXY", False),
            country_code=env_text("TINYFISH_COUNTRY_CODE", "US"),
            enable_stealth_escalation=env_bool("TINYFISH_STEALTH_ESCALATION", True),
            retry_base_seconds=env_float("TINYFISH_RETRY_BASE_SECONDS", 2.0),
            retry_cap_seconds=env_float("TINYFISH_RETRY_CAP_SECONDS", 30.0),
            user_agent=env_text("TINYFISH_USER_AGENT", "nexus-intel-web-agent/1.0"),
            mock=resolved_mock,
        )


@dataclass(frozen=True, slots=True)
class RunStart:
    run_id: str
    session_id: str | None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    run_id: str
    status: str
    result: Any | None
    error: Mapping[str, Any] | None
    steps: tuple[Mapping[str, Any], ...]
    streaming_url: str | None
    session_id: str | None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_RUN_STATUSES


@dataclass(frozen=True, slots=True)
class ActionResult:
    action: str
    status: ActionStatus
    evidence: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"action": self.action, "status": self.status.value, "evidence": self.evidence}


@dataclass(frozen=True, slots=True)
class PricingPlan:
    plan_name: str
    price: str
    currency: str
    billing_period: str
    description: str
    source_url: str
    verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_name": self.plan_name,
            "price": self.price,
            "currency": self.currency,
            "billing_period": self.billing_period,
            "description": self.description,
            "source_url": self.source_url,
            "verified": self.verified,
        }


@dataclass(frozen=True, slots=True)
class FeatureItem:
    name: str
    category: str
    description: str
    plans: tuple[str, ...]
    source_url: str
    verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "plans": list(self.plans),
            "source_url": self.source_url,
            "verified": self.verified,
        }


@dataclass(frozen=True, slots=True)
class ProductDetail:
    name: str
    detail: str
    source_url: str
    verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "detail": self.detail,
            "source_url": self.source_url,
            "verified": self.verified,
        }


@dataclass(frozen=True, slots=True)
class Announcement:
    title: str
    date: str
    summary: str
    source_url: str
    verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "date": self.date,
            "summary": self.summary,
            "source_url": self.source_url,
            "verified": self.verified,
        }


@dataclass(frozen=True, slots=True)
class SourceReference:
    url: str
    title: str
    retrieved_at: str

    def as_dict(self) -> dict[str, str]:
        return {"url": self.url, "title": self.title, "retrieved_at": self.retrieved_at}


@dataclass(frozen=True, slots=True)
class CompetitorIntelligence:
    page_ready: bool
    status: str
    final_url: str
    competitor_name: str
    website: str
    summary: str
    pricing: tuple[PricingPlan, ...]
    features: tuple[FeatureItem, ...]
    product_details: tuple[ProductDetail, ...]
    announcements: tuple[Announcement, ...]
    sources: tuple[SourceReference, ...]
    actions: tuple[ActionResult, ...]
    missing_data: tuple[str, ...]
    unverified_claims: tuple[str, ...]
    obstacles: tuple[str, ...]
    notes: str
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @property
    def item_count(self) -> int:
        return (
            len(self.pricing)
            + len(self.features)
            + len(self.product_details)
            + len(self.announcements)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "page_ready": self.page_ready,
            "status": self.status,
            "final_url": self.final_url,
            "competitor_name": self.competitor_name,
            "website": self.website,
            "summary": self.summary,
            "pricing": [item.as_dict() for item in self.pricing],
            "features": [item.as_dict() for item in self.features],
            "product_details": [item.as_dict() for item in self.product_details],
            "announcements": [item.as_dict() for item in self.announcements],
            "sources": [item.as_dict() for item in self.sources],
            "actions": [item.as_dict() for item in self.actions],
            "missing_data": list(self.missing_data),
            "unverified_claims": list(self.unverified_claims),
            "obstacles": list(self.obstacles),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class WebAgentResult:
    success: bool
    session_id: str | None
    session_id_missing_reason: str | None
    run_id: str | None
    run_ids: tuple[str, ...]
    attempts: int
    status: str
    target_url: str
    competitor: str
    objective: str
    intelligence: CompetitorIntelligence | None
    errors: tuple[str, ...] = ()
    last_error: str | None = None
    duration_seconds: float = 0.0
    mock: bool = False

    @property
    def data(self) -> dict[str, Any] | None:
        return self.intelligence.as_dict() if self.intelligence is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "session_id": self.session_id,
            "session_id_missing_reason": self.session_id_missing_reason,
            "session_id_source": "tinyfish_agent_api" if self.session_id else None,
            "run_id": self.run_id,
            "run_ids": list(self.run_ids),
            "attempts": self.attempts,
            "status": self.status,
            "target_url": self.target_url,
            "competitor": self.competitor,
            "objective": self.objective,
            "mock": self.mock,
            "duration_seconds": self.duration_seconds,
            "errors": list(self.errors),
            "last_error": self.last_error,
            "data": self.data,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _site_root(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url


def _as_items(value: Any, limit: int) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        return (value,)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    items = tuple(item for item in value[:limit] if isinstance(item, Mapping))
    return items


def _mark_unverified(claims: list[str], label: str) -> None:
    text = f"{label} was reported but not verified on the page."
    if text not in claims:
        claims.append(text)


def parse_competitor_intelligence(
    payload: Any,
    plan: WebAgentPlan,
) -> CompetitorIntelligence:
    """Parse a raw TinyFish result into a defensive structured object.

    Raises :class:`TinyFishAgentError` when no JSON object can be recovered.
    """

    data = coerce_json_object(payload)
    for _ in range(3):
        nested = data.get("result")
        if isinstance(nested, str):
            nested = coerce_json_object(nested)
        if not isinstance(nested, Mapping) or not nested:
            break
        if any(key in data for key in ("page_ready", "pricing", "features", "sources", "summary")):
            break
        data = dict(nested)

    if not data:
        raise TinyFishAgentError("TinyFish returned an empty or malformed result", retryable=False)

    final_url = normalize_source_url(data.get("final_url"), plan.url) or plan.url
    website = normalize_source_url(data.get("website"), plan.url) or _site_root(plan.url)
    competitor_name = as_text(data.get("competitor_name"), 120) or plan.competitor
    summary = as_text(data.get("summary"), 2000)
    notes = as_text(data.get("notes"), 2000)

    sources: list[SourceReference] = []
    for item in _as_items(data.get("sources"), 30):
        url = normalize_source_url(item.get("url") or item.get("source_url"), plan.url)
        if not url:
            continue
        sources.append(
            SourceReference(
                url=url,
                title=as_text(item.get("title"), 200),
                retrieved_at=as_text(item.get("retrieved_at"), 80) or _now_iso(),
            )
        )

    pricing: list[PricingPlan] = []
    for item in _as_items(data.get("pricing"), 50):
        name = as_text(item.get("plan_name") or item.get("name"), 200)
        if not name:
            continue
        pricing.append(
            PricingPlan(
                plan_name=name,
                price=as_text(item.get("price"), 100),
                currency=as_text(item.get("currency"), 20),
                billing_period=normalize_billing_period(item.get("billing_period")),
                description=as_text(item.get("description"), 1000),
                source_url=normalize_source_url(item.get("source_url") or item.get("url"), final_url) or final_url,
                verified=coerce_bool(item.get("verified"), False),
            )
        )

    features: list[FeatureItem] = []
    for item in _as_items(data.get("features"), 100):
        name = as_text(item.get("name") or item.get("feature"), 200)
        if not name:
            continue
        features.append(
            FeatureItem(
                name=name,
                category=as_text(item.get("category"), 120),
                description=as_text(item.get("description"), 1500),
                plans=as_string_list(item.get("plans"), limit=20, max_length=120),
                source_url=normalize_source_url(item.get("source_url") or item.get("url"), final_url) or final_url,
                verified=coerce_bool(item.get("verified"), False),
            )
        )

    product_details: list[ProductDetail] = []
    for item in _as_items(data.get("product_details"), 50):
        name = as_text(item.get("name") or item.get("product"), 200)
        if not name:
            continue
        product_details.append(
            ProductDetail(
                name=name,
                detail=as_text(item.get("detail") or item.get("description"), 2000),
                source_url=normalize_source_url(item.get("source_url") or item.get("url"), final_url) or final_url,
                verified=coerce_bool(item.get("verified"), False),
            )
        )

    announcements: list[Announcement] = []
    for item in _as_items(data.get("announcements"), 30):
        title = as_text(item.get("title") or item.get("name"), 300)
        if not title:
            continue
        announcements.append(
            Announcement(
                title=title,
                date=as_text(item.get("date"), 80),
                summary=as_text(item.get("summary") or item.get("description"), 2000),
                source_url=normalize_source_url(item.get("source_url") or item.get("url"), final_url) or final_url,
                verified=coerce_bool(item.get("verified"), False),
            )
        )

    actions: list[ActionResult] = []
    for item in _as_items(data.get("actions"), 20):
        name = normalize_action_name(item.get("action") or item.get("name"))
        if not name:
            continue
        actions.append(
            ActionResult(
                action=name,
                status=ActionStatus(normalize_action_status(item.get("status"))),
                evidence=as_text(item.get("evidence") or item.get("reason"), 500),
            )
        )

    missing_data = list(as_string_list(data.get("missing_data"), limit=30, max_length=500))
    unverified_claims = list(as_string_list(data.get("unverified_claims"), limit=30, max_length=500))
    obstacles = list(as_string_list(data.get("obstacles"), limit=20, max_length=500))

    focus = set(plan.focus_areas)
    if FocusArea.PRICING in focus and not pricing and "No verified pricing information was found." not in missing_data:
        missing_data.append("No verified pricing information was found.")
    if FocusArea.FEATURES in focus and not features and "No verified feature information was found." not in missing_data:
        missing_data.append("No verified feature information was found.")
    if FocusArea.PRODUCT_DETAILS in focus and not product_details and "No verified product details were found." not in missing_data:
        missing_data.append("No verified product details were found.")
    if FocusArea.ANNOUNCEMENTS in focus and not announcements and "No verified announcements were found." not in missing_data:
        missing_data.append("No verified announcements were found.")

    for item in pricing:
        if not item.verified:
            _mark_unverified(unverified_claims, f"Price for {item.plan_name}")
    for item in features:
        if not item.verified:
            _mark_unverified(unverified_claims, f"Feature {item.name}")
    for item in product_details:
        if not item.verified:
            _mark_unverified(unverified_claims, f"Product detail {item.name}")
    for item in announcements:
        if not item.verified:
            _mark_unverified(unverified_claims, f"Announcement {item.title}")

    if not sources and coerce_bool(data.get("page_ready"), False):
        sources.append(SourceReference(url=final_url, title=competitor_name, retrieved_at=_now_iso()))

    page_ready = coerce_bool(data.get("page_ready"), False)
    item_count = len(pricing) + len(features) + len(product_details) + len(announcements)
    status = normalize_extraction_status(
        data.get("status"),
        page_ready=page_ready,
        has_sources=bool(sources),
        item_count=item_count,
    )

    return CompetitorIntelligence(
        page_ready=page_ready,
        status=status,
        final_url=final_url,
        competitor_name=competitor_name,
        website=website,
        summary=summary,
        pricing=tuple(pricing),
        features=tuple(features),
        product_details=tuple(product_details),
        announcements=tuple(announcements),
        sources=tuple(sources),
        actions=tuple(actions),
        missing_data=tuple(dedupe(missing_data)),
        unverified_claims=tuple(dedupe(unverified_claims)),
        obstacles=tuple(dedupe(obstacles)),
        notes=notes,
        raw=dict(data),
    )


def is_extraction_complete(intelligence: CompetitorIntelligence) -> bool:
    return (
        intelligence.page_ready
        and intelligence.status == "success"
        and bool(intelligence.sources)
        and intelligence.item_count > 0
    )


def _api_error_details(body: Any) -> tuple[str | None, str | None, float | None]:
    if not isinstance(body, Mapping):
        return None, None, None

    error = body.get("error")
    if isinstance(error, Mapping):
        return (
            as_text(error.get("code"), 80) or None,
            as_text(error.get("message") or error.get("detail"), 500) or None,
            parse_retry_after(error.get("retry_after")),
        )
    if error is not None and not isinstance(error, Mapping):
        return None, as_text(error, 500) or None, parse_retry_after(body.get("retry_after"))

    return (
        as_text(body.get("code"), 80) or None,
        as_text(body.get("message") or body.get("detail"), 500) or None,
        parse_retry_after(body.get("retry_after")),
    )


def _run_error_payload(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if value is None:
        return None
    return {"message": as_text(value, 500)}


def _snapshot_from_payload(data: Mapping[str, Any]) -> RunSnapshot:
    raw_steps = data.get("steps")
    steps: tuple[Mapping[str, Any], ...] = ()
    if isinstance(raw_steps, Sequence) and not isinstance(raw_steps, (str, bytes, bytearray)):
        steps = tuple(step for step in raw_steps if isinstance(step, Mapping))

    return RunSnapshot(
        run_id=as_text(data.get("run_id"), 120),
        status=normalize_run_status(data.get("status")),
        result=data.get("result"),
        error=_run_error_payload(data.get("error")),
        steps=steps,
        streaming_url=normalize_source_url(data.get("streaming_url"), data.get("run_url") or "") or None,
        session_id=extract_session_id(data),
        raw=dict(data),
    )


def _format_error(exc: TinyFishAgentError, api_key: str = "") -> str:
    code = f" [{exc.code}]" if exc.code else ""
    status = f" (HTTP {exc.status_code})" if exc.status_code else ""
    return redact_text(f"{exc.__class__.__name__}{code}{status}: {exc}", api_key)


def _format_run_error(error: Mapping[str, Any]) -> str:
    code = as_text(error.get("code"), 80) or "RUN_FAILED"
    category = as_text(error.get("category"), 40) or "UNKNOWN"
    message = as_text(error.get("message"), 500) or "no error message"
    return f"{code} ({category}): {message}"


def _mock_intelligence(plan: WebAgentPlan) -> CompetitorIntelligence:
    now = _now_iso()
    pricing = [
        PricingPlan(
            plan_name="Starter",
            price="$0",
            currency="USD",
            billing_period="monthly",
            description="Mock free tier.",
            source_url=plan.url,
            verified=False,
        ),
        PricingPlan(
            plan_name="Growth",
            price="$49",
            currency="USD",
            billing_period="annual",
            description="Mock annual plan price.",
            source_url=plan.url,
            verified=False,
        ),
    ]
    features = [
        FeatureItem(
            name="Advanced analytics",
            category="Analytics",
            description="Mock feature entry.",
            plans=("Growth",),
            source_url=plan.url,
            verified=False,
        )
    ]
    details = [
        ProductDetail(
            name=plan.competitor,
            detail="Mock product detail. No live website request was made.",
            source_url=plan.url,
            verified=False,
        )
    ]
    announcements = [
        Announcement(
            title="Mock product update",
            date="",
            summary="Mock announcement. No live date was observed.",
            source_url=plan.url,
            verified=False,
        )
    ]
    return CompetitorIntelligence(
        page_ready=True,
        status="success",
        final_url=plan.url,
        competitor_name=plan.competitor,
        website=_site_root(plan.url),
        summary="MOCK DATA: no request was sent to TinyFish.",
        pricing=tuple(pricing),
        features=tuple(features),
        product_details=tuple(details),
        announcements=tuple(announcements),
        sources=(SourceReference(url=plan.url, title="Mock source", retrieved_at=now),),
        actions=(),
        missing_data=("Mock mode does not contain live competitor data.",),
        unverified_claims=("All mock values are simulated and must not be treated as verified.",),
        obstacles=(),
        notes="Mock mode. No network request was made.",
        raw={"mock": True},
    )


class TinyFishAgentClient:
    """Reusable async client for TinyFish Agent runs."""

    def __init__(
        self,
        settings: TinyFishSettings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or TinyFishSettings.from_env()
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.http_timeout),
            follow_redirects=True,
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.settings.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.settings.user_agent,
        }

    async def __aenter__(self) -> TinyFishAgentClient:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_http and not self._http.is_closed:
            await self._http.aclose()

    def __repr__(self) -> str:
        return (
            f"TinyFishAgentClient(base_url={self.settings.base_url!r}, "
            f"max_attempts={self.settings.max_attempts}, mock={self.settings.mock})"
        )

    async def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.settings.mock:
            raise TinyFishConfigError("real API requests are disabled in mock mode")

        url = f"{self.settings.base_url}{path}"
        request_kwargs: dict[str, Any] = {"headers": self._headers}
        if payload is not None:
            request_kwargs["json"] = payload

        try:
            response = await self._http.request(method, url, **request_kwargs)
        except httpx.TimeoutException as exc:
            raise TinyFishTimeoutError("TinyFish API request timed out", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise TinyFishNetworkError(
                f"TinyFish API request failed: {exc.__class__.__name__}",
                retryable=True,
            ) from exc

        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = None

        code, message, retry_after = _api_error_details(body)
        header_retry_after = parse_retry_after(response.headers.get("Retry-After"))
        if retry_after is None:
            retry_after = header_retry_after
        fallback_message = redact_text(as_text(response.text, 300) or f"HTTP {status}", self.settings.api_key)

        if status == 401:
            raise TinyFishAuthError(
                message or "TinyFish rejected the API key",
                code=code or "INVALID_API_KEY",
                status_code=status,
            )
        if status == 402:
            raise TinyFishAgentError(
                message or "TinyFish account has insufficient credits",
                code=code or "INSUFFICIENT_CREDITS",
                status_code=status,
                retryable=False,
            )
        if status == 403:
            raise TinyFishAgentError(
                message or "TinyFish denied access to this run",
                code=code or "FORBIDDEN",
                status_code=status,
                retryable=False,
            )
        if status in {400, 422}:
            raise TinyFishValidationError(
                message or fallback_message,
                code=code or "INVALID_INPUT",
                status_code=status,
            )
        if status == 404:
            raise TinyFishAgentError(
                message or "TinyFish resource not found",
                code=code or "NOT_FOUND",
                status_code=status,
                retryable=False,
            )
        if status in _RETRYABLE_HTTP_STATUSES:
            exception_type = TinyFishRateLimitError if status == 429 else TinyFishAgentError
            raise exception_type(
                message or "TinyFish temporarily unavailable",
                code=code or "RATE_LIMIT_EXCEEDED",
                status_code=status,
                retryable=True,
                retry_after=retry_after,
            )
        if status >= 500:
            raise TinyFishServerError(
                message or "TinyFish server error",
                code=code or "INTERNAL_ERROR",
                status_code=status,
                retryable=True,
                retry_after=retry_after,
            )
        if status >= 400:
            raise TinyFishAgentError(
                message or fallback_message,
                code=code,
                status_code=status,
                retryable=False,
            )

        if not isinstance(body, Mapping):
            raise TinyFishAgentError(
                "TinyFish returned a non-JSON or malformed response",
                status_code=status,
                retryable=False,
            )
        return dict(body)

    def _build_run_payload(
        self,
        plan: WebAgentPlan,
        goal: str,
        output_schema: Mapping[str, Any],
        browser_profile: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": plan.url,
            "goal": goal,
            "output_schema": dict(output_schema),
            "browser_profile": browser_profile,
            "api_integration": "nexus-intel",
        }

        if self.settings.use_proxy:
            payload["proxy_config"] = {
                "enabled": True,
                "type": "tinyfish",
                "country_code": self.settings.country_code,
            }

        agent_config: dict[str, Any] = {
            "max_duration_seconds": plan.max_duration_seconds,
        }
        if plan.max_steps is not None:
            agent_config["max_steps"] = plan.max_steps
        payload["agent_config"] = agent_config
        return payload

    async def start_run(
        self,
        plan: WebAgentPlan,
        goal: str,
        output_schema: Mapping[str, Any],
        *,
        browser_profile: str | None = None,
    ) -> RunStart:
        profile = browser_profile or plan.browser_profile
        payload = self._build_run_payload(plan, goal, output_schema, profile)
        data = await self._request("POST", RUN_ASYNC_PATH, payload)

        error = _run_error_payload(data.get("error"))
        if error is not None:
            raise TinyFishRunError(
                f"TinyFish rejected the run: {as_text(error.get('message'), 500) or 'unknown error'}",
                code=as_text(error.get("code"), 80) or None,
                retryable=is_retryable_run_error(error),
                retry_after=parse_retry_after(error.get("retry_after")),
            )

        run_id = as_text(data.get("run_id"), 120)
        if not run_id:
            raise TinyFishAgentError("TinyFish did not return a run_id", retryable=False)

        session_id = extract_session_id(data)
        logger.info(
            "Started TinyFish agent run %s for %s (profile=%s, session=%s)",
            run_id,
            plan.url,
            profile,
            session_id or "not provided",
        )
        return RunStart(run_id=run_id, session_id=session_id, raw=dict(data))

    async def get_run(self, run_id: str, *, screenshots: str = "none") -> RunSnapshot:
        safe_run_id = quote(as_text(run_id, 200), safe="")
        if not safe_run_id:
            raise ValueError("run_id must be a non-empty string")
        if screenshots not in {"none", "url", "base64"}:
            raise ValueError("screenshots must be 'none', 'url', or 'base64'")

        data = await self._request("GET", f"/v1/runs/{safe_run_id}?screenshots={screenshots}")
        return _snapshot_from_payload(data)

    async def cancel_run(self, run_id: str) -> bool:
        safe_run_id = quote(as_text(run_id, 200), safe="")
        if not safe_run_id:
            raise ValueError("run_id must be a non-empty string")
        data = await self._request("POST", f"/v1/runs/{safe_run_id}/cancel")
        return normalize_run_status(data.get("status")) == "CANCELLED"

    async def _cancel_quietly(self, run_id: str) -> None:
        try:
            await self.cancel_run(run_id)
        except TinyFishAgentError as exc:
            logger.warning("Could not cancel TinyFish run %s: %s", run_id, _format_error(exc, self.settings.api_key))

    async def wait_for_run(
        self,
        run_id: str,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> RunSnapshot:
        wait_seconds = clamp(float(timeout or self.settings.run_timeout), 0.1, 600.0)
        interval = clamp(float(poll_interval or self.settings.poll_interval), 0.01, 30.0)
        deadline = time.monotonic() + wait_seconds
        last_poll_error: TinyFishAgentError | None = None

        while True:
            try:
                snapshot = await self.get_run(run_id)
            except TinyFishAgentError as exc:
                if not exc.retryable:
                    raise
                last_poll_error = exc
                logger.warning("Polling TinyFish run %s failed: %s", run_id, _format_error(exc, self.settings.api_key))
            else:
                if snapshot.is_terminal:
                    logger.info("TinyFish run %s finished with status %s", run_id, snapshot.status)
                    return snapshot

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                await self._cancel_quietly(run_id)
                detail = (
                    f" (last polling error: {_format_error(last_poll_error, self.settings.api_key)})"
                    if last_poll_error
                    else ""
                )
                raise TinyFishTimeoutError(
                    f"TinyFish run {run_id} did not finish within {wait_seconds:.1f}s{detail}",
                    retryable=True,
                )
            await asyncio.sleep(min(interval, remaining))

    def _browser_profile_for_attempt(self, plan: WebAgentPlan, attempt: int, force_stealth: bool = False) -> str:
        base = plan.browser_profile or self.settings.browser_profile
        if base == "stealth":
            return base
        if not self.settings.enable_stealth_escalation:
            return base
        if attempt > 1 and (force_stealth or attempt >= self.settings.max_attempts):
            return "stealth"
        return base

    def _retry_delay(self, attempt: int, exc: TinyFishAgentError | None = None) -> float:
        if exc is not None and exc.retry_after is not None:
            return clamp(exc.retry_after, 0.0, 60.0)
        return compute_backoff(
            attempt,
            base=self.settings.retry_base_seconds,
            cap=self.settings.retry_cap_seconds,
        )

    def _build_result(
        self,
        *,
        started_at: float,
        success: bool,
        plan: WebAgentPlan,
        intelligence: CompetitorIntelligence | None,
        session_id: str | None,
        run_ids: Sequence[str],
        attempts: int,
        errors: Sequence[str],
        last_error: str | None,
    ) -> WebAgentResult:
        missing_reason = None
        if session_id is None:
            missing_reason = MOCK_SESSION_MISSING_REASON if self.settings.mock else SESSION_MISSING_REASON
        return WebAgentResult(
            success=success,
            session_id=session_id,
            session_id_missing_reason=missing_reason,
            run_id=run_ids[-1] if run_ids else None,
            run_ids=tuple(run_ids),
            attempts=attempts,
            status=intelligence.status if intelligence is not None else "failure",
            target_url=plan.url,
            competitor=plan.competitor,
            objective=plan.objective,
            intelligence=intelligence,
            errors=tuple(errors),
            last_error=last_error,
            duration_seconds=round(time.monotonic() - started_at, 3),
            mock=self.settings.mock,
        )

    async def extract(self, plan: WebAgentPlan) -> WebAgentResult:
        started_at = time.monotonic()

        if self.settings.mock:
            intelligence = _mock_intelligence(plan)
            run_id = f"mock_run_{hashlib.sha1(plan.url.encode('utf-8')).hexdigest()[:12]}"
            return self._build_result(
                started_at=started_at,
                success=True,
                plan=plan,
                intelligence=intelligence,
                session_id=None,
                run_ids=(run_id,),
                attempts=0,
                errors=(),
                last_error=None,
            )

        run_ids: list[str] = []
        errors: list[str] = []
        last_intelligence: CompetitorIntelligence | None = None
        last_error: str | None = None
        session_id: str | None = None
        force_stealth = False
        attempts_tried = 0

        for attempt in range(1, self.settings.max_attempts + 1):
            attempts_tried = attempt
            prompt = build_prompt_spec(plan, attempt=attempt, previous_errors=errors)
            profile = self._browser_profile_for_attempt(plan, attempt, force_stealth)

            try:
                started = await self.start_run(
                    plan,
                    prompt.goal,
                    prompt.output_schema,
                    browser_profile=profile,
                )
            except TinyFishAgentError as exc:
                last_error = _format_error(exc, self.settings.api_key)
                errors.append(last_error)
                if not exc.retryable or attempt >= self.settings.max_attempts:
                    break
                await asyncio.sleep(self._retry_delay(attempt, exc))
                continue

            run_ids.append(started.run_id)
            if started.session_id:
                session_id = started.session_id

            try:
                snapshot = await self.wait_for_run(started.run_id)
            except TinyFishAgentError as exc:
                last_error = _format_error(exc, self.settings.api_key)
                errors.append(last_error)
                if not exc.retryable or attempt >= self.settings.max_attempts:
                    break
                await asyncio.sleep(self._retry_delay(attempt, exc))
                continue

            if snapshot.session_id:
                session_id = snapshot.session_id

            if snapshot.status == "COMPLETED":
                try:
                    intelligence = parse_competitor_intelligence(snapshot.result, plan)
                except TinyFishAgentError as exc:
                    last_error = _format_error(exc, self.settings.api_key)
                    errors.append(last_error)
                    if attempt >= self.settings.max_attempts:
                        break
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue

                last_intelligence = intelligence
                if is_extraction_complete(intelligence):
                    logger.info(
                        "TinyFish extraction succeeded for %s in %d attempt(s)",
                        plan.url,
                        attempt,
                    )
                    return self._build_result(
                        started_at=started_at,
                        success=True,
                        plan=plan,
                        intelligence=intelligence,
                        session_id=session_id,
                        run_ids=run_ids,
                        attempts=attempt,
                        errors=errors,
                        last_error=None,
                    )

                last_error = (
                    "Extraction incomplete "
                    f"(page_ready={intelligence.page_ready}, status={intelligence.status}, "
                    f"items={intelligence.item_count}, sources={len(intelligence.sources)})"
                )
                errors.append(last_error)
                force_stealth = contains_blocked_signal(
                    intelligence.notes,
                    *intelligence.obstacles,
                    *intelligence.missing_data,
                )
                if attempt >= self.settings.max_attempts:
                    break
                await asyncio.sleep(self._retry_delay(attempt))
                continue

            if snapshot.status == "CANCELLED":
                last_error = "TinyFish run was cancelled"
                errors.append(last_error)
                break

            error_payload = snapshot.error or {}
            last_error = _format_run_error(error_payload)
            errors.append(last_error)
            force_stealth = contains_blocked_signal(
                error_payload.get("code"),
                error_payload.get("category"),
                error_payload.get("message"),
            )
            if attempt >= self.settings.max_attempts or not is_retryable_run_error(error_payload):
                break

            delay = parse_retry_after(error_payload.get("retry_after"))
            if delay is None:
                delay = self._retry_delay(attempt)
            await asyncio.sleep(clamp(delay, 0.0, 60.0))

        return self._build_result(
            started_at=started_at,
            success=False,
            plan=plan,
            intelligence=last_intelligence,
            session_id=session_id,
            run_ids=run_ids,
            attempts=attempts_tried,
            errors=errors,
            last_error=last_error,
        )

    async def run_web_agent(self, plan: WebAgentPlan) -> WebAgentResult:
        return await self.extract(plan)


def resolve_target(competitor_or_url: str, website_url: str | None = None) -> tuple[str, str]:
    """Return ``(url, competitor_name)`` from a URL/domain or name plus URL."""

    value = as_text(competitor_or_url, 500)
    if not value:
        raise ValueError("competitor name or website URL is required")

    if website_url:
        url = normalize_url(website_url)
        competitor = "" if looks_like_url(value) else value
        return url, competitor

    if looks_like_url(value):
        url = normalize_url(value)
        return url, ""

    raise ValueError(
        "a website URL is required when competitor_or_url is a name; "
        "pass website_url='https://example.com'"
    )


async def run_web_agent(
    competitor_or_url: str,
    objective: str | None = None,
    *,
    website_url: str | None = None,
    focus_areas: Sequence[FocusArea | str] | None = None,
    actions: Sequence[Any] | None = None,
    mock: bool | None = None,
    settings: TinyFishSettings | None = None,
    client: TinyFishAgentClient | None = None,
) -> WebAgentResult:
    """Navigate a competitor site and return structured intelligence.

    ``session_id`` is exposed at the top level of :class:`WebAgentResult` and its
    ``as_dict()`` output. It is populated only when TinyFish explicitly returns a
    browser session identifier. The current Agent API does not, so the field is
    ``None`` and ``session_id_missing_reason`` explains the limitation.
    """

    url, competitor = resolve_target(competitor_or_url, website_url)
    plan = WebAgentPlan.for_target(
        url,
        competitor,
        objective=objective or DEFAULT_OBJECTIVE,
        focus_areas=focus_areas,
        actions=actions,
    )

    if client is not None:
        return await client.extract(plan)

    resolved_settings = settings
    if resolved_settings is None:
        resolved_settings = TinyFishSettings.from_env(mock=mock)
    elif mock is not None and resolved_settings.mock != mock:
        resolved_settings = replace(resolved_settings, mock=mock)

    async with TinyFishAgentClient(settings=resolved_settings) as active_client:
        return await active_client.extract(plan)


run_competitor_extraction = run_web_agent
