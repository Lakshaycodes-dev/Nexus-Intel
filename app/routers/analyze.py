"""``POST /api/v1/analyze`` and ``GET /api/v1/analyze/{analysis_id}``.

The POST endpoint mirrors the frontend contract recovered from the (removed)
``lib/api.ts``: the dashboard sends ``{domain, parameters}`` and reads the
response's ``data`` field as ``CompetitorData``. The pipeline is *awaited*
inline (the orchestrator is already async and does not block the event loop);
the analysis record is persisted with ``queued -> running -> completed|failed``
transitions so it can be re-read later by ID or by domain.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pymongo.errors import PyMongoError

from app import config
from app.database import AnalysisRepository, get_repository, record_to_public, utcnow
from app.errors import AnalysisTimeoutError, DatabaseUnavailableError
from app.schemas import (
    AnalysisParameters,
    AnalysisRecord,
    AnalyzeRequest,
    AnalyzeResponse,
    CompetitorData,
    ExtractionSummary,
)
from app.security import derive_query_from_domain
from app.services import orchestrator_service

logger = logging.getLogger("nexus_intel.api")

router = APIRouter(tags=["analysis"])


def _new_record(
    analysis_id: str,
    domain: str,
    query: str,
    mock: bool,
    parameters: AnalysisParameters,
) -> dict:
    now = utcnow()
    return {
        "analysis_id": analysis_id,
        "domain": domain,
        "query": query,
        "mock": mock,
        "status": "queued",
        "parameters": parameters.model_dump(),
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "execution_time_sec": None,
        "report_path": None,
        "extractions": [],
        "data": None,
        "error": None,
    }


def _safe_error(exc: Exception) -> dict:
    """Client-safe error snippet persisted with failed records."""
    code = getattr(exc, "code", "internal_error")
    message = getattr(exc, "message", str(exc) or type(exc).__name__)
    return {"code": code, "message": message}


async def _mark_failed(
    repository: AnalysisRepository,
    analysis_id: str,
    error: dict,
) -> None:
    try:
        await repository.update(
            analysis_id,
            {
                "status": "failed",
                "completed_at": utcnow(),
                "error": error,
            },
        )
    except PyMongoError:  # pragma: no cover - best-effort bookkeeping
        logger.error("Could not persist failure state for %s", analysis_id)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger a competitor analysis",
)
async def create_analysis(
    payload: AnalyzeRequest,
    repository: AnalysisRepository = Depends(get_repository),
) -> AnalyzeResponse:
    """Run the orchestrator pipeline for one competitor and persist the result.

    The synchronous response keeps the existing frontend working unchanged; the
    record is also stored so ``GET /api/v1/analyze/{id}`` and
    ``GET /api/v1/competitors/{id}`` can retrieve it later.
    """
    query = payload.query or derive_query_from_domain(payload.domain)
    mock = config.MOCK_MODE if payload.mock is None else payload.mock
    analysis_id = uuid.uuid4().hex

    try:
        await repository.create(_new_record(analysis_id, payload.domain, query, mock, payload.parameters))
        await repository.update(analysis_id, {"status": "running"})
    except PyMongoError as exc:
        logger.error("Could not create analysis record: %s", type(exc).__name__)
        raise DatabaseUnavailableError(
            "Could not save the analysis request. Please retry shortly."
        ) from exc

    try:
        outcome = await asyncio.wait_for(
            orchestrator_service.run_analysis(
                domain=payload.domain,
                query=query,
                parameters=payload.parameters,
                mock=mock,
            ),
            timeout=config.ANALYSIS_TIMEOUT_SECONDS,
        )
    except (TimeoutError, asyncio.TimeoutError) as exc:
        await _mark_failed(
            repository,
            analysis_id,
            {"code": "analysis_timeout", "message": "The analysis timed out."},
        )
        raise AnalysisTimeoutError() from exc
    except Exception as exc:  # PipelineExecutionError or unexpected failure
        await _mark_failed(repository, analysis_id, _safe_error(exc))
        raise

    extractions = [result.to_summary() for result in outcome.extractions]
    completed_at = utcnow()

    try:
        await repository.update(
            analysis_id,
            {
                "status": "completed",
                "completed_at": completed_at,
                "execution_time_sec": outcome.data.get("executionTimeSec", 0.0),
                "report_path": outcome.report_path,
                "extractions": extractions,
                "data": outcome.data,
                "error": None,
            },
        )
    except PyMongoError:
        # The run succeeded; return the result even if persistence failed.
        logger.error("Could not persist completed analysis %s", analysis_id)

    return AnalyzeResponse(
        analysis_id=analysis_id,
        status="completed",
        domain=payload.domain,
        query=query,
        mock=mock,
        created_at=utcnow(),
        completed_at=completed_at,
        execution_time_sec=outcome.data.get("executionTimeSec", 0.0),
        report_path=outcome.report_path,
        extractions=[ExtractionSummary(**summary) for summary in extractions],
        data=CompetitorData(**outcome.data),
    )


_ANALYSIS_ID_PATH = Path(
    ...,
    min_length=32,
    max_length=32,
    description="The analysis ID returned by POST /api/v1/analyze.",
)


@router.get(
    "/analyze/{analysis_id}",
    response_model=AnalysisRecord,
    summary="Retrieve an analysis by ID",
)
async def get_analysis(
    analysis_id: str = _ANALYSIS_ID_PATH,
    repository: AnalysisRepository = Depends(get_repository),
) -> AnalysisRecord:
    """Return the stored record (status, timestamps, results, error)."""
    try:
        record = await repository.get_by_id(analysis_id)
    except PyMongoError as exc:
        raise DatabaseUnavailableError() from exc

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found with id {analysis_id!r}.",
        )
    return AnalysisRecord(**record_to_public(record))
