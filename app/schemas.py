"""API request/response contracts for the Nexus-Intel backend.

``CompetitorData`` mirrors the frontend contract recovered from the (removed)
``lib/api.ts``: the client reads ``raw.data`` and validates it as
``{domain, pricing[], offsiteNews[], capabilities[], executionTimeSec}``.
Keeping that shape stable is what lets the dashboard consume the live API
without UI changes.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import config
from app.security import TargetValidationError, normalize_domain

AnalysisStatus = Literal["queued", "running", "completed", "failed"]

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class RegisterRequest(BaseModel):
    """POST /api/v1/auth/register payload."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., max_length=254)
    password: str = Field(
        ...,
        min_length=config.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="At least 8 characters; hashed with scrypt before storage.",
    )
    workspace_name: Optional[str] = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email address.")
        return email

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        name = " ".join(value.split())
        if not name:
            raise ValueError("Your name is required.")
        return name

    @field_validator("workspace_name")
    @classmethod
    def _clean_workspace(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        workspace = " ".join(value.split())
        return workspace or None


class LoginRequest(BaseModel):
    """POST /api/v1/auth/login payload."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class UserPublic(BaseModel):
    """Account details safe to return to the client (never the hash)."""

    user_id: str
    email: str
    name: str
    workspace_name: str
    created_at: datetime


class AuthResponse(BaseModel):
    """Token + profile returned by register/login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserPublic


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
    # Per-target provenance ("gemini" | "fallback") so the UI can be honest
    # about whether a row came from the LLM or the heuristic extractor.
    provenance: dict[str, str] = Field(default_factory=dict)


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


class CompetitorListEntry(BaseModel):
    """One tracked domain in the caller's workspace."""

    domain: str
    analysis_id: str
    status: AnalysisStatus
    created_at: datetime
    updated_at: datetime
    has_data: bool = False


class CompetitorListResponse(BaseModel):
    """GET /api/v1/competitors payload (latest run per domain)."""

    competitors: list[CompetitorListEntry] = Field(default_factory=list)
    total: int = 0


class HealthResponse(BaseModel):
    """GET /health payload."""

    status: Literal["ok", "degraded"]
    service: str = "nexus-intel-api"
    version: str
    mock_mode: bool
    database: Literal["connected", "unavailable"]
    timestamp: datetime
