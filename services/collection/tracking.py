"""URL registry, incremental crawling, content hashing and change detection.

The pipeline stores one registry entry per (competitor, URL), immutable snapshots
per meaningful content hash, and structured change events. A MongoDB-backed
store is used when the database is available; an in-memory store keeps the
pipeline usable in tests, mock mode and offline environments.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from .cleaning import content_hash, stable_text
from .models import PageExtraction, PageSnapshot, iso_now

logger = logging.getLogger("nexus_intel.collection.tracking")


class TrackingConflictError(RuntimeError):
    """Raised when a competitor already has an active collection run."""


class CompetitorRunGuard:
    """In-process guard preventing overlapping runs for one competitor."""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "CompetitorRunGuard":
        raise RuntimeError("Use acquire(competitor) instead")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def acquire(self, competitor: str) -> None:
        async with self._lock:
            if competitor in self._active:
                raise TrackingConflictError(
                    f"A tracking run for {competitor!r} is already in progress."
                )
            self._active.add(competitor)

    async def release(self, competitor: str) -> None:
        async with self._lock:
            self._active.discard(competitor)

    def is_active(self, competitor: str) -> bool:
        return competitor in self._active


_GLOBAL_GUARD = CompetitorRunGuard()


def global_run_guard() -> CompetitorRunGuard:
    return _GLOBAL_GUARD


@dataclass
class TrackingDecision:
    should_crawl: bool
    reason: str
    cached_snapshots: list[PageSnapshot] = field(default_factory=list)
    registry: Optional[dict[str, Any]] = None


@dataclass
class TrackingOutcome:
    status: str  # new | updated | unchanged | reused | failed
    content_hash: str
    text_hash: str
    changes: list[dict[str, Any]] = field(default_factory=list)


class TrackingStore(Protocol):
    async def get_page(self, competitor: str, url: str) -> Optional[dict[str, Any]]: ...
    async def upsert_page(self, competitor: str, url: str, values: dict[str, Any]) -> None: ...
    async def latest_snapshot(self, competitor: str, url: str) -> Optional[dict[str, Any]]: ...
    async def snapshots_for_structured_hash(
        self, competitor: str, url: str, structured_hash: str
    ) -> list[dict[str, Any]]: ...
    async def save_snapshot(self, record: dict[str, Any]) -> None: ...
    async def record_change(self, event: dict[str, Any]) -> None: ...
    async def list_changes(self, competitor: str, limit: int = 100) -> list[dict[str, Any]]: ...


class InMemoryTrackingStore:
    def __init__(self) -> None:
        self.pages: dict[tuple[str, str], dict[str, Any]] = {}
        self.snapshots: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.changes: list[dict[str, Any]] = []

    async def get_page(self, competitor: str, url: str) -> Optional[dict[str, Any]]:
        value = self.pages.get((competitor, url))
        return dict(value) if value else None

    async def upsert_page(self, competitor: str, url: str, values: dict[str, Any]) -> None:
        key = (competitor, url)
        current = self.pages.get(key, {})
        current.update(values)
        current["competitor"] = competitor
        current["url"] = url
        self.pages[key] = current

    async def latest_snapshot(self, competitor: str, url: str) -> Optional[dict[str, Any]]:
        items = self.snapshots.get((competitor, url)) or []
        return dict(items[-1]) if items else None

    async def snapshots_for_structured_hash(
        self, competitor: str, url: str, structured_hash: str
    ) -> list[dict[str, Any]]:
        items = self.snapshots.get((competitor, url)) or []
        return [
            dict(item)
            for item in items
            if item.get("structured_hash") == structured_hash
        ]

    async def save_snapshot(self, record: dict[str, Any]) -> None:
        key = (record["competitor"], record["url"])
        bucket = self.snapshots.setdefault(key, [])
        if any(item.get("content_hash") == record.get("content_hash") for item in bucket):
            return
        bucket.append(dict(record))
        if len(bucket) > 20:
            del bucket[:-20]

    async def record_change(self, event: dict[str, Any]) -> None:
        self.changes.append(dict(event))

    async def list_changes(self, competitor: str, limit: int = 100) -> list[dict[str, Any]]:
        return [dict(e) for e in self.changes if e.get("competitor") == competitor][-limit:]


class MongoTrackingStore:
    """MongoDB-backed store; duck-typed so ``services`` does not import motor."""

    def __init__(
        self,
        database: Any,
        *,
        registry_collection: str = "page_registry",
        snapshots_collection: str = "page_snapshots",
        changes_collection: str = "change_events",
    ) -> None:
        self._db = database
        self._registry = database[registry_collection]
        self._snapshots = database[snapshots_collection]
        self._changes = database[changes_collection]
        self._indexed = False

    async def _ensure_indexes(self) -> None:
        if self._indexed:
            return
        from pymongo import ASCENDING, DESCENDING

        try:
            await self._registry.create_index(
                [("competitor", ASCENDING), ("url", ASCENDING)],
                unique=True,
                name="page_registry_competitor_url",
            )
            await self._registry.create_index(
                [("competitor", ASCENDING), ("last_crawl_at", DESCENDING)],
                name="page_registry_last_crawl",
            )
            await self._snapshots.create_index(
                [("competitor", ASCENDING), ("url", ASCENDING), ("content_hash", ASCENDING)],
                unique=True,
                name="page_snapshot_unique",
            )
            await self._changes.create_index(
                [("competitor", ASCENDING), ("detected_at", DESCENDING)],
                name="change_events_competitor_time",
            )
        except Exception as exc:  # pragma: no cover - index creation is best effort
            logger.warning("Could not ensure tracking indexes: %s", exc)
        self._indexed = True

    async def get_page(self, competitor: str, url: str) -> Optional[dict[str, Any]]:
        await self._ensure_indexes()
        return await self._registry.find_one({"competitor": competitor, "url": url})

    async def upsert_page(self, competitor: str, url: str, values: dict[str, Any]) -> None:
        await self._ensure_indexes()
        await self._registry.update_one(
            {"competitor": competitor, "url": url},
            {"$set": {**values, "competitor": competitor, "url": url}},
            upsert=True,
        )

    async def latest_snapshot(self, competitor: str, url: str) -> Optional[dict[str, Any]]:
        await self._ensure_indexes()
        cursor = self._snapshots.find({"competitor": competitor, "url": url}).sort("created_at", -1).limit(1)
        matches = await cursor.to_list(length=1)
        return matches[0] if matches else None

    async def snapshots_for_structured_hash(
        self, competitor: str, url: str, structured_hash: str
    ) -> list[dict[str, Any]]:
        await self._ensure_indexes()
        cursor = (
            self._snapshots.find(
                {
                    "competitor": competitor,
                    "url": url,
                    "structured_hash": structured_hash,
                }
            )
            .sort("created_at", 1)
            .limit(50)
        )
        return await cursor.to_list(length=50)

    async def save_snapshot(self, record: dict[str, Any]) -> None:
        await self._ensure_indexes()
        try:
            await self._snapshots.insert_one(dict(record))
        except Exception as exc:  # duplicate key is expected for unchanged content
            if "duplicate" not in str(exc).lower():
                logger.warning("Could not save page snapshot: %s", exc)

    async def record_change(self, event: dict[str, Any]) -> None:
        await self._ensure_indexes()
        await self._changes.insert_one(dict(event))

    async def list_changes(self, competitor: str, limit: int = 100) -> list[dict[str, Any]]:
        await self._ensure_indexes()
        cursor = (
            self._changes.find({"competitor": competitor})
            .sort("detected_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def snapshots_to_records(
    competitor: str,
    snapshots: list[PageSnapshot],
    *,
    store_full_text: bool = True,
) -> list[dict[str, Any]]:
    records = []
    for snapshot in snapshots:
        if snapshot.status != "success":
            continue
        digest = content_hash(stable_text(snapshot.text), snapshot.title, snapshot.billing_state)
        records.append(
            {
                "competitor": competitor,
                "url": snapshot.final_url or snapshot.url,
                "requested_url": snapshot.url,
                "title": snapshot.title,
                "billing_state": snapshot.billing_state,
                "content_hash": digest,
                "text_hash": content_hash(stable_text(snapshot.text)),
                "text": snapshot.text if store_full_text else "",
                "headings": list(snapshot.headings),
                "tables": list(snapshot.tables),
                "lists": list(snapshot.lists),
                "interactions": list(snapshot.interactions),
                "retrieval_method": snapshot.retrieval_method,
                "created_at": snapshot.retrieved_at,
            }
        )
    return records


def snapshots_from_record(record: dict[str, Any]) -> list[PageSnapshot]:
    return [
        PageSnapshot(
            url=record.get("requested_url") or record.get("url") or "",
            final_url=record.get("url") or "",
            title=record.get("title") or "",
            headings=list(record.get("headings") or []),
            text=record.get("text") or "",
            tables=list(record.get("tables") or []),
            lists=list(record.get("lists") or []),
            billing_state=record.get("billing_state") or "default",
            interactions=list(record.get("interactions") or []),
            retrieval_method=f"cache:{record.get('retrieval_method') or 'unknown'}",
            retrieved_at=record.get("created_at") or iso_now(),
        )
    ]


def _normalize_name(value: Any) -> str:
    return str(value or "").strip().lower()


def _plan_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    plans = payload.get("plans") or payload.get("pricing", {}).get("plans") or []
    for plan in plans:
        key = _normalize_name(plan.get("name") or plan.get("plan_name"))
        if key:
            index[key] = plan
    return index


def _feature_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for category in payload.get("categories") or []:
        for feature in category.get("features") or []:
            key = _normalize_name(feature.get("name"))
            if key:
                index[key] = feature
    return index


def detect_changes(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    competitor: str,
    url: str,
) -> list[dict[str, Any]]:
    """Compare structured extraction payloads. Content-only edits yield none."""
    events: list[dict[str, Any]] = []

    def event(kind: str, category: str, old: Any, new: Any, evidence: str, confidence: float = 0.9) -> None:
        events.append(
            {
                "competitor": competitor,
                "url": url,
                "change_type": kind,
                "category": category,
                "previous_value": old,
                "current_value": new,
                "detected_at": iso_now(),
                "evidence": evidence,
                "confidence": confidence,
            }
        )

    old_plans = _plan_index(previous.get("pricing") or {})
    new_plans = _plan_index(current.get("pricing") or {})
    for name in sorted(new_plans.keys() - old_plans.keys()):
        plan = new_plans[name]
        event(
            "plan_added",
            "pricing",
            None,
            {"name": plan.get("name") or name, "price": plan.get("price_display") or plan.get("price")},
            f"Plan {name!r} appears in the current snapshot but not the previous one.",
        )
    for name in sorted(old_plans.keys() - new_plans.keys()):
        plan = old_plans[name]
        event(
            "plan_removed",
            "pricing",
            {"name": plan.get("name") or name, "price": plan.get("price_display") or plan.get("price")},
            None,
            f"Plan {name!r} was present previously and is now absent.",
        )
    for name in sorted(old_plans.keys() & new_plans.keys()):
        old = old_plans[name]
        new = new_plans[name]
        old_price = old.get("price")
        new_price = new.get("price")
        if old_price != new_price:
            event(
                "price_changed",
                "pricing",
                old.get("price_display") or old_price,
                new.get("price_display") or new_price,
                f"Price for plan {name!r} changed.",
            )
        old_period = old.get("billing_period")
        new_period = new.get("billing_period")
        if old_period != new_period:
            event(
                "billing_changed",
                "pricing",
                old_period,
                new_period,
                f"Billing period for plan {name!r} changed.",
            )
        old_features = {_normalize_name(f) for f in old.get("included_features") or []}
        new_features = {_normalize_name(f) for f in new.get("included_features") or []}
        for feature in sorted(new_features - old_features):
            event(
                "plan_feature_added",
                "pricing",
                None,
                feature,
                f"Feature {feature!r} added to plan {name!r}.",
                0.8,
            )
        for feature in sorted(old_features - new_features):
            event(
                "plan_feature_removed",
                "pricing",
                feature,
                None,
                f"Feature {feature!r} removed from plan {name!r}.",
                0.8,
            )

    old_features = _feature_index(previous.get("features") or {})
    new_features = _feature_index(current.get("features") or {})
    for name in sorted(new_features.keys() - old_features.keys()):
        event(
            "feature_added",
            "features",
            None,
            new_features[name].get("name") or name,
            f"Feature {name!r} is newly present.",
            0.8,
        )
    for name in sorted(old_features.keys() - new_features.keys()):
        event(
            "feature_removed",
            "features",
            old_features[name].get("name") or name,
            None,
            f"Feature {name!r} is no longer present.",
            0.7,
        )
    for name in sorted(old_features.keys() & new_features.keys()):
        old = old_features[name]
        new = new_features[name]
        if old.get("description") != new.get("description") or old.get("support") != new.get("support"):
            event(
                "feature_changed",
                "features",
                old.get("description") or old.get("support"),
                new.get("description") or new.get("support"),
                f"Feature {name!r} description/support changed.",
                0.7,
            )

    old_news = {
        _normalize_name(item.get("title"))
        for item in (previous.get("news") or {}).get("items") or []
    }
    new_news = {
        _normalize_name(item.get("title"))
        for item in (current.get("news") or {}).get("items") or []
    }
    for title in sorted(new_news - old_news):
        event(
            "announcement_added",
            "announcements",
            None,
            title,
            f"Announcement {title!r} is newly present.",
            0.8,
        )

    return events


class TrackingService:
    def __init__(
        self,
        store: Optional[TrackingStore] = None,
        *,
        settings: Any = None,
    ) -> None:
        self.store: TrackingStore = store or InMemoryTrackingStore()
        self.settings = settings

    async def decide(
        self,
        competitor: str,
        url: str,
        *,
        force: bool = False,
    ) -> TrackingDecision:
        settings = self.settings
        if settings is not None and not getattr(settings, "tracking_enabled", True):
            return TrackingDecision(True, "tracking disabled: always crawl")
        registry = await self.store.get_page(competitor, url)
        if registry is None:
            return TrackingDecision(True, "new URL")
        if force or settings is None or not getattr(settings, "incremental_crawl", True):
            return TrackingDecision(True, "forced/incremental disabled")
        last_success = _parse_dt(registry.get("last_success_at"))
        if last_success is None:
            return TrackingDecision(True, "no successful crawl recorded")
        interval = timedelta(hours=float(getattr(settings, "tracking_interval_hours", 12.0)))
        if datetime.now(timezone.utc) - last_success < interval:
            snapshot = await self.store.latest_snapshot(competitor, url)
            if snapshot is not None:
                structured_hash = snapshot.get("structured_hash") or ""
                records = (
                    await self.store.snapshots_for_structured_hash(
                        competitor, url, structured_hash
                    )
                    if structured_hash
                    else []
                )
                if not records:
                    records = [snapshot]
                cached: list[PageSnapshot] = []
                seen: set[tuple[str, str]] = set()
                for record in records:
                    for candidate in snapshots_from_record(record):
                        key = (
                            candidate.billing_state,
                            content_hash(stable_text(candidate.text)),
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        cached.append(candidate)
                return TrackingDecision(
                    False,
                    "crawled recently; reusing cached snapshots",
                    cached_snapshots=cached,
                    registry=registry,
                )
        return TrackingDecision(True, "tracking interval elapsed")

    async def process(
        self,
        competitor: str,
        extraction: PageExtraction,
        *,
        status_override: Optional[str] = None,
        force: bool = False,
    ) -> TrackingOutcome:
        url = extraction.url
        payload = extraction.structured_payload()
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        structured_hash = content_hash(payload_json)
        text_blob = "\n".join(snapshot.text for snapshot in extraction.snapshots)
        text_digest = content_hash(stable_text(text_blob))

        registry = await self.store.get_page(competitor, url)
        previous_snapshot = await self.store.latest_snapshot(competitor, url)
        changes: list[dict[str, Any]] = []
        has_success = any(
            snapshot.status == "success" for snapshot in extraction.snapshots
        )

        if previous_snapshot is not None and not force and has_success:
            previous_payload = previous_snapshot.get("structured") or {}
            if previous_snapshot.get("structured_hash") == structured_hash:
                status = "unchanged"
                # Text may have changed without a semantic change (layout-only).
                await self.store.upsert_page(
                    competitor,
                    url,
                    {
                        "page_category": extraction.categories[0].value if extraction.categories else "general",
                        "last_crawl_at": iso_now(),
                        "last_success_at": iso_now(),
                        "last_text_hash": text_digest,
                        "crawl_status": "unchanged",
                    },
                )
                return TrackingOutcome(status, structured_hash, text_digest)
            changes = detect_changes(previous_payload, payload, competitor=competitor, url=url)

        status = status_override or ("updated" if changes else ("new" if registry is None else "updated"))

        if self.settings is None or getattr(self.settings, "store_full_snapshot", True):
            for record in snapshots_to_records(
                competitor,
                extraction.snapshots,
                store_full_text=True,
            ):
                record["structured_hash"] = structured_hash
                record["structured"] = payload
                record["page_category"] = extraction.categories[0].value if extraction.categories else "general"
                await self.store.save_snapshot(record)

        await self.store.upsert_page(
            competitor,
            url,
            {
                "page_category": extraction.categories[0].value if extraction.categories else "general",
                "page_categories": [category.value for category in extraction.categories],
                "last_crawl_at": iso_now(),
                "last_success_at": iso_now()
                if has_success
                else (registry or {}).get("last_success_at"),
                "last_content_hash": structured_hash,
                "last_text_hash": text_digest,
                "crawl_status": status,
            },
        )
        for event in changes:
            await self.store.record_change(event)
        return TrackingOutcome(status, structured_hash, text_digest, changes)
