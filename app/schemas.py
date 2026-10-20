"""API request/response contracts for the Nexus-Intel backend.

``CompetitorData`` mirrors the frontend contract recovered from the (removed)
``lib/api.ts``: the client reads ``raw.data`` and validates it as
``{domain, pricing[], offsiteNews[], capabilities[], executionTimeSec}``.
Keeping that shape stable is what lets the dashboard consume the live API
without UI changes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security import TargetValidationError, normalize_domain

AnalysisStatus = Literal["queued", "running", "completed", "failed"]


class AnalysisParameters(BaseModel):
    """Feature flags accepted by the frontend's analysis form."""

    model_config = ConfigDict(extra="forbid")

    pricing_tiers: bool = True
    feature_accordions: bool = True
    offsite_mentions: bool = True


class AnalyzeRequest(BaseModel):
    """POST /api/v1/analyze payload (frontend: {domain, parameters})."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(
        ...,
        description="Competitor domain or pricing-page URL, e.g. 'stripe.com'.",
        examples=["stripe.com"],
    )
    parameters: AnalysisParameters = Field(default_factory=AnalysisParameters)
    query: Optional[str] = Field(
        default=None,
        max_length=300,
        description=(
            "Optional override for the pipeline search query. Defaults to "
            "'<label> pricing' derived from the domain (the orchestrator is "
            "query-based)."
        ),
    )
    mock: Optional[bool] = Field(
        default=None,
        description="Force mock mode on/off; defaults to the MOCK_MODE env var.",
    )

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        try:
            return normalize_domain(value)
        except TargetValidationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


# --- Result payloads ------------------------------------------------------- #


class PricingEntry(BaseModel):
    """One pricing row in the frontend's comparison matrix."""

    tier: str
    monthly: str = ""
    annual: str = ""
    features: list[str] = Field(default_factory=list)


class NewsEntry(BaseModel):
    """One off-site mention."""

    title: str
    source: str = "unknown"
    url: Optional[str] = None
    sentiment: Literal["positive", "threat", "neutral"] = "neutral"


class CapabilityEntry(BaseModel):
    """Capability comparison row (traditional scraper vs Nexus-Intel)."""

    name: str
    traditionalScraper: bool = False
    nexusIntel: bool = True


class CompetitorData(BaseModel):
    """Payload validated by the frontend's ``isCompetitorData()``."""

    domain: str
    pricing: list[PricingEntry] = Field(default_factory=list)
    offsiteNews: list[NewsEntry] = Field(default_factory=list)
    capabilities: list[CapabilityEntry] = Field(default_factory=list)
    executionTimeSec: float = 0.0


class ExtractionSummary(BaseModel):
    """Per-target extraction outcome, kept for transparency/debugging."""

    target: str
    provenance: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Synchronous analyze response (the dashboard awaits this POST)."""

    analysis_id: str
    status: AnalysisStatus
    domain: str
    query: str
    mock: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_sec: float = 0.0
    report_path: Optional[str] = None
    extractions: list[ExtractionSummary] = Field(default_factory=list)
    data: CompetitorData


class AnalysisRecord(BaseModel):
    """Persisted analysis as returned by the retrieval endpoints."""

    analysis_id: str
    domain: str
    query: str
    mock: bool
    status: AnalysisStatus
    parameters: AnalysisParameters
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_sec: Optional[float] = None
    report_path: Optional[str] = None
    extractions: list[ExtractionSummary] = Field(default_factory=list)
    data: Optional[CompetitorData] = None
    error: Optional[dict[str, Any]] = None


class CompetitorResponse(BaseModel):
    """GET /api/v1/competitors/{id} payload."""

    competitor_id: str
    domain: str
    analysis_id: str
    status: AnalysisStatus
    created_at: datetime
    updated_at: datetime
    data: Optional[CompetitorData] = None
    error: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    """GET /health payload."""

    status: Literal["ok", "degraded"]
    service: str = "nexus-intel-api"
    version: str
    mock_mode: bool
    database: Literal["connected", "unavailable"]
    timestamp: datetime
