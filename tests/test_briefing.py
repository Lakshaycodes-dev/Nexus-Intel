"""Voice briefing tests: window filtering, digest, audio endpoint, auth.

No network calls are made; ElevenLabs synthesis is monkeypatched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services import voice_briefing
from conftest import FakeRepository, seed_completed_record


def _seed(
    repo: FakeRepository,
    user_id: str,
    domain: str,
    *,
    analysis_id: str,
    created_at: datetime,
    pricing: Optional[list[dict[str, Any]]] = None,
    news: Optional[list[dict[str, Any]]] = None,
) -> str:
    seed_completed_record(
        repo,
        user_id,
        domain,
        analysis_id=analysis_id,
        created_at=created_at,
    )
    record = repo.records[analysis_id]
    record["data"]["domain"] = domain
    if pricing is not None:
        record["data"]["pricing"] = pricing
    if news is not None:
        record["data"]["offsiteNews"] = news
    return analysis_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# JSON digest
# --------------------------------------------------------------------------- #
def test_summary_only_includes_selected_window(client, fake_repo, auth_user):
    now = _now()
    user_id = auth_user["user_id"]

    _seed(
        fake_repo,
        user_id,
        "stripe.com",
        analysis_id="1" * 32,
        created_at=now - timedelta(hours=20),
        pricing=[{"tier": "Starter", "monthly": "$29", "annual": "", "features": []}],
    )
    _seed(
        fake_repo,
        user_id,
        "stripe.com",
        analysis_id="2" * 32,
        created_at=now - timedelta(hours=2),
        pricing=[{"tier": "Starter", "monthly": "$39", "annual": "", "features": []}],
    )
    _seed(
        fake_repo,
        user_id,
        "legacy.example",
        analysis_id="3" * 32,
        created_at=now - timedelta(days=3),
    )
    # Another workspace must never leak into this briefing.
    _seed(
        fake_repo,
        "someone-else",
        "private.example",
        analysis_id="4" * 32,
        created_at=now - timedelta(hours=1),
    )

    day = client.get("/api/v1/briefing/changes?window=24h")
    assert day.status_code == 200, day.text
    day_body = day.json()
    assert day_body["window"] == "24h"
    assert day_body["domains"] == ["stripe.com"]
    assert day_body["record_count"] == 2
    assert day_body["has_activity"] is True
    pricing_changes = [
        change for change in day_body["changes"] if change["change_type"] == "pricing"
    ]
    assert len(pricing_changes) == 1
    assert "$29" in pricing_changes[0]["detail"]
    assert "$39" in pricing_changes[0]["detail"]
    assert "Nexus Intel" in day_body["script"]

    week = client.get("/api/v1/briefing/changes?window=7d")
    assert week.status_code == 200, week.text
    week_body = week.json()
    assert week_body["window"] == "7d"
    assert set(week_body["domains"]) == {"stripe.com", "legacy.example"}
    assert week_body["record_count"] == 3


def test_invalid_window_is_rejected(client):
    response = client.get("/api/v1/briefing/changes?window=30d")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_empty_workspace_returns_quiet_briefing(client):
    response = client.get("/api/v1/briefing/changes?window=7d")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["has_activity"] is False
    assert body["changes"] == []
    assert body["record_count"] == 0
    assert "No completed competitor analyses" in body["script"]


def test_requires_authentication(anon_client):
    response = anon_client.get("/api/v1/briefing/changes")
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Voice endpoint
# --------------------------------------------------------------------------- #
def test_voice_endpoint_returns_mp3(client, fake_repo, auth_user, monkeypatch):
    now = _now()
    _seed(
        fake_repo,
        auth_user["user_id"],
        "croma.example",
        analysis_id="5" * 32,
        created_at=now - timedelta(hours=1),
        pricing=[{"tier": "Pro", "monthly": "₹999", "annual": "", "features": []}],
    )

    captured: dict[str, str] = {}

    async def fake_synthesize(text: str, **_kwargs: Any) -> bytes:
        captured["text"] = text
        return b"ID3\x04fake-mp3"

    monkeypatch.setattr(voice_briefing, "synthesize_speech", fake_synthesize)

    response = client.post("/api/v1/briefing/voice", json={"window": "24h"})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["x-briefing-window"] == "24h"
    assert response.content == b"ID3\x04fake-mp3"
    assert "Nexus Intel" in captured["text"]
    assert "croma dot example" in captured["text"]


def test_voice_endpoint_reports_missing_configuration(
    client, fake_repo, auth_user, monkeypatch
):
    monkeypatch.setattr(voice_briefing.config, "ELEVENLABS_API_KEY", "")

    response = client.post("/api/v1/briefing/voice", json={"window": "7d"})
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "voice_briefing_not_configured"


def test_voice_endpoint_requires_authentication(anon_client):
    response = anon_client.post("/api/v1/briefing/voice", json={"window": "24h"})
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Digest unit tests
# --------------------------------------------------------------------------- #
def test_briefing_handles_naive_utc_timestamps():
    reference = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    record = {
        "status": "completed",
        "domain": "acme.example",
        "created_at": datetime(2026, 1, 10, 10, 0),  # Mongo returns naive UTC
        "data": {
            "domain": "acme.example",
            "pricing": [
                {"tier": "Basic", "monthly": "₹499", "annual": "", "features": []}
            ],
            "offsiteNews": [],
        },
    }

    summary = voice_briefing.build_briefing(
        [record], window="24h", now=reference
    )
    assert summary.record_count == 1
    assert summary.domains == ["acme.example"]
    assert summary.has_activity is False
    assert summary.changes[0].change_type == "tracked"


def test_briefing_detects_new_tiers_and_news():
    reference = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    older = {
        "status": "completed",
        "created_at": reference - timedelta(days=1),
        "data": {
            "domain": "acme.example",
            "pricing": [
                {"tier": "Basic", "monthly": "₹499", "annual": "", "features": []}
            ],
            "offsiteNews": [
                {"title": "Existing story", "source": "Wire", "sentiment": "neutral"}
            ],
        },
    }
    newer = {
        "status": "completed",
        "created_at": reference - timedelta(hours=1),
        "data": {
            "domain": "acme.example",
            "pricing": [
                {"tier": "Basic", "monthly": "₹499", "annual": "", "features": []},
                {"tier": "Pro", "monthly": "₹1,299", "annual": "", "features": []},
            ],
            "offsiteNews": [
                {"title": "Existing story", "source": "Wire", "sentiment": "neutral"},
                {"title": "New launch", "source": "TechWire", "sentiment": "threat"},
            ],
        },
    }

    summary = voice_briefing.build_briefing(
        [older, newer], window="24h", now=reference
    )
    types = {(change.change_type, change.title) for change in summary.changes}
    assert ("pricing", "New Pro tier") in types
    assert ("news", "New launch") in types
    assert summary.has_activity is True
    assert "New launch" in summary.script
