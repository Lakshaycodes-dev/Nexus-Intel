"""Shared pytest fixtures: hermetic API client with fake persistence.

No MongoDB, network, or credentials are used. Both repositories are replaced
through FastAPI dependency overrides, and the app lifespan's database calls are
monkeypatched so startup cannot touch a real cluster.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import database  # noqa: E402
from app.database import get_repository, get_user_repository  # noqa: E402
from app.errors import ConflictError  # noqa: E402
from app.main import app  # noqa: E402

CANNED_DATA = {
    "domain": "stripe.com",
    "pricing": [{"tier": "Starter", "monthly": "$0", "annual": "", "features": ["Dash"]}],
    "offsiteNews": [
        {
            "title": "Stripe expands stablecoin payouts",
            "source": "TechCrunch",
            "url": "https://techcrunch.com/",
            "sentiment": "neutral",
        }
    ],
    "capabilities": [
        {"name": "Static Page", "traditionalScraper": True, "nexusIntel": True}
    ],
    "executionTimeSec": 1.25,
    "provenance": {"pricing_matrix": "gemini"},
}


class FakeRepository:
    """In-memory stand-in for AnalysisRepository (async, same surface)."""

    def __init__(self) -> None:
        self.records: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []

    async def create(self, record: dict) -> None:
        self.calls.append(("create", record["status"]))
        self.records[record["analysis_id"]] = dict(record)

    async def update(self, analysis_id: str, changes: dict) -> None:
        self.calls.append(("update", changes.get("status", "?")))
        self.records[analysis_id].update(changes)

    async def get_by_id(self, analysis_id: str, *, user_id: str | None = None) -> dict | None:
        record = self.records.get(analysis_id)
        if record is None:
            return None
        if user_id is not None and record.get("user_id") != user_id:
            return None
        return dict(record)

    async def get_latest_by_domain(
        self, domain: str, *, user_id: str | None = None
    ) -> dict | None:
        matches = [
            record
            for record in self.records.values()
            if record["domain"] == domain
            and (user_id is None or record.get("user_id") == user_id)
        ]
        if not matches:
            return None
        return dict(sorted(matches, key=lambda record: record["created_at"])[-1])

    async def list_latest_by_user(self, user_id: str, *, limit: int = 50) -> list[dict]:
        latest: dict[str, dict] = {}
        for record in self.records.values():
            if record.get("user_id") != user_id:
                continue
            current = latest.get(record["domain"])
            if current is None or record["created_at"] > current["created_at"]:
                latest[record["domain"]] = record
        ordered = sorted(
            latest.values(), key=lambda record: record["created_at"], reverse=True
        )
        return [dict(record) for record in ordered[:limit]]


class FakeUserRepository:
    """In-memory stand-in for UserRepository."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    async def create(self, record: dict) -> None:
        if any(user["email"] == record["email"] for user in self.users.values()):
            raise ConflictError("An account with this email already exists.")
        self.users[record["user_id"]] = dict(record)

    async def get_by_email(self, email: str) -> dict | None:
        for user in self.users.values():
            if user["email"] == email:
                return dict(user)
        return None

    async def get_by_id(self, user_id: str) -> dict | None:
        user = self.users.get(user_id)
        return dict(user) if user is not None else None


def seed_completed_record(
    repo: FakeRepository,
    user_id: str,
    domain: str = "stripe.com",
    *,
    analysis_id: str | None = None,
    created_at: datetime | None = None,
) -> str:
    now = created_at or datetime.now(timezone.utc)
    analysis_id = analysis_id or ("a" * 32)
    repo.records[analysis_id] = {
        "analysis_id": analysis_id,
        "user_id": user_id,
        "domain": domain,
        "query": "stripe pricing",
        "mock": True,
        "status": "completed",
        "parameters": {
            "pricing_tiers": True,
            "feature_accordions": True,
            "offsite_mentions": True,
        },
        "created_at": now,
        "updated_at": now,
        "completed_at": now,
        "execution_time_sec": 1.25,
        "report_path": "output/report.md",
        "extractions": [],
        "data": {**CANNED_DATA, "domain": domain},
        "error": None,
    }
    return analysis_id


@pytest.fixture
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def fake_users() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def anon_client(fake_repo, fake_users, monkeypatch):
    """API client with no Authorization header."""

    async def _noop_connect() -> None:
        return None

    async def _noop_close() -> None:
        return None

    monkeypatch.setattr(database, "connect_db", _noop_connect)
    monkeypatch.setattr(database, "close_db", _noop_close)
    monkeypatch.setattr(database, "_database", None)

    app.dependency_overrides[get_repository] = lambda: fake_repo
    app.dependency_overrides[get_user_repository] = lambda: fake_users
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client):
    """API client signed in as a freshly registered workspace user."""
    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Lakshay Sharma",
            "email": "lakshay@example.com",
            "password": "correct-horse-battery",
            "workspace_name": "Lakshay Retail",
        },
    )
    assert response.status_code == 201, response.text
    anon_client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    return anon_client


@pytest.fixture
def auth_user(client) -> dict:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200, response.text
    return response.json()
