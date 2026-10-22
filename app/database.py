"""Async MongoDB (Motor) connection management and analysis persistence.

Design notes
------------
* Credentials come from ``MONGODB_URI`` (env only) and are never logged or
  returned in API responses - only the coarse connection *state* is exposed.
* The startup probe uses a short server-selection timeout so a down database
  degrades the health check to ``"unavailable"`` instead of blocking boot.
* All queries go through :class:`AnalysisRepository`, keeping route handlers
  free of database details (see ``app/routers/``).
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


def get_repository() -> "AnalysisRepository":
    """FastAPI dependency yielding a repository bound to the live connection.

    Raises ``DatabaseUnavailableError`` (-> 503 envelope) when MongoDB is not
    connected, so routers never see a bare RuntimeError.
    """
    from app.errors import DatabaseUnavailableError

    if _database is None:
        raise DatabaseUnavailableError()
    return AnalysisRepository(_database)


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
