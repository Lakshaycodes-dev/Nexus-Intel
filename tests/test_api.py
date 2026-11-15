"""API test suite for the Nexus-Intel FastAPI backend.

Runs fully offline: MongoDB and the account store are replaced with in-memory
fakes (wired in through FastAPI dependency overrides) and the orchestrator
service is monkeypatched, so no credentials, database, or network access are
needed.

Run with:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from conftest import CANNED_DATA, seed_completed_record
from app import config
from app.errors import PipelineExecutionError
from app.main import app
from app.services import orchestrator_service


@pytest.fixture
def pipeline_calls(monkeypatch):
    """Replace the orchestrator service with a canned successful run."""
    calls: list[dict] = []

    async def _fake_run_analysis(*, domain, query, parameters, mock):
        calls.append({"domain": domain, "query": query, "parameters": parameters, "mock": mock})
        return orchestrator_service.AnalysisOutcome(
            report_path="output/stripe_pricing_market_intelligence.md",
            sources=["https://stripe.com/pricing"],
            extractions=[],
            data={**CANNED_DATA, "domain": domain},
            execution_time_sec=1.25,
        )

    monkeypatch.setattr(orchestrator_service, "run_analysis", _fake_run_analysis)
    return calls


# --- 1. Health ------------------------------------------------------------- #


def test_health_returns_success(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"connected", "unavailable"}
    # Never leak the connection string.
    assert "mongodb://" not in response.text


# --- 2. Valid analyze request ---------------------------------------------- #


def test_analyze_accepts_valid_request(client, pipeline_calls, fake_repo):
    response = client.post(
        "/api/v1/analyze",
        json={"domain": "stripe.com", "parameters": {"pricing_tiers": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["analysis_id"]) == 32
    assert body["status"] == "completed"
    assert body["domain"] == "stripe.com"
    # The frontend reads raw.data and validates it as CompetitorData.
    data = body["data"]
    assert isinstance(data["domain"], str)
    assert isinstance(data["pricing"], list)
    assert isinstance(data["offsiteNews"], list)
    assert isinstance(data["capabilities"], list)
    assert isinstance(data["executionTimeSec"], (int, float))
    assert data["provenance"]["pricing_matrix"] == "gemini"


# --- 3. Invalid input ------------------------------------------------------ #


@pytest.mark.parametrize(
    "payload",
    [
        {},  # missing domain
        {"domain": ""},  # empty domain
        {"domain": "not a domain"},  # malformed
        {"domain": "localhost"},  # internal host (SSRF guard)
        {"domain": "http://192.168.1.1/pricing"},  # private IP (SSRF guard)
        {"domain": "ftp://stripe.com"},  # unsupported scheme
        {"domain": "stripe.com", "parameters": {"bogus_flag": True}},  # unknown flag
        {"domain": "stripe.com", "unexpected": 1},  # unknown top-level field
    ],
)
def test_analyze_rejects_invalid_input(client, pipeline_calls, payload):
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["details"], list)


# --- 4. Orchestrator invocation -------------------------------------------- #


def test_analyze_invokes_orchestrator_with_derived_query(client, pipeline_calls):
    response = client.post(
        "/api/v1/analyze",
        json={"domain": "https://www.stripe.com/pricing", "mock": True},
    )
    assert response.status_code == 200
    assert len(pipeline_calls) == 1
    call = pipeline_calls[0]
    assert call["domain"] == "stripe.com"  # normalised like the frontend
    assert call["query"] == "stripe pricing"  # derived from the domain
    assert call["mock"] is True  # explicit request flag wins over env default


# --- 5. Database record lifecycle ------------------------------------------ #


def test_analyze_persists_record_transitions(client, pipeline_calls, fake_repo, auth_user):
    response = client.post("/api/v1/analyze", json={"domain": "stripe.com"})
    assert response.status_code == 200
    analysis_id = response.json()["analysis_id"]

    # queued -> running -> completed, with results stored on the record.
    assert fake_repo.calls[:3] == [("create", "queued"), ("update", "running"), ("update", "completed")]
    record = fake_repo.records[analysis_id]
    assert record["status"] == "completed"
    assert record["user_id"] == auth_user["user_id"]
    assert record["data"]["domain"] == "stripe.com"
    assert record["completed_at"] is not None
    assert record["execution_time_sec"] == 1.25
    assert record["error"] is None


# --- 6. Orchestrator failure handling -------------------------------------- #


def test_analyze_failure_returns_502_and_records_error(client, monkeypatch, fake_repo):
    async def _explode(**kwargs):
        raise PipelineExecutionError("The upstream search service could not be reached.")

    monkeypatch.setattr(orchestrator_service, "run_analysis", _explode)

    response = client.post("/api/v1/analyze", json={"domain": "stripe.com"})
    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "pipeline_failed"

    failed = [r for r in fake_repo.records.values() if r["status"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["error"]["code"] == "pipeline_failed"


def test_analyze_timeout_returns_504(client, monkeypatch, fake_repo):
    async def _slow(**kwargs):
        await asyncio.sleep(5)
        return orchestrator_service.AnalysisOutcome(
            report_path="", sources=[], extractions=[], data=CANNED_DATA, execution_time_sec=5.0
        )

    monkeypatch.setattr(orchestrator_service, "run_analysis", _slow)
    monkeypatch.setattr(config, "ANALYSIS_TIMEOUT_SECONDS", 0.05)

    response = client.post("/api/v1/analyze", json={"domain": "stripe.com"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "analysis_timeout"


def test_analyze_unexpected_error_hides_internals(
    client, monkeypatch, fake_repo, fake_users
):
    async def _boom(**kwargs):
        raise ValueError("secret=sk-internal-detail")

    monkeypatch.setattr(orchestrator_service, "run_analysis", _boom)

    # raise_server_exceptions=False lets the app's 500 handler respond.
    with TestClient(app, raise_server_exceptions=False) as leak_client:
        from app.database import get_repository, get_user_repository

        app.dependency_overrides[get_repository] = lambda: fake_repo
        app.dependency_overrides[get_user_repository] = lambda: fake_users
        leak_client.headers.update(dict(client.headers))
        response = leak_client.post("/api/v1/analyze", json={"domain": "stripe.com"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "sk-internal-detail" not in response.text


# --- 7. Competitor retrieval ----------------------------------------------- #


def test_competitor_lookup_by_domain(client, fake_repo, auth_user):
    seed_completed_record(fake_repo, auth_user["user_id"])
    response = client.get("/api/v1/competitors/stripe.com")
    assert response.status_code == 200
    body = response.json()
    assert body["competitor_id"] == "stripe.com"
    assert body["domain"] == "stripe.com"
    assert body["status"] == "completed"
    assert body["data"]["pricing"][0]["tier"] == "Starter"


def test_competitor_lookup_by_analysis_id(client, fake_repo, auth_user):
    analysis_id = seed_completed_record(fake_repo, auth_user["user_id"])
    response = client.get(f"/api/v1/competitors/{analysis_id}")
    assert response.status_code == 200
    assert response.json()["analysis_id"] == analysis_id


def test_competitor_lookup_is_scoped_to_workspace(client, fake_repo):
    seed_completed_record(fake_repo, "another-user", "stripe.com")
    response = client.get("/api/v1/competitors/stripe.com")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_list_competitors_returns_latest_run_per_domain(client, fake_repo, auth_user):
    user_id = auth_user["user_id"]
    seed_completed_record(
        fake_repo,
        user_id,
        "stripe.com",
        analysis_id="1" * 32,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    seed_completed_record(
        fake_repo,
        user_id,
        "stripe.com",
        analysis_id="2" * 32,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    seed_completed_record(
        fake_repo,
        user_id,
        "croma.com",
        analysis_id="3" * 32,
        created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    response = client.get("/api/v1/competitors")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    entries = {entry["domain"]: entry for entry in body["competitors"]}
    assert entries["stripe.com"]["analysis_id"] == "2" * 32
    assert entries["croma.com"]["has_data"] is True


# --- 8. Missing records -> 404 --------------------------------------------- #


def test_missing_competitor_returns_404(client):
    response = client.get("/api/v1/competitors/stripe.com")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_missing_analysis_returns_404(client):
    response = client.get(f"/api/v1/analyze/{'b' * 32}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --- 9. Analysis status/results retrieval ---------------------------------- #


def test_get_analysis_by_id_returns_status_and_results(client, pipeline_calls, fake_repo):
    create = client.post("/api/v1/analyze", json={"domain": "stripe.com"})
    analysis_id = create.json()["analysis_id"]

    response = client.get(f"/api/v1/analyze/{analysis_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert body["status"] == "completed"
    assert body["created_at"] is not None
    assert body["completed_at"] is not None
    assert body["data"]["domain"] == "stripe.com"


# --- 10. CORS and configuration -------------------------------------------- #


def test_cors_preflight_allows_frontend_origin(client):
    response = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_configuration_is_env_driven():
    assert isinstance(config.CORS_ORIGINS, list)
    assert all(origin.startswith(("http://", "https://")) for origin in config.CORS_ORIGINS)
    assert config.ANALYSIS_TIMEOUT_SECONDS > 0


# --- Bonus: security helpers ----------------------------------------------- #


def test_normalize_domain_strips_scheme_www_path_and_port():
    from app.security import normalize_domain

    assert normalize_domain("https://WWW.Stripe.com/pricing?ref=1") == "stripe.com"
    assert normalize_domain("stripe.com:443") == "stripe.com"


def test_derive_query_matches_pipeline_convention():
    from app.security import derive_query_from_domain

    assert derive_query_from_domain("stripe.com") == "stripe pricing"


# --- Bonus: pricing mapping robustness ------------------------------------- #


def test_map_pricing_handles_fallback_billing_period_quirks():
    """The heuristic fallback can emit non-enum billing periods (e.g. '$0')."""
    from types import SimpleNamespace

    from app.services.orchestrator_service import _map_pricing

    model = SimpleNamespace(
        model_dump=lambda: {
            "plans": [
                {
                    "name": "Starter",
                    "price": 0.0,
                    "price_display": "$0",
                    "billing_period": "$0",  # misparsed by the fallback parser
                    "included_features": ["$0", "1", "Basic dashboard"],
                },
                {
                    "name": "Scale",
                    "price": 199.0,
                    "price_display": "$199/yr",
                    "billing_period": "annual",
                    "included_features": ["SSO"],
                },
            ]
        }
    )
    rows = _map_pricing(model)
    assert rows[0] == {
        "tier": "Starter",
        "monthly": "$0",
        "annual": "",
        "features": ["1", "Basic dashboard"],  # duplicate price cell dropped
    }
    assert rows[1]["annual"] == "$199/yr"
    assert rows[1]["monthly"] == ""


def test_map_pricing_preserves_inr_display():
    """INR prices must not be rewritten with a USD symbol."""
    from types import SimpleNamespace

    from app.services.orchestrator_service import _map_pricing

    model = SimpleNamespace(
        model_dump=lambda: {
            "plans": [
                {
                    "name": "55-inch QLED",
                    "price": 54990.0,
                    "price_display": "₹54,990",
                    "billing_period": "one_time",
                    "included_features": [],
                },
                {
                    "name": "Soundbar",
                    "price": 12990.0,
                    "price_display": "12990",
                    "billing_period": "one_time",
                    "included_features": [],
                },
            ]
        }
    )
    rows = _map_pricing(model)
    assert rows[0]["monthly"] == "₹54,990"
    # A bare number is left untouched rather than given a fabricated symbol.
    assert rows[1]["monthly"] == "12990"


def test_provenance_labels_llm_and_fallback():
    from app.services.orchestrator_service import _provenance_for

    assert _provenance_for([]) == "gemini"
    assert _provenance_for(["repaired: model output fixed"]) == "gemini"
    assert _provenance_for(["fallback: extracted by heuristic parser, not the LLM"]) == "fallback"
