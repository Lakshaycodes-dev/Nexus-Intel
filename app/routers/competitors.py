"""``GET /api/v1/competitors/{id}``.

Assumption (documented per the backend spec): the repository has no separate
"competitor" collection - a competitor is identified by its normalised domain,
and each analysis run is one competitor-intelligence record. The ``{id}``
path parameter therefore accepts *either*:

* a domain (``stripe.com`` or a full URL) -> most recent analysis for it, or
* a 32-char analysis ID -> that exact analysis.

Returns 404 with the standard error envelope when nothing matches.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pymongo.errors import PyMongoError

from app.database import AnalysisRepository, get_repository, record_to_public
from app.errors import DatabaseUnavailableError
from app.schemas import CompetitorResponse
from app.security import TargetValidationError, normalize_domain

logger = logging.getLogger("nexus_intel.api")

router = APIRouter(tags=["competitors"])

_ANALYSIS_ID_LENGTH = 32


def _is_analysis_id(value: str) -> bool:
    """Analysis IDs are ``uuid.uuid4().hex``: 32 lowercase hex characters."""
    return len(value) == _ANALYSIS_ID_LENGTH and all(
        c in "0123456789abcdef" for c in value
    )


@router.get(
    "/competitors/{competitor_id}",
    response_model=CompetitorResponse,
    summary="Retrieve competitor intelligence",
)
async def get_competitor(
    competitor_id: str = Path(
        ...,
        min_length=1,
        max_length=2048,
        description="A competitor domain (e.g. 'stripe.com') or an analysis ID.",
    ),
    repository: AnalysisRepository = Depends(get_repository),
) -> CompetitorResponse:
    """Look up the latest analysis for a competitor domain or analysis ID."""
    record = None

    if _is_analysis_id(competitor_id):
        try:
            record = await repository.get_by_id(competitor_id)
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    if record is None:
        # Treat the identifier as a domain/URL (frontend sends bare domains).
        try:
            domain = normalize_domain(competitor_id)
        except TargetValidationError:
            domain = None
        if domain:
            try:
                record = await repository.get_latest_by_domain(domain)
            except PyMongoError as exc:
                raise DatabaseUnavailableError() from exc

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No competitor analysis found for {competitor_id!r}.",
        )

    public = record_to_public(record)
    return CompetitorResponse(
        competitor_id=public["domain"],
        domain=public["domain"],
        analysis_id=public["analysis_id"],
        status=public["status"],
        created_at=public["created_at"],
        updated_at=public["updated_at"],
        data=public.get("data"),
        error=public.get("error"),
    )
