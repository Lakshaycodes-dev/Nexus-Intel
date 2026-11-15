"""Competitor intelligence retrieval endpoints.

There is no separate "competitor" collection - a competitor is identified by
its normalised domain, and each analysis run is one intelligence record scoped
to the authenticated user's workspace.

* ``GET /api/v1/competitors``        -> latest run per tracked domain
* ``GET /api/v1/competitors/{id}``   -> one run, by domain or analysis ID
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pymongo.errors import PyMongoError

from app.auth import get_current_user
from app.database import AnalysisRepository, get_repository, record_to_public
from app.errors import DatabaseUnavailableError
from app.schemas import (
    CompetitorListEntry,
    CompetitorListResponse,
    CompetitorResponse,
)
from app.security import TargetValidationError, normalize_domain

logger = logging.getLogger("nexus_intel.api")

router = APIRouter(tags=["competitors"])

_ANALYSIS_ID_LENGTH = 32


def _is_analysis_id(value: str) -> bool:
    """Analysis IDs are ``uuid.uuid4().hex``: 32 lowercase hex characters."""
    return len(value) == _ANALYSIS_ID_LENGTH and all(
        c in "0123456789abcdef" for c in value
    )


def _list_entry(record: dict) -> CompetitorListEntry:
    public = record_to_public(record)
    return CompetitorListEntry(
        domain=public["domain"],
        analysis_id=public["analysis_id"],
        status=public["status"],
        created_at=public["created_at"],
        updated_at=public["updated_at"],
        has_data=bool(public.get("data")),
    )


@router.get(
    "/competitors",
    response_model=CompetitorListResponse,
    summary="List tracked competitors",
)
async def list_competitors(
    limit: int = Query(default=50, ge=1, le=200),
    repository: AnalysisRepository = Depends(get_repository),
    user: dict = Depends(get_current_user),
) -> CompetitorListResponse:
    """Return the most recent run for each domain in the caller's workspace."""
    try:
        records = await repository.list_latest_by_user(user["user_id"], limit=limit)
    except PyMongoError as exc:
        raise DatabaseUnavailableError() from exc

    entries = [_list_entry(record) for record in records]
    return CompetitorListResponse(competitors=entries, total=len(entries))


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
    user: dict = Depends(get_current_user),
) -> CompetitorResponse:
    """Look up the latest analysis for a competitor domain or analysis ID.

    Both lookups are filtered by ``user_id`` so one workspace can never read
    another workspace's records.
    """
    record = None

    if _is_analysis_id(competitor_id):
        try:
            record = await repository.get_by_id(
                competitor_id, user_id=user["user_id"]
            )
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
                record = await repository.get_latest_by_domain(
                    domain, user_id=user["user_id"]
                )
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
