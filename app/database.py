"""Async MongoDB (Motor) connection management and analysis persistence.

Design notes
------------
* Credentials come from ``MONGODB_URI`` (env only) and are never logged or
  returned in API responses - only the coarse connection *state* is exposed.
* The startup probe uses a short server-selection timeout so a down database
  degrades the health check to ``"unavailable"`` instead of blocking boot.
* All queries go through :class:`AnalysisRepository`, keeping route handlers
  free of database details (see ``app/routers/``).
* Mock-mode local runs can fall back to :class:`InMemoryAnalysisRepository`
  when MongoDB is unavailable; restarting the API clears those records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app import config

logger = logging.getLogger("nexus_intel.db")

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None
_memory_repository: Optional["InMemoryAnalysisRepository"] = None
_memory_tracking_store: Optional[Any] = None
_memory_fallback_logged = False


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def connect_db() -> None:
    """Create the client, probe connectivity, and ensure indexes.

    Raises ``PyMongoError`` on failure; the caller (app lifespan) decides how
    to degrade. The URI itself is never included in raised messages or logs.
    """
    global _client, _database

    await close_db()

    _client = AsyncIOMotorClient(
        config.MONGODB_URI,
        serverSelectionTimeoutMS=config.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    )
    # Probe: raises ServerSelectionTimeoutError if unreachable.
    await _client.admin.command("ping")
    _database = _client[config.MONGODB_DATABASE]
    await _ensure_indexes(_database)
    logger.info(
        "Connected to MongoDB database %r (host configured via MONGODB_URI)",
        config.MONGODB_DATABASE,
    )


async def close_db() -> None:
    """Close the active client (safe to call when never connected)."""
    global _client, _database
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")
    _client = None
    _database = None


def is_connected() -> bool:
    return _database is not None


def get_database() -> AsyncIOMotorDatabase:
    """Return the active database or raise ``ApiException``-free RuntimeError.

    Routers call this via the ``get_repository`` dependency, which converts the
    error into a 503 envelope.
    """
    if _database is None:
        raise RuntimeError("MongoDB is not connected")
    return _database


def get_tracking_store() -> Optional[Any]:
    """Return the active tracking store (MongoDB or shared in-memory fallback).

    Imports are lazy so ``services.collection`` stays independent of Motor. A
    process-global in-memory store keeps incremental crawling/change detection
    working during local no-Mongo demos; it resets with the server.
    """
    global _memory_tracking_store

    if _database is not None:
        from services.collection.tracking import MongoTrackingStore

        return MongoTrackingStore(
            _database,
            registry_collection=config.MONGODB_PAGE_REGISTRY_COLLECTION,
            snapshots_collection=config.MONGODB_SNAPSHOTS_COLLECTION,
            changes_collection=config.MONGODB_CHANGE_EVENTS_COLLECTION,
        )
    if not config.IN_MEMORY_PERSISTENCE:
        return None

    if _memory_tracking_store is None:
        from services.collection.tracking import InMemoryTrackingStore

        _memory_tracking_store = InMemoryTrackingStore()
    return _memory_tracking_store


class InMemoryAnalysisRepository:
    """Process-local fallback used when MongoDB is unavailable in mock mode.

    Records survive for the lifetime of the server process only. This keeps the
    API and frontend usable for local demos without silently pretending MongoDB
    is connected.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    async def create(self, record: dict[str, Any]) -> None:
        self._records[record["analysis_id"]] = dict(record)

    async def update(self, analysis_id: str, changes: dict[str, Any]) -> None:
        record = self._records.get(analysis_id)
        if record is not None:
            record.update({**changes, "updated_at": utcnow()})

    async def get_by_id(self, analysis_id: str) -> Optional[dict[str, Any]]:
        record = self._records.get(analysis_id)
        return dict(record) if record is not None else None

    async def get_latest_by_domain(self, domain: str) -> Optional[dict[str, Any]]:
        matches = [
            record for record in self._records.values() if record.get("domain") == domain
        ]
        if not matches:
            return None
        return dict(max(matches, key=lambda record: record["created_at"]))


def get_repository() -> "Any":
    """FastAPI dependency yielding a repository bound to the live connection.

    When MongoDB is down, mock mode uses an in-memory repository so the product
    remains runnable locally (data resets on restart). Otherwise this raises
    ``DatabaseUnavailableError`` (-> 503 envelope), so routers never see a bare
    RuntimeError.
    """
    global _memory_repository, _memory_fallback_logged

    if _database is not None:
        return AnalysisRepository(_database)
    if not config.IN_MEMORY_PERSISTENCE:
        from app.errors import DatabaseUnavailableError

        raise DatabaseUnavailableError()

    if _memory_repository is None:
        _memory_repository = InMemoryAnalysisRepository()
    if not _memory_fallback_logged:
        logger.warning(
            "MongoDB is unavailable; using the in-memory analysis store. "
            "Analysis records will not survive a server restart."
        )
        _memory_fallback_logged = True
    return _memory_repository


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    collection = db[config.MONGODB_COLLECTION]
    await collection.create_index(
        [("analysis_id", ASCENDING)], unique=True, name="analysis_id_unique"
    )
    # Competitor lookups resolve to the most recent analysis for a domain.
    await collection.create_index(
        [("domain", ASCENDING), ("created_at", DESCENDING)],
        name="domain_created_at",
    )
    await collection.create_index([("status", ASCENDING)], name="status")

    # Additive tracking indexes. The MongoTrackingStore also ensures these
    # lazily, but creating them at startup keeps first-run latency predictable.
    registry = db[config.MONGODB_PAGE_REGISTRY_COLLECTION]
    await registry.create_index(
        [("competitor", ASCENDING), ("url", ASCENDING)],
        unique=True,
        name="page_registry_competitor_url",
    )
    await registry.create_index(
        [("competitor", ASCENDING), ("last_crawl_at", DESCENDING)],
        name="page_registry_last_crawl",
    )
    snapshots = db[config.MONGODB_SNAPSHOTS_COLLECTION]
    await snapshots.create_index(
        [("competitor", ASCENDING), ("url", ASCENDING), ("content_hash", ASCENDING)],
        unique=True,
        name="page_snapshot_unique",
    )
    changes = db[config.MONGODB_CHANGE_EVENTS_COLLECTION]
    await changes.create_index(
        [("competitor", ASCENDING), ("detected_at", DESCENDING)],
        name="change_events_competitor_time",
    )


class AnalysisRepository:
    """Persistence operations for analysis records.

    Documents follow the schema in STEP 3 of the backend spec:
    ``analysis_id``, ``domain``, ``query``, ``parameters``, ``status``,
    ``created_at``, ``updated_at``, ``completed_at``, ``execution_time_sec``,
    ``report_path``, ``extractions``, ``data``, ``error``.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[config.MONGODB_COLLECTION]

    async def create(self, record: dict[str, Any]) -> None:
        try:
            await self._collection.insert_one(record)
        except PyMongoError as exc:
            logger.error("Failed to insert analysis record: %s", type(exc).__name__)
            raise

    async def update(self, analysis_id: str, changes: dict[str, Any]) -> None:
        changes = {**changes, "updated_at": utcnow()}
        try:
            await self._collection.update_one(
                {"analysis_id": analysis_id}, {"$set": changes}
            )
        except PyMongoError as exc:
            logger.error("Failed to update analysis record: %s", type(exc).__name__)
            raise

    async def get_by_id(self, analysis_id: str) -> Optional[dict[str, Any]]:
        try:
            return await self._collection.find_one({"analysis_id": analysis_id})
        except PyMongoError as exc:
            logger.error("Failed to read analysis record: %s", type(exc).__name__)
            raise

    async def get_latest_by_domain(self, domain: str) -> Optional[dict[str, Any]]:
        try:
            cursor = (
                self._collection.find({"domain": domain})
                .sort("created_at", DESCENDING)
                .limit(1)
            )
            matches = await cursor.to_list(length=1)
            return matches[0] if matches else None
        except PyMongoError as exc:
            logger.error("Failed to read competitor record: %s", type(exc).__name__)
            raise


def record_to_public(record: dict[str, Any]) -> dict[str, Any]:
    """Strip the Mongo ``_id`` before a document leaves the persistence layer."""
    return {key: value for key, value in record.items() if key != "_id"}
