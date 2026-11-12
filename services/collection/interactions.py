"""Bounded, non-destructive interaction with pricing/feature pages.

Nothing here blindly clicks every button. Each interaction is scoped to a
category, capped by ``max_interactions`` and protected by a guard list of
destructive actions (buy, trial, login, contact sales, checkout, ...).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("nexus_intel.collection.interactions")

_DESTRUCTIVE_RE = re.compile(
    r"\b(?:buy|purchase|checkout|add\s+to\s+cart|start\s+(?:free\s+)?trial|"
    r"free\s+trial|try\s+for\s+free|sign\s*up|register|log\s*in|sign\s*in|"
    r"contact\s+sales|talk\s+to\s+sales|book\s+a\s+demo|request\s+a\s+demo|"
    r"subscribe\s+now|upgrade\s+now|download|install)\b",
    re.IGNORECASE,
)
_ANNUAL_RE = re.compile(
    r"\b(?:annual|annually|yearly|per\s+year|billed\s+annually|pay\s+yearly|save\s+\d+%)\b",
    re.IGNORECASE,
)
_MONTHLY_RE = re.compile(r"\b(?:monthly|per\s+month|billed\s+monthly|pay\s+monthly)\b", re.IGNORECASE)
_EXPAND_RE = re.compile(
    r"\b(?:show\s+more|see\s+all|view\s+all|show\s+all|more\s+details|"
    r"expand|compare\s+(?:all\s+)?(?:plans|features)|all\s+features|"
    r"view\s+features|show\s+features|learn\s+more)\b",
    re.IGNORECASE,
)
_COOKIE_RE = re.compile(r"\b(?:accept\s+all|reject\s+all|accept\s+cookies|close|dismiss|got\s+it|no\s+thanks)\b", re.IGNORECASE)


def _safe_text(value: Any, limit: int = 120) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


async def _first_visible(locator: Any) -> Any | None:
    try:
        count = await locator.count()
    except Exception:
        return None
    for index in range(min(count, 6)):
        candidate = locator.nth(index)
        try:
            if await candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


async def _click(locator: Any, *, timeout_ms: int) -> bool:
    try:
        await locator.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass
    try:
        await locator.click(timeout=timeout_ms, no_wait_after=True)
        return True
    except Exception:
        try:
            await locator.click(timeout=timeout_ms, force=True, no_wait_after=True)
            return True
        except Exception:
            return False


async def _settle(page: Any, timeout_ms: int) -> None:
    try:
        await page.wait_for_timeout(min(1200, timeout_ms))
    except Exception:
        pass


async def dismiss_overlays(page: Any, settings: Any) -> list[str]:
    """Close cookie banners / marketing popups when a visible control exists."""
    actions: list[str] = []
    for role in ("button", "link"):
        locator = page.get_by_role(role, name=_COOKIE_RE)
        candidate = await _first_visible(locator)
        if candidate is not None:
            text = _safe_text(await candidate.inner_text() if hasattr(candidate, "inner_text") else "")
            if _DESTRUCTIVE_RE.search(text):
                continue
            if await _click(candidate, timeout_ms=settings.interaction_timeout_ms):
                actions.append(f"dismissed overlay: {text or role}")
                await _settle(page, settings.interaction_timeout_ms)
                break
    return actions


async def select_billing_state(page: Any, settings: Any, target: str) -> str | None:
    """Click an Annual/Monthly billing control; return the label that was clicked."""
    pattern = _ANNUAL_RE if target == "annual" else _MONTHLY_RE
    published = getattr(page, "locator", None)
    if published is None:
        return None
    for role in ("button", "tab", "radio", "link"):
        locator = page.get_by_role(role, name=pattern)
        candidate = await _first_visible(locator)
        if candidate is None:
            continue
        try:
            text = _safe_text(await candidate.inner_text())
        except Exception:
            text = target
        if _DESTRUCTIVE_RE.search(text):
            continue
        if await _click(candidate, timeout_ms=settings.interaction_timeout_ms):
            await _settle(page, settings.interaction_timeout_ms)
            return text or target
    # Fallback: text search inside the visible page.
    locator = page.get_by_text(pattern, exact=False)
    candidate = await _first_visible(locator)
    if candidate is not None:
        try:
            text = _safe_text(await candidate.inner_text())
        except Exception:
            text = target
        if not _DESTRUCTIVE_RE.search(text) and await _click(candidate, timeout_ms=settings.interaction_timeout_ms):
            await _settle(page, settings.interaction_timeout_ms)
            return text or target
    return None


async def expand_content(page: Any, settings: Any, *, limit: int | None = None) -> list[str]:
    """Expand accordions/feature lists with a hard interaction budget."""
    budget = min(limit or settings.max_interactions, settings.max_interactions)
    actions: list[str] = []
    clicked: set[str] = set()

    candidates: list[Any] = []
    for role in ("button", "link", "tab"):
        locator = page.get_by_role(role, name=_EXPAND_RE)
        try:
            count = await locator.count()
        except Exception:
            count = 0
        for index in range(min(count, budget)):
            candidates.append(locator.nth(index))
    try:
        collapsed = page.locator("[aria-expanded='false']")
        count = await collapsed.count()
        for index in range(min(count, budget)):
            candidates.append(collapsed.nth(index))
    except Exception:
        pass
    try:
        summaries = page.locator("details:not([open]) > summary")
        count = await summaries.count()
        for index in range(min(count, budget)):
            candidates.append(summaries.nth(index))
    except Exception:
        pass

    for candidate in candidates:
        if len(actions) >= budget:
            break
        try:
            if not await candidate.is_visible():
                continue
            text = _safe_text(await candidate.inner_text())
        except Exception:
            continue
        key = text.lower()
        if key in clicked:
            continue
        if _DESTRUCTIVE_RE.search(text):
            continue
        clicked.add(key)
        if await _click(candidate, timeout_ms=settings.interaction_timeout_ms):
            actions.append(f"expanded: {text or 'collapsed section'}")
            await _settle(page, settings.interaction_timeout_ms)
    return actions


async def interact_for_page(
    page: Any,
    settings: Any,
    categories: list[str],
    *,
    on_snapshot: Any = None,
) -> tuple[list[str], list[str]]:
    """Run category-appropriate interactions.

    Returns ``(actions, billing_labels)``. ``on_snapshot`` is an optional async
    callback ``(billing_state, actions)`` used to capture intermediate states.
    """
    category_set = set(categories or [])
    actions: list[str] = []
    billing_labels: list[str] = []

    actions.extend(await dismiss_overlays(page, settings))

    if "pricing" in category_set:
        if on_snapshot is not None:
            await on_snapshot("default", list(actions))
        if settings.capture_billing_states:
            annual_label = await select_billing_state(page, settings, "annual")
            if annual_label:
                billing_labels.append(annual_label)
                actions.append(f"selected billing: {annual_label}")
                if on_snapshot is not None:
                    await on_snapshot("annual", list(actions))
                # Best-effort restore to monthly so subsequent expansion starts
                # from the more common state (failure is harmless).
                monthly_label = await select_billing_state(page, settings, "monthly")
                if monthly_label and monthly_label not in billing_labels:
                    billing_labels.append(monthly_label)
        remaining = max(0, settings.max_interactions - len(actions))
        actions.extend(await expand_content(page, settings, limit=remaining))
        if on_snapshot is not None:
            await on_snapshot("default", list(actions))
    elif category_set & {"features", "product", "changelog", "announcements", "general", "blog"}:
        actions.extend(await expand_content(page, settings))
        if on_snapshot is not None:
            await on_snapshot("default", list(actions))

    return actions, billing_labels
